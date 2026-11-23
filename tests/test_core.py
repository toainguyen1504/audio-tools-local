import json
import tempfile
import unittest
import wave
from pathlib import Path

from pion_audio.core import atomic_json, fingerprint, load_items, output_lock, run_batch, validate_items, wav_info


class FakeEngine:
    def __init__(self):
        self.calls = []

    def synthesize(self, text, destination):
        self.calls.append(text)
        if text == "失败":
            raise ValueError("test failure")
        with wave.open(str(destination), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(24000)
            wav.writeframes(b"\0\0" * 2400)


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.output = Path(self.tmp.name)
        self.items = validate_items([{"id": "a", "text": "银行", "pinyin": "yínháng"},
                                     {"id": "b", "text": "你好"}])
        self.profile = {"engine": "test", "voice": "one", "speed": 1}
        self.engine = FakeEngine()

    def run_batch(self, items=None, stop=lambda: False):
        return run_batch(items or self.items, self.profile, self.output, lambda: self.engine, stop)

    def test_successful_wav_and_manifest(self):
        result = self.run_batch()
        self.assertEqual(result["status"], "completed")
        for row in result["items"]:
            self.assertEqual(row["review"], "pending")
            self.assertEqual(wav_info(self.output / row["file"])["duration"], .1)

    def test_resume_does_not_load_model_and_preserves_review(self):
        result = self.run_batch()
        result["items"][0]["review"] = "approved"
        atomic_json(self.output / "manifest.json", result)
        result = run_batch(self.items, self.profile, self.output,
                           lambda: self.fail("Cache hit should not load model"))
        self.assertTrue(all(r["reused"] for r in result["items"]))
        self.assertEqual(result["items"][0]["review"], "approved")

    def test_same_text_different_reading_not_shared(self):
        self.assertNotEqual(fingerprint(self.items[0], self.profile),
                            fingerprint({**self.items[0], "pinyin": "yínxíng"}, self.profile))

    def test_different_voice_or_speed_not_shared(self):
        key = fingerprint(self.items[0], self.profile)
        self.assertNotEqual(key, fingerprint(self.items[0], {**self.profile, "voice": "two"}))
        self.assertNotEqual(key, fingerprint(self.items[0], {**self.profile, "speed": .85}))

    def test_identical_content_different_id_reuses_audio(self):
        self.run_batch()
        result = self.run_batch([{**self.items[0], "id": "other"}])
        self.assertTrue(result["items"][0]["reused"])
        self.assertEqual(len(self.engine.calls), 2)

    def test_invalid_cache_regenerated(self):
        result = self.run_batch()
        (self.output / result["items"][0]["file"]).write_bytes(b"truncated")
        self.run_batch()
        self.assertEqual(len(self.engine.calls), 3)

    def test_errors_do_not_stop_later_items(self):
        result = self.run_batch([{"id": "error", "text": "失败"}, *self.items])
        self.assertEqual(result["status"], "completed_with_errors")
        self.assertEqual([x["status"] for x in result["items"]], ["error", "ready", "ready"])

    def test_failed_engine_load_stops_instead_of_retrying_every_item(self):
        calls = []
        def broken():
            calls.append(1)
            raise RuntimeError("Missing model")
        result = run_batch(self.items, self.profile, self.output, broken)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(result["items"]), 1)

    def test_stop_then_resume(self):
        result = self.run_batch(stop=lambda: bool(self.engine.calls))
        self.assertEqual(result["status"], "stopped")
        self.assertEqual(len(result["items"]), 1)
        self.run_batch()
        self.assertEqual(len(self.engine.calls), 2)

    def test_previous_manifest_preserves_review_after_ui_restart(self):
        result = self.run_batch()
        result["items"][0]["review"] = "rejected"
        atomic_json(self.output / "previous-manifest.json", result)
        (self.output / "manifest.json").unlink()
        self.assertEqual(self.run_batch()["items"][0]["review"], "rejected")

    def test_reject_duplicate_path_and_bad_text(self):
        for items in ([self.items[0], self.items[0]], [{"id": "../escape", "text": "好"}],
                      [{"id": "a", "text": " "}], [{"id": "a", "text": "好" * 301}],
                      [{"id": "a", "text": "好", "pinyin": []}], [], {}):
            with self.subTest(items=items), self.assertRaises(ValueError):
                validate_items(items)

    def test_utf8_bom_input(self):
        path = self.output / "input.json"
        path.write_text(json.dumps(self.items, ensure_ascii=False), encoding="utf-8-sig")
        self.assertEqual(load_items(path), self.items)

    def test_output_lock_blocks_other_writer(self):
        with output_lock(self.output):
            with self.assertRaises(ValueError):
                with output_lock(self.output):
                    pass
        with output_lock(self.output):
            pass
