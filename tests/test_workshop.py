import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

from pion_audio import catalog, server
from pion_audio.core import SPEEDS, atomic_json, profile_for, run_batch
from pion_audio.export import export_bundle
from test_core import FakeEngine


class CatalogAndSpeedTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.assets = {}
        for name in ('kokoro-v1.1-zh.onnx', 'voices-v1.1-zh.bin', 'config.json'):
            self.assets[name] = self.root / name
            self.assets[name].write_text('{}')

    def test_all_speeds_and_unknown_speeds(self):
        with patch('pion_audio.catalog.validate_voice'), patch('importlib.metadata.version', return_value='test'):
            for speed in SPEEDS:
                self.assertEqual(profile_for('kokoro', 'zf_001', speed, self.root)['speed'], speed)
        for speed in (0, 0.49, 0.9, 1.1, 1.51, float('nan'), float('inf')):
            with self.subTest(speed=speed), self.assertRaises(ValueError):
                profile_for('kokoro', 'zf_001', speed, self.root)

    def test_melo_speakers_come_from_config(self):
        self.assets['config.json'].write_text(json.dumps({'data': {'spk2id': {'ZH': 1, 'other': 2}}}))
        with patch.object(catalog, 'model_assets', return_value=self.assets):
            self.assertEqual(catalog.voice_ids('melo'), ['ZH', 'other'])

    def test_unknown_voice_is_rejected(self):
        with patch.object(catalog, 'voice_ids', return_value=['zf_001']):
            with self.assertRaises(ValueError):
                catalog.validate_voice('kokoro', 'nonexistent')

    def inspect(self, voices):
        with patch('importlib.util.find_spec', return_value=object()), \
             patch('importlib.metadata.version', return_value='test'), \
             patch.object(catalog, 'model_assets', return_value=self.assets), \
             patch.object(catalog, 'voice_ids', return_value=voices):
            return catalog.inspect_engine('kokoro')

    def test_curated_choices_only_include_existing_voices(self):
        result = self.inspect(['zf_001', 'zf_003', 'zf_099', 'zm_009'])
        self.assertEqual(result['voices'], ['zf_001', 'zf_003', 'zm_009'])
        self.assertTrue(result['ready'])

    def test_missing_default_is_not_silently_replaced(self):
        result = self.inspect(['zf_003'])
        self.assertFalse(result['ready'])
        self.assertEqual(result['voices'], [])


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.profile = {'engine': 'kokoro', 'voice': 'zf_001', 'speed': 1}
        self.manifest = run_batch([{'id': 'a', 'text': '银行'}, {'id': 'b', 'text': '你好'}],
                                  self.profile, self.folder, FakeEngine)
        self.manifest['items'][0]['review'] = 'approved'
        atomic_json(self.folder / 'manifest.json', self.manifest)

    def test_approved_only_contains_exact_id_and_file(self):
        data = io.BytesIO()
        self.assertEqual(export_bundle(self.folder, data), 1)
        with ZipFile(data) as archive:
            mapping = json.loads(archive.read('manifest.json'))
            self.assertEqual(mapping['items'][0]['id'], 'a')
            self.assertEqual(mapping['profile'], self.profile)
            self.assertEqual(len(archive.namelist()), 2)

    def test_include_pending_is_explicit(self):
        data = io.BytesIO()
        self.assertEqual(export_bundle(self.folder, data, approved_only=False), 2)

    def test_export_empty_approved_fails_clearly(self):
        self.manifest['items'][0]['review'] = 'rejected'
        atomic_json(self.folder / 'manifest.json', self.manifest)
        with self.assertRaises(ValueError):
            export_bundle(self.folder, io.BytesIO())

    def test_export_rejects_path_escape(self):
        self.manifest['items'][0]['fingerprint'] = '../../outside'
        atomic_json(self.folder / 'manifest.json', self.manifest)
        with self.assertRaises(ValueError):
            export_bundle(self.folder, io.BytesIO())

    def test_regenerated_corrupt_audio_loses_previous_approval(self):
        (self.folder / self.manifest['items'][0]['file']).write_bytes(b'broken')
        result = run_batch([{'id': 'a', 'text': '银行'}], self.profile, self.folder, FakeEngine)
        self.assertEqual(result['items'][0]['review'], 'pending')


class JobTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.executable = self.root / 'python'
        self.executable.touch()
        self.patches = [patch.object(server, 'OUTPUT', self.root),
                       patch.object(server, 'python_for', return_value=self.executable),
                       patch.object(server, 'JOBS', {}),
                       patch.object(server, 'CATALOGS', {'kokoro': (0, {'ready': True,
                           'dependencies_ready': True, 'voices': ['zf_001']})})]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)
        self.process = patch.object(server.subprocess, 'Popen')
        self.spawn = self.process.start()
        self.addCleanup(self.process.stop)
        self.spawn.return_value.poll.return_value = None

    def test_reject_voice_and_speed_before_spawning(self):
        for payload in ({'voice': 'fake', 'speed': 1}, {'voice': 'zf_001', 'speed': 0.9}):
            with self.assertRaises(ValueError):
                server.start_job('kokoro', payload)
        self.spawn.assert_not_called()

    def test_preview_uses_separate_results_folder(self):
        server.start_job('kokoro', {'voice': 'zf_001', 'speed': .5, 'text': '你好'}, 'preview')
        self.assertTrue((self.root / 'kokoro/preview/input.json').exists())
        self.assertFalse((self.root / 'kokoro/manifest.json').exists())
        self.assertIn('--speed', self.spawn.call_args.args[0])

    def test_retry_reuses_original_input_and_profile(self):
        folder = self.root / 'kokoro'
        atomic_json(folder / 'input.json', [{'id': 'original', 'text': '你好'}])
        atomic_json(folder / 'manifest.json', {'profile': {'voice': 'zf_001', 'speed': .75},
                    'items': [{'id': 'original', 'status': 'error'}]})
        server.start_job('kokoro', {'voice': 'fake', 'speed': 1.5}, 'retry')
        args = self.spawn.call_args.args[0]
        self.assertEqual(args[args.index('--speed')+1], '0.75')
        self.assertEqual(json.loads((folder / 'input.json').read_text())[0]['id'], 'original')
        self.assertEqual(len(list((folder / 'history').glob('*.json'))), 1)

    def test_busy_does_not_overwrite_inputs(self):
        server.start_job('kokoro', {'voice': 'zf_001', 'items': [{'id': 'a', 'text': '好'}]})
        with self.assertRaises(ValueError):
            server.start_job('kokoro', {'voice': 'zf_001', 'items': [{'id': 'b', 'text': '坏'}]})
        self.assertEqual(json.loads((self.root / 'kokoro/input.json').read_text())[0]['id'], 'a')

    def test_resume_after_failed_startup_uses_saved_request(self):
        folder = self.root / 'kokoro'
        atomic_json(folder / 'input.json', [{'id': 'original', 'text': '你好'}])
        atomic_json(folder / 'request.json', {'profile': {'engine': 'kokoro', 'voice': 'zf_001', 'speed': 1.5}, 'total': 1})
        server.start_job('kokoro', {}, 'resume')
        args = self.spawn.call_args.args[0]
        self.assertEqual(args[args.index('--speed')+1], '1.5')
