"""Export reviewed results with ID mapping and content-addressed WAVs."""
import json
import re
import wave
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from .core import wav_info


def export_bundle(folder, destination, approved_only=True):
    folder = Path(folder)
    manifest = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
    rows = [r for r in manifest.get('items', []) if r.get('status') == 'ready'
            and (not approved_only or r.get('review') == 'approved')]
    if not rows:
        raise ValueError('Chưa có audio đã duyệt để xuất.' if approved_only else 'Chưa có audio để xuất.')
    included, seen = [], set()
    with ZipFile(destination, 'w', compression=ZIP_DEFLATED) as archive:
        for row in rows:
            key = row.get('fingerprint', '')
            if not re.fullmatch('[a-f0-9]{64}', key):
                raise ValueError('Mã audio không hợp lệ.')
            relative = 'audio/' + key + '.wav'
            source = folder / relative
            try:
                wav_info(source)
            except (OSError, ValueError, EOFError, wave.Error) as error:
                raise ValueError('File audio bị lỗi hoặc thiếu, cần tạo lại trước khi xuất.') from error
            if key not in seen:
                archive.write(source, relative)
                seen.add(key)
            included.append({**row, 'file': relative})
        archive.writestr('manifest.json', json.dumps({
            'profile': manifest['profile'], 'approved_only': approved_only,
            'total': len(included), 'items': included,
        }, ensure_ascii=False, indent=2))
    return len(included)
