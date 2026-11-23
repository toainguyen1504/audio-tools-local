"""Validated input, content-addressed WAVs, durable progress and resume."""
import hashlib
import json
import math
import os
import re
import time
import unicodedata
import wave
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODEL_DIR = ROOT / "models" / "kokoro-zh"
OUTPUT = ROOT / "output"
SAMPLES = ROOT / "samples" / "mandarin-20.json"
DEFAULT_VOICES = {"kokoro": "zf_001", "melo": "ZH"}
SPEEDS = (0.5, 0.75, 0.85, 1.0, 1.25, 1.5)


@contextmanager
def output_lock(output):
    """An OS lock releases even when a worker crashes (Windows and Unix)."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    with (output / ".worker.lock").open("a+b") as handle:
        handle.seek(0, 2)
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            raise ValueError("Thư mục đang được một tiến trình khác sử dụng.") from error
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, path)


def validate_items(items):
    if not isinstance(items, list) or not 1 <= len(items) <= 10000:
        raise ValueError("Danh sách cần có 1–10.000 mục.")
    clean, seen = [], set()
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("Mỗi mục phải là object JSON.")
        identifier = item.get("id")
        text = item.get("text")
        if not isinstance(identifier, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,100}", identifier):
            raise ValueError("ID chỉ gồm chữ Latin, số, _, -, ., :; tối đa 100 ký tự.")
        if identifier in seen:
            raise ValueError(f"ID bị trùng: {identifier}")
        if not isinstance(text, str) or not 1 <= len(text.strip()) <= 300:
            raise ValueError(f"{identifier}: nội dung cần có 1–300 ký tự.")
        seen.add(identifier)
        row = {"id": identifier, "text": unicodedata.normalize("NFC", text.strip())}
        for field in ("pinyin", "meaning", "kind", "note"):
            value = item.get(field, "")
            if not isinstance(value, str) or len(value) > 1000:
                raise ValueError(f"{identifier}: trường {field} không hợp lệ.")
            row[field] = value
        clean.append(row)
    return clean


def load_items(path):
    return validate_items(json.loads(Path(path).read_text(encoding="utf-8-sig")))


def sha256_file(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def profile_for(engine, voice, speed, model_dir=MODEL_DIR):
    if engine not in DEFAULT_VOICES:
        raise ValueError("Model không hợp lệ.")
    if not isinstance(speed, (float, int)) or not math.isfinite(speed) or speed not in SPEEDS:
        raise ValueError("Tốc độ hợp lệ: 0.5, 0.75, 0.85, 1.0, 1.25, 1.5.")
    if not isinstance(voice, str) or not re.fullmatch(r"[A-Za-z0-9_]{1,60}", voice):
        raise ValueError("Tên giọng không hợp lệ.")
    from .catalog import validate_voice
    validate_voice(engine, voice, model_dir)
    from importlib.metadata import version
    packages = ("kokoro-onnx", "misaki-fork") if engine == "kokoro" else ("MeloTTS", "torch")
    profile = {"engine": engine, "voice": voice, "speed": float(speed), "pipeline": 1,
               "packages": {name: version(name) for name in packages}}
    if engine == "kokoro":
        profile["assets"] = {name: sha256_file(model_dir / name) for name in
                             ("kokoro-v1.1-zh.onnx", "voices-v1.1-zh.bin", "config.json")}
    else:
        from .catalog import model_assets
        profile["model"] = "myshell-ai/MeloTTS-Chinese"
        profile["source_revision"] = "209145371cff8fc3bd60d7be902ea69cbdb7965a"
        profile["assets"] = {name: sha256_file(path) for name, path in
                             model_assets(engine, model_dir, local_only=False).items()}
    return profile


def fingerprint(item, profile):
    # Reading is part of identity: 行 xíng and 行 háng must not share a cache key.
    payload = {"text": item["text"], "pinyin": item.get("pinyin", ""), "profile": profile}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def wav_info(path):
    with wave.open(str(path), "rb") as audio:
        if audio.getnframes() == 0 or audio.getframerate() == 0 or audio.getsampwidth() != 2:
            raise ValueError("File WAV không hợp lệ hoặc rỗng.")
        return {"duration": round(audio.getnframes() / audio.getframerate(), 3),
                "sample_rate": audio.getframerate()}


def run_batch(items, profile, output, engine_factory, stopped=lambda: False):
    items = validate_items(items)
    output = Path(output)
    audio_dir = output / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output / "manifest.json"
    previous_path = manifest_path if manifest_path.exists() else output / "previous-manifest.json"
    previous = json.loads(previous_path.read_text(encoding="utf-8")) if previous_path.exists() else {}
    old = {(row["id"], row["fingerprint"]): row for row in previous.get("items", [])}
    manifest = {"profile": profile, "status": "running", "items": [], "total": len(items)}
    engine = None
    atomic_json(manifest_path, manifest)
    for item in items:
        if stopped():
            manifest["status"] = "stopped"
            break
        key = fingerprint(item, profile)
        target = audio_dir / (key + ".wav")
        row = {**item, "fingerprint": key, "review": "pending"}
        loading_engine = False
        cached = old.get((item["id"], key), {})
        started = time.monotonic()
        try:
            try:
                info = wav_info(target)
                reused = True
            except (OSError, EOFError, wave.Error, ValueError):
                if engine is None:
                    loading_engine = True
                    engine = engine_factory()
                    loading_engine = False
                temporary = audio_dir / (key + ".part.wav")
                try:
                    engine.synthesize(item["text"], temporary)
                    info = wav_info(temporary)
                    os.replace(temporary, target)
                finally:
                    temporary.unlink(missing_ok=True)
                reused = False
            row.update(info, status="ready", file="audio/" + target.name,
                       reused=reused, review=cached.get("review", "pending") if reused else "pending",
                       seconds=round(time.monotonic() - started, 3))
        except Exception as error:
            row.update(status="error", error=str(error)[:1000])
            if loading_engine:
                manifest["status"] = "failed"
                manifest["error"] = "Không nạp được model: " + str(error)[:1000]
        manifest["items"].append(row)
        atomic_json(manifest_path, manifest)
        print(json.dumps({"id": item["id"], "status": row["status"],
                          "done": len(manifest["items"]), "total": len(items),
                          **({"error": row["error"]} if "error" in row else {})}, ensure_ascii=False), flush=True)
        if manifest["status"] == "failed":
            break
    if manifest["status"] == "running":
        manifest["status"] = "completed_with_errors" if any(x["status"] == "error" for x in manifest["items"]) else "completed"
    atomic_json(manifest_path, manifest)
    return manifest
