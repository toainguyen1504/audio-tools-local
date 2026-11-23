"""Download upstream Kokoro Mandarin assets without committing model files."""
import argparse
import json
import os
import urllib.request

from .core import MODEL_DIR, atomic_json, sha256_file

RELEASE = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/"
ASSETS = {
    "kokoro-v1.1-zh.onnx": RELEASE + "kokoro-v1.1-zh.onnx",
    "voices-v1.1-zh.bin": RELEASE + "voices-v1.1-zh.bin",
    "config.json": "https://huggingface.co/hexgrad/Kokoro-82M-v1.1-zh/resolve/main/config.json",
}


def main():
    parser = argparse.ArgumentParser(description="Tải model Kokoro tiếng Trung (khoảng 350 MB).")
    parser.add_argument("--force", action="store_true", help="Tải lại các file đã có")
    args = parser.parse_args()
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    receipt = {}
    for name, url in ASSETS.items():
        path = MODEL_DIR / name
        if args.force or not path.exists():
            print(f"Đang tải {name}…", flush=True)
            temporary = path.with_suffix(path.suffix + ".download")
            try:
                request = urllib.request.Request(url, headers={"User-Agent": "PionAudioTools/0.1"})
                with urllib.request.urlopen(request, timeout=120) as response, temporary.open("wb") as target:
                    expected = response.headers.get("Content-Length")
                    size = 0
                    while chunk := response.read(1024 * 1024):
                        target.write(chunk)
                        size += len(chunk)
                    if not size or (expected and size != int(expected)):
                        raise ValueError(f"Tải chưa đầy đủ: {name}")
                if name.endswith(".json"):
                    config = json.loads(temporary.read_text(encoding="utf-8"))
                    if "vocab" not in config:
                        raise ValueError("Config thiếu vocab.")
                elif size < 100000:
                    raise ValueError(f"File model quá nhỏ: {name}")
                os.replace(temporary, path)
            finally:
                temporary.unlink(missing_ok=True)
        receipt[name] = {"url": url, "sha256": sha256_file(path)}
    atomic_json(MODEL_DIR / "download-receipt.json", receipt)
    print("Model đã sẵn sàng. SHA256 lưu trong download-receipt.json.")


if __name__ == "__main__":
    main()
