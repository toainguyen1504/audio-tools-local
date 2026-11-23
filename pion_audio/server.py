"""Loopback-only UI. Model workers run in separate virtual environments."""
import argparse
import json
import os
import secrets
import subprocess
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from .core import DEFAULT_VOICES, MODEL_DIR, OUTPUT, ROOT, SAMPLES, atomic_json, load_items, output_lock, validate_items

TOKEN = secrets.token_urlsafe(32)
LOCK = threading.RLock()
JOBS = {}


def python_for(engine):
    folder = ROOT / (".venv-" + engine)
    return folder / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def state():
    with LOCK:
        engines = {}
        for engine in DEFAULT_VOICES:
            job = JOBS.get(engine, {})
            process = job.get("process")
            running = process is not None and process.poll() is None
            folder = OUTPUT / engine
            manifest = {}
            if (folder / "manifest.json").exists():
                manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
            log = (folder / "worker.log").read_text(encoding="utf-8", errors="replace")[-8000:] if (folder / "worker.log").exists() else ""
            engines[engine] = {"installed": python_for(engine).exists(), "running": running,
                               "manifest": manifest, "log": log,
                               "exit_code": process.poll() if process else None,
                               "assets_ready": engine != "kokoro" or all((MODEL_DIR / n).exists() for n in
                                    ("kokoro-v1.1-zh.onnx", "voices-v1.1-zh.bin", "config.json"))}
        return {"token": TOKEN, "engines": engines, "samples": load_items(SAMPLES)}


def start_job(engine, payload):
    if engine not in DEFAULT_VOICES:
        raise ValueError("Model không hợp lệ.")
    voice = payload.get("voice") or DEFAULT_VOICES[engine]
    speed = float(payload.get("speed", 1.0))
    import math
    import re
    if not isinstance(voice, str) or not re.fullmatch(r"[A-Za-z0-9_]{1,60}", voice):
        raise ValueError("Tên giọng không hợp lệ.")
    if not math.isfinite(speed) or not 0.6 <= speed <= 1.3:
        raise ValueError("Tốc độ cần trong khoảng 0.6–1.3.")
    items = validate_items(payload.get("items", load_items(SAMPLES)))
    with LOCK:
        if any(j["process"].poll() is None for j in JOBS.values()):
            raise ValueError("Một đợt đang chạy. Hãy chờ hoặc dừng trước khi bắt đầu đợt khác.")
        executable = python_for(engine)
        if not executable.exists():
            raise ValueError(f"Chưa cài {engine}. Xem hướng dẫn trong README.")
        folder = OUTPUT / engine
        folder.mkdir(parents=True, exist_ok=True)
        with output_lock(folder):
            (folder / "STOP").unlink(missing_ok=True)
            # A failed startup must not display a previous batch as the new result.
            if (folder / "manifest.json").exists():
                os.replace(folder / "manifest.json", folder / "previous-manifest.json")
            atomic_json(folder / "input.json", items)
        log = (folder / "worker.log").open("w", encoding="utf-8")
        try:
            process = subprocess.Popen([str(executable), "-u", "-m", "pion_audio.worker",
                                        "--engine", engine, "--input", str(folder / "input.json"),
                                        "--output", str(folder), "--voice", voice, "--speed", str(speed),
                                        "--stop-file", str(folder / "STOP")],
                                       cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                                       env={**os.environ, "PYTHONUTF8": "1"})
        finally:
            log.close()
        JOBS[engine] = {"process": process}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def send(self, status, data, mime="application/json; charset=utf-8"):
        if isinstance(data, (dict, list)):
            data = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self'; script-src 'self'; media-src 'self'")
        self.end_headers()
        self.wfile.write(data)

    def valid_host(self):
        return self.headers.get("Host") == f"127.0.0.1:{self.server.server_port}"

    def do_GET(self):
        if not self.valid_host():
            return self.send(403, {"error": "Chỉ truy cập qua địa chỉ 127.0.0.1."})
        path = urlsplit(self.path).path
        if path == "/api/state":
            return self.send(200, state())
        if path in ("/", "/app.js", "/style.css"):
            name = "index.html" if path == "/" else path[1:]
            mime = {"index.html": "text/html; charset=utf-8", "app.js": "text/javascript; charset=utf-8", "style.css": "text/css; charset=utf-8"}[name]
            return self.send(200, (ROOT / "web" / name).read_bytes(), mime)
        parts = path.strip("/").split("/")
        if len(parts) == 3 and parts[:2] == ["api", "manifest"] and parts[2] in DEFAULT_VOICES:
            target = OUTPUT / parts[2] / "manifest.json"
            if target.exists():
                return self.send(200, target.read_bytes())
        if len(parts) == 3 and parts[0] == "audio" and parts[1] in DEFAULT_VOICES:
            import re
            if re.fullmatch(r"[a-f0-9]{64}\.wav", parts[2]):
                target = OUTPUT / parts[1] / "audio" / parts[2]
                if target.is_file():
                    return self.send(200, target.read_bytes(), "audio/wav")
        self.send(404, {"error": "Không tìm thấy."})

    def do_POST(self):
        if not self.valid_host() or not secrets.compare_digest(self.headers.get("X-Pion-Token", ""), TOKEN):
            return self.send(403, {"error": "Yêu cầu không hợp lệ. Tải lại trang local."})
        origin = self.headers.get("Origin")
        if origin and origin != f"http://127.0.0.1:{self.server.server_port}":
            return self.send(403, {"error": "Origin không hợp lệ."})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 8 * 1024 * 1024:
                raise ValueError("Yêu cầu quá lớn hoặc rỗng.")
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise ValueError("Yêu cầu cần là object JSON.")
            engine = payload.get("engine")
            if engine not in DEFAULT_VOICES:
                raise ValueError("Model không hợp lệ.")
            path = urlsplit(self.path).path
            if path == "/api/start":
                start_job(engine, payload)
            elif path == "/api/stop":
                (OUTPUT / engine).mkdir(parents=True, exist_ok=True)
                (OUTPUT / engine / "STOP").touch()
            elif path == "/api/review":
                with LOCK:
                    if JOBS.get(engine, {}).get("process") and JOBS[engine]["process"].poll() is None:
                        raise ValueError("Hãy chờ đợt tạo audio kết thúc trước khi duyệt.")
                    target = OUTPUT / engine / "manifest.json"
                    manifest = json.loads(target.read_text(encoding="utf-8"))
                    verdict = payload.get("review")
                    if verdict not in ("approved", "rejected", "pending"):
                        raise ValueError("Trạng thái duyệt không hợp lệ.")
                    row = next((x for x in manifest["items"] if x["id"] == payload.get("id") and x.get("status") == "ready"), None)
                    if row is None:
                        raise ValueError("Không tìm thấy audio để duyệt.")
                    with output_lock(OUTPUT / engine):
                        row["review"] = verdict
                        atomic_json(target, manifest)
            else:
                return self.send(404, {"error": "Không tìm thấy."})
            self.send(200, {"ok": True})
        except (ValueError, OSError, TypeError) as error:
            self.send(400, {"error": str(error)})


def main():
    parser = argparse.ArgumentParser(description="Pion Audio Tools — giao diện local")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    url = f"http://127.0.0.1:{server.server_port}"
    print(f"Pion Audio Tools: {url}\nCtrl+C để dừng. Giữ cửa sổ này khi tạo audio.", flush=True)
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Đang dừng công cụ…", flush=True)
    finally:
        for engine, job in JOBS.items():
            if job["process"].poll() is None:
                (OUTPUT / engine / "STOP").touch()
        server.server_close()


if __name__ == "__main__":
    main()
