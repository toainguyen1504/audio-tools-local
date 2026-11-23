"""Optional full loopback/worker check; requires both model environments installed."""
import io
import json
import threading
import time
import urllib.error
import urllib.request
from zipfile import ZipFile

from pion_audio import server
from pion_audio.core import OUTPUT, atomic_json

if __name__ == '__main__':
    http = server.ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
    thread = threading.Thread(target=http.serve_forever, daemon=True)
    thread.start()
    base = f'http://127.0.0.1:{http.server_port}'

    def get(path):
        return urllib.request.urlopen(base + path)

    def post(path, payload):
        request = urllib.request.Request(base + path, data=json.dumps(payload).encode(),
            headers={'X-Pion-Token': server.TOKEN, 'Content-Type': 'application/json'})
        return json.load(urllib.request.urlopen(request))

    def wait_job(name):
        process = server.JOBS[name]['process']
        process.wait(timeout=180)
        assert process.returncode == 0, server.state()['engines'][name]['log']

    try:
        for _ in range(100):
            s = server.state()
            if all(info.get('ready') for info in s['engines'].values()):
                break
            time.sleep(.2)
        assert all(info.get('ready') for info in s['engines'].values()), s
        for name, speed in [('kokoro', .75), ('melo', 1.25)]:
            post('/api/preview', {'engine': name, 'voice': 'zf_001' if name == 'kokoro' else 'ZH',
                                  'speed': speed, 'text': '我喜欢学习中文。'})
            wait_job(name)
            preview = server.state()['engines'][name]['preview']
            key = preview['items'][0]['fingerprint']
            with get(f'/preview/{name}/{key}.wav') as response:
                assert response.read(4) == b'RIFF'
            assert preview['profile']['speed'] == speed
        items = [{'id': 'http:a', 'text': '银行'}, {'id': 'http:b', 'text': '你好'}, {'id': 'http:c', 'text': '学习'}]
        post('/api/start', {'engine': 'kokoro', 'voice': 'zf_001', 'speed': .75, 'items': items})
        wait_job('kokoro')
        folder = OUTPUT / 'kokoro'
        m = json.loads((folder / 'manifest.json').read_text())
        first = m['items'][0]
        post('/api/review', {'engine': 'kokoro', 'id': first['id'], 'fingerprint': first['fingerprint'], 'review': 'approved'})
        with get('/api/export/kokoro?approved=1') as response:
            with ZipFile(io.BytesIO(response.read())) as archive:
                exported = json.loads(archive.read('manifest.json'))
                assert exported['total'] == 1 and exported['items'][0]['id'] == first['id']
        with get('/api/export/kokoro?approved=0') as response:
            with ZipFile(io.BytesIO(response.read())) as archive:
                assert json.loads(archive.read('manifest.json'))['total'] == 3
        m = json.loads((folder / 'manifest.json').read_text())
        last = m['items'][-1]
        (folder / last['file']).write_bytes(b'broken')
        last['status'] = 'error'
        atomic_json(folder / 'manifest.json', m)
        post('/api/retry', {'engine': 'kokoro'})
        wait_job('kokoro')
        result = json.loads((folder / 'manifest.json').read_text())
        assert len(result['items']) == 3 and sum(r['reused'] for r in result['items']) == 2
        assert result['items'][0]['review'] == 'approved'
        assert result['items'][-1]['review'] == 'pending'
        assert list((folder / 'history').glob('*.json'))
        print('HTTP model smoke passed: both previews, real batch, review, ZIP approved/all, retry/cache/history.')
    finally:
        http.shutdown()
        http.server_close()
        thread.join()
