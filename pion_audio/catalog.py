"""Read speaker IDs from installed model assets; never invent a voice list."""
import json
import os
from pathlib import Path

from .core import DEFAULT_VOICES, MODEL_DIR

# Keep downloadable checkpoints with the local project, outside Git.
os.environ.setdefault('HF_HOME', str(MODEL_DIR.parent / 'huggingface'))

PREFERRED_KOKORO = ('zf_001', 'zf_002', 'zf_003', 'zm_009', 'zm_010')


def model_assets(engine, model_dir=MODEL_DIR, local_only=True):
    if engine == 'kokoro':
        return {n: model_dir / n for n in ('kokoro-v1.1-zh.onnx', 'voices-v1.1-zh.bin', 'config.json')}
    from huggingface_hub import hf_hub_download
    from huggingface_hub.errors import LocalEntryNotFoundError
    assets = {}
    for name in ('config.json', 'checkpoint.pth'):
        try:
            value = hf_hub_download('myshell-ai/MeloTTS-Chinese', filename=name, local_files_only=True)
        except LocalEntryNotFoundError:
            if local_only:
                raise
            value = hf_hub_download('myshell-ai/MeloTTS-Chinese', filename=name)
        assets[name] = Path(value)
    return assets


def voice_ids(engine, model_dir=MODEL_DIR, local_only=True):
    if engine == 'kokoro':
        import numpy as np
        with np.load(model_dir / 'voices-v1.1-zh.bin', allow_pickle=False) as voices:
            return sorted(v for v in voices.files if v.startswith(('zf_', 'zm_')))
    assets = model_assets(engine, model_dir, local_only)
    config = json.loads(assets['config.json'].read_text(encoding='utf-8'))
    speakers = config['data']['spk2id']
    if not isinstance(speakers, dict) or not speakers:
        raise ValueError('Model không có danh sách speaker hợp lệ.')
    return sorted(speakers)


def validate_voice(engine, voice, model_dir=MODEL_DIR):
    available = voice_ids(engine, model_dir, local_only=False)
    if voice not in available:
        raise ValueError(f'Giọng {voice} không có trong model {engine}.')


def inspect_engine(engine):
    import importlib.util
    from importlib.metadata import version
    from .core import OUTPUT
    required = {'kokoro': ('kokoro_onnx', 'misaki', 'soundfile', 'numpy'),
                'melo': ('melo', 'torch', 'soundfile', 'huggingface_hub')}
    missing = [name for name in required[engine] if importlib.util.find_spec(name) is None]
    result = {'dependencies_ready': not missing, 'missing': missing, 'assets_ready': False,
              'voices': [], 'default_voice': DEFAULT_VOICES[engine], 'prepared': False,
              'ready': False, 'message': 'Thiếu thư viện: ' + ', '.join(missing) if missing else ''}
    if missing:
        return result
    try:
        assets = model_assets(engine)
        if not all(path.is_file() and path.stat().st_size > 0 for path in assets.values()):
            raise ValueError('Chưa tải đầy đủ model.')
        available = voice_ids(engine)
        selected = [v for v in PREFERRED_KOKORO if v in available] if engine == 'kokoro' else available
        if DEFAULT_VOICES[engine] not in selected:
            raise ValueError('Bộ model thiếu giọng mặc định. Kiểm tra lại model đã tải.')
        versions = {name: version(name) for name in
                    (('kokoro-onnx', 'misaki-fork') if engine == 'kokoro' else ('MeloTTS', 'torch'))}
        signature = {'packages': versions, 'assets': {n: [str(p), p.stat().st_size, p.stat().st_mtime_ns]
                                                       for n, p in assets.items()}}
        proof = OUTPUT / engine / 'prepared.json'
        prepared = proof.exists() and json.loads(proof.read_text(encoding='utf-8')) == signature
        result.update(assets_ready=True, voices=selected, signature=signature, prepared=prepared,
                      ready=engine == 'kokoro' or prepared,
                      message='Sẵn sàng' if engine == 'kokoro' or prepared else 'Cần chuẩn bị dữ liệu giọng lần đầu.')
    except Exception as error:
        result['message'] = 'Cần chuẩn bị model: ' + str(error)[:300]
    return result
