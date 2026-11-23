"""Loopback-only workshop; synthesis and inspection use each model's own venv."""
import argparse
import json
import os
import secrets
import shutil
import subprocess
import tempfile
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from .core import (DEFAULT_VOICES, OUTPUT, ROOT, SAMPLES, SPEEDS, atomic_json,
                   load_items, output_lock, validate_items)
from .export import export_bundle

TOKEN = secrets.token_urlsafe(32)
LOCK = threading.RLock()
JOBS, CATALOGS, CHECKING = {}, {}, set()


def python_for(engine):
    return ROOT / ('.venv-' + engine) / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')


def check_catalog(engine, force=False):
    """Do not block HTTP polling while Python imports model metadata."""
    with LOCK:
        if engine in CHECKING:
            return
        cached = CATALOGS.get(engine)
        if cached and not force and time.monotonic() - cached[0] < 30:
            return
        if not python_for(engine).exists():
            CATALOGS[engine] = (time.monotonic(), {'dependencies_ready': False, 'assets_ready': False,
                'ready': False, 'voices': [], 'message': 'Chưa tạo môi trường. Chạy script cài model.'})
            return
        CHECKING.add(engine)

    def inspect():
        try:
            result = subprocess.run([str(python_for(engine)), '-m', 'pion_audio.probe', '--engine', engine],
                cwd=ROOT, capture_output=True, text=True, encoding='utf-8', timeout=30,
                env={**os.environ, 'PYTHONUTF8': '1'})
            if result.returncode:
                raise ValueError(result.stderr[-500:])
            report = json.loads(result.stdout)
        except Exception as error:
            report = {'dependencies_ready': False, 'assets_ready': False, 'ready': False,
                      'voices': [], 'message': 'Không kiểm tra được môi trường: ' + str(error)[:500]}
        with LOCK:
            CATALOGS[engine] = (time.monotonic(), report)
            CHECKING.discard(engine)
    threading.Thread(target=inspect, daemon=True).start()


def read_json(path, default=None):
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else (default or {})


def state():
    with LOCK:
        engines = {}
        for engine in DEFAULT_VOICES:
            job = JOBS.get(engine, {})
            process = job.get('process')
            running = process is not None and process.poll() is None
            if process and not running and not job.get('checked_after_exit'):
                job['checked_after_exit'] = True
                check_catalog(engine, force=True)
            else:
                check_catalog(engine)
            report = CATALOGS.get(engine, (0, {}))[1]
            folder = OUTPUT / engine
            preview = read_json(folder / 'preview' / 'manifest.json')
            log_path = job.get('log_path', folder / 'worker.log')
            log = ''
            if log_path.exists():
                with log_path.open('rb') as source:
                    source.seek(max(0, source.seek(0, 2) - 8000))
                    log = source.read().decode('utf-8', errors='replace')
            manifest = read_json(folder / 'manifest.json')
            request = read_json(folder / 'request.json')
            if not manifest and request:
                batch_running = running and job.get('operation') in ('batch', 'retry', 'resume')
                manifest = {'profile': request['profile'], 'items': [], 'total': request['total'],
                            'status': 'running' if batch_running else 'failed'}
            engines[engine] = {**report, 'checking': engine in CHECKING,
                'installed': report.get('dependencies_ready', False), 'running': running,
                'has_input': (folder / 'input.json').exists(), 'operation': job.get('operation'), 'manifest': manifest,
                'preview': preview, 'log': log, 'exit_code': process.poll() if process else None}
        return {'token': TOKEN, 'engines': engines, 'samples': load_items(SAMPLES), 'speeds': SPEEDS}


def start_job(engine, payload, operation='batch'):
    if engine not in DEFAULT_VOICES:
        raise ValueError('Model không hợp lệ.')
    if operation not in ('batch', 'preview', 'prepare', 'retry', 'resume'):
        raise ValueError('Thao tác không hợp lệ.')
    with LOCK:
        if any(j['process'].poll() is None for j in JOBS.values()):
            raise ValueError('Một đợt đang chạy. Hãy chờ hoặc dừng trước khi bắt đầu đợt khác.')
        executable = python_for(engine)
        if not executable.exists():
            raise ValueError(f'Chưa cài {engine}. Xem README.')
        if operation in ('retry', 'resume'):
            previous = read_json(OUTPUT / engine / 'manifest.json')
            if operation == 'retry' and not any(r.get('status') == 'error' for r in previous.get('items', [])):
                raise ValueError('Không có mục lỗi để thử lại.')
            profile = previous.get('profile') or read_json(OUTPUT / engine / 'request.json').get('profile')
            if not profile:
                raise ValueError('Không có cấu hình đợt trước để tiếp tục.')
            payload = {**profile, 'items': load_items(OUTPUT / engine / 'input.json')}
        voice = payload.get('voice') or DEFAULT_VOICES[engine]
        speed = float(payload.get('speed', 1))
        if speed not in SPEEDS:
            raise ValueError('Chọn tốc độ trong danh sách cho phép.')
        report = CATALOGS.get(engine, (0, {}))[1]
        if operation == 'prepare':
            if not report.get('dependencies_ready'):
                raise ValueError('Cần cài đủ thư viện trước khi chuẩn bị model.')
            voice, speed = DEFAULT_VOICES[engine], 1.0
        else:
            if not report.get('ready'):
                raise ValueError(report.get('message', 'Đang kiểm tra model, vui lòng chờ.'))
            if voice not in report.get('voices', []):
                raise ValueError('Giọng không có trong danh sách của model đã tải.')
        items = validate_items([{'id': 'preview', 'text': payload.get('text', '我喜欢学习中文。')}]
                              if operation == 'preview' else payload.get('items', load_items(SAMPLES)))
        folder = OUTPUT / engine
        if operation in ('preview', 'prepare'):
            folder = folder / operation
        folder.mkdir(parents=True, exist_ok=True)
        with output_lock(folder):
            (folder / 'STOP').unlink(missing_ok=True)
            manifest = folder / 'manifest.json'
            if manifest.exists():
                history = folder / 'history'
                history.mkdir(exist_ok=True)
                shutil.copyfile(manifest, history / f'{time.time_ns()}.json')
                os.replace(manifest, folder / 'previous-manifest.json')
            atomic_json(folder / 'input.json', items)
            atomic_json(folder / 'request.json', {'profile': {'engine': engine, 'voice': voice, 'speed': speed},
                                                  'total': len(items)})
        log_path = folder / 'worker.log'
        command = [str(executable), '-u', '-m', 'pion_audio.worker', '--engine', engine,
            '--input', str(folder / 'input.json'), '--output', str(folder), '--voice', voice,
            '--speed', str(speed), '--stop-file', str(folder / 'STOP')]
        if operation == 'prepare':
            command.append('--prepare')
        with log_path.open('w', encoding='utf-8') as log:
            process = subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                                        env={**os.environ, 'PYTHONUTF8': '1'})
        JOBS[engine] = {'process': process, 'operation': operation, 'log_path': log_path,
                        'stop_file': folder / 'STOP'}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def headers_for(self, status, size, mime):
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(size))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; style-src 'self'; script-src 'self'; media-src 'self'")

    def send(self, status, data, mime='application/json; charset=utf-8'):
        if isinstance(data, (dict, list)):
            data = json.dumps(data, ensure_ascii=False).encode()
        self.headers_for(status, len(data), mime)
        self.end_headers()
        self.wfile.write(data)

    def valid_host(self):
        return self.headers.get('Host') == f'127.0.0.1:{self.server.server_port}'

    def do_GET(self):
        if not self.valid_host():
            return self.send(403, {'error': 'Chỉ truy cập qua địa chỉ 127.0.0.1.'})
        url = urlsplit(self.path)
        path = url.path
        if path == '/api/state':
            return self.send(200, state())
        if path in ('/', '/app.js', '/style.css'):
            name = 'index.html' if path == '/' else path[1:]
            mime = {'index.html': 'text/html; charset=utf-8', 'app.js': 'text/javascript; charset=utf-8',
                    'style.css': 'text/css; charset=utf-8'}[name]
            return self.send(200, (ROOT / 'web' / name).read_bytes(), mime)
        parts = path.strip('/').split('/')
        if len(parts) == 3 and parts[:2] == ['api', 'export'] and parts[2] in DEFAULT_VOICES:
            engine = parts[2]
            try:
                with LOCK, output_lock(OUTPUT / engine), tempfile.SpooledTemporaryFile(max_size=8*1024*1024) as bundle:
                    if JOBS.get(engine, {}).get('process') and JOBS[engine]['process'].poll() is None:
                        raise ValueError('Chờ đợt xử lý kết thúc trước khi xuất.')
                    export_bundle(OUTPUT / engine, bundle, parse_qs(url.query).get('approved', ['1'])[0] != '0')
                    size = bundle.seek(0, 2)
                    bundle.seek(0)
                    self.headers_for(200, size, 'application/zip')
                    self.send_header('Content-Disposition', f'attachment; filename="pion-{engine}-audio.zip"')
                    self.end_headers()
                    shutil.copyfileobj(bundle, self.wfile)
                return
            except (ValueError, OSError, KeyError) as error:
                return self.send(400, {'error': str(error)})
        if len(parts) == 3 and parts[:2] == ['api', 'manifest'] and parts[2] in DEFAULT_VOICES:
            target = OUTPUT / parts[2] / 'manifest.json'
            if target.exists():
                return self.send(200, target.read_bytes())
        if len(parts) == 3 and parts[0] in ('audio', 'preview') and parts[1] in DEFAULT_VOICES:
            import re
            if re.fullmatch(r'[a-f0-9]{64}\.wav', parts[2]):
                folder = OUTPUT / parts[1]
                if parts[0] == 'preview':
                    folder = folder / 'preview'
                target = folder / 'audio' / parts[2]
                if target.is_file():
                    return self.send(200, target.read_bytes(), 'audio/wav')
        self.send(404, {'error': 'Không tìm thấy.'})

    def do_POST(self):
        if not self.valid_host() or not secrets.compare_digest(self.headers.get('X-Pion-Token', ''), TOKEN):
            return self.send(403, {'error': 'Yêu cầu không hợp lệ. Tải lại trang local.'})
        origin = self.headers.get('Origin')
        if origin and origin != f'http://127.0.0.1:{self.server.server_port}':
            return self.send(403, {'error': 'Origin không hợp lệ.'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 8*1024*1024:
                raise ValueError('Yêu cầu quá lớn hoặc rỗng.')
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise ValueError('Yêu cầu cần là object JSON.')
            engine = payload.get('engine')
            if engine not in DEFAULT_VOICES:
                raise ValueError('Model không hợp lệ.')
            path = urlsplit(self.path).path
            if path in ('/api/start', '/api/preview', '/api/prepare', '/api/retry', '/api/resume'):
                operation = {'/api/start': 'batch', '/api/preview': 'preview',
                             '/api/prepare': 'prepare', '/api/retry': 'retry', '/api/resume': 'resume'}[path]
                start_job(engine, payload, operation)
            elif path == '/api/check':
                check_catalog(engine, force=True)
            elif path == '/api/stop':
                with LOCK:
                    job = JOBS.get(engine)
                    if job and job['process'].poll() is None:
                        job['stop_file'].touch()
            elif path == '/api/review':
                with LOCK, output_lock(OUTPUT / engine):
                    if JOBS.get(engine, {}).get('process') and JOBS[engine]['process'].poll() is None:
                        raise ValueError('Chờ đợt xử lý kết thúc trước khi duyệt.')
                    target = OUTPUT / engine / 'manifest.json'
                    manifest = read_json(target)
                    verdict = payload.get('review')
                    if verdict not in ('approved', 'rejected', 'pending'):
                        raise ValueError('Trạng thái duyệt không hợp lệ.')
                    row = next((r for r in manifest.get('items', []) if r['id'] == payload.get('id')
                                and r.get('status') == 'ready'), None)
                    if row is None or (payload.get('fingerprint') and row['fingerprint'] != payload['fingerprint']):
                        raise ValueError('Audio đã thay đổi. Tải lại kết quả trước khi duyệt.')
                    row['review'] = verdict
                    atomic_json(target, manifest)
            else:
                return self.send(404, {'error': 'Không tìm thấy.'})
            self.send(200, {'ok': True})
        except (ValueError, OSError, TypeError, KeyError) as error:
            self.send(400, {'error': str(error)})


def main():
    parser = argparse.ArgumentParser(description='Pion Audio Tools — giao diện local')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    url = f'http://127.0.0.1:{server.server_port}'
    print(f'Pion Audio Tools: {url}\nCtrl+C để dừng. Giữ cửa sổ này khi tạo audio.', flush=True)
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('Đang dừng công cụ…', flush=True)
    finally:
        for job in JOBS.values():
            if job['process'].poll() is None:
                job['stop_file'].touch()
        server.server_close()


if __name__ == '__main__':
    main()
