"""Optional real-model smoke check. Run with the selected model's Python venv."""
import argparse
import json
from pathlib import Path

from pion_audio.catalog import voice_ids
from pion_audio.core import DEFAULT_VOICES, MODEL_DIR, OUTPUT, SPEEDS, wav_info
from pion_audio.engines import load_engine

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--engine', choices=DEFAULT_VOICES, required=True)
    name = parser.parse_args().engine
    directory = OUTPUT / ('smoke-' + name)
    directory.mkdir(parents=True, exist_ok=True)
    engine = load_engine(name, MODEL_DIR, DEFAULT_VOICES[name], 1)
    results = {}
    for speed in SPEEDS:
        engine.speed = speed
        path = directory / f'speed-{speed}.wav'
        engine.synthesize('我喜欢学习中文。', path)
        results[str(speed)] = wav_info(path)['duration']
    assert results['0.5'] > results['1.5'], results
    if name == 'kokoro':
        for voice in ('zf_001', 'zf_002', 'zf_003', 'zm_009', 'zm_010'):
            assert voice in voice_ids(name)
            engine.voice, engine.speed = voice, 1
            path = directory / (voice + '.wav')
            engine.synthesize('我喜欢学习中文。', path)
            wav_info(path)
    print(json.dumps({'engine': name, 'durations': results, 'status': 'passed'}))
