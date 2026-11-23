import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

from pion_audio import server
from pion_audio.core import atomic_json


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.output = Path(cls.tmp.name)
        cls.patch = patch.object(server, "OUTPUT", cls.output)
        cls.patch.start()
        cls.http = server.ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        cls.thread = threading.Thread(target=cls.http.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.http.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown()
        cls.http.server_close()
        cls.thread.join()
        cls.patch.stop()
        cls.tmp.cleanup()

    def request(self, path, data=None, token=server.TOKEN, headers=None):
        request = urllib.request.Request(self.base + path,
                    data=json.dumps(data).encode() if data is not None else None,
                    headers={"X-Pion-Token": token, **(headers or {})})
        return urllib.request.urlopen(request)

    def test_state_and_page(self):
        with self.request("/api/state") as response:
            result = json.load(response)
        self.assertEqual(len(result["samples"]), 20)
        self.assertEqual(result["token"], server.TOKEN)
        with self.request("/") as response:
            self.assertIn(b"Pion", response.read())

    def test_cross_origin_mutation_rejected(self):
        for token, headers in (("bad", {}), (server.TOKEN, {"Origin": "https://example.com"})):
            with self.assertRaises(urllib.error.HTTPError) as error:
                self.request("/api/start", {"engine": "kokoro"}, token=token, headers=headers)
            self.assertEqual(error.exception.code, 403)

    def test_host_rebinding_rejected(self):
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.request("/api/state", headers={"Host": "evil.example"})
        self.assertEqual(error.exception.code, 403)

    def test_audio_route_cannot_read_other_files(self):
        for path in ("/audio/kokoro/../../../README.md", "/audio/kokoro/manifest.json", "/.env"):
            with self.assertRaises(urllib.error.HTTPError) as error:
                self.request(path)
            self.assertEqual(error.exception.code, 404)

    def test_invalid_jobs_fail_before_spawning(self):
        for data in ({"engine": "evil"}, {"engine": "kokoro", "speed": 100},
                     {"engine": "kokoro", "items": [{"id": "../a", "text": "好"}]}):
            with self.assertRaises(urllib.error.HTTPError) as error:
                self.request("/api/start", data)
            self.assertEqual(error.exception.code, 400)

    def test_review_persists(self):
        target = self.output / "kokoro" / "manifest.json"
        atomic_json(target, {"items": [{"id": "one", "status": "ready", "review": "pending"}]})
        with self.request("/api/review", {"engine": "kokoro", "id": "one", "review": "approved"}) as response:
            self.assertTrue(json.load(response)["ok"])
        self.assertEqual(json.loads(target.read_text())["items"][0]["review"], "approved")


if __name__ == "__main__":
    unittest.main()
