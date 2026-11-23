import argparse
import signal
import sys
import traceback
from pathlib import Path

from .core import DEFAULT_VOICES, MODEL_DIR, OUTPUT, SAMPLES, atomic_json, load_items, output_lock, profile_for, run_batch
from .engines import load_engine


def main():
    parser = argparse.ArgumentParser(description="Tạo audio tiếng Trung theo lô; tự bỏ qua file đã có.")
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--engine", choices=DEFAULT_VOICES, required=True)
    parser.add_argument("--input", type=Path, default=SAMPLES)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--voice")
    parser.add_argument("--speed", type=float, default=1.0)
    parser.add_argument("--model-dir", type=Path, default=MODEL_DIR)
    parser.add_argument("--stop-file", type=Path, help="Dùng nội bộ bởi giao diện local")
    args = parser.parse_args()
    stopped = False

    def stop(*_):
        nonlocal stopped
        stopped = True

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    voice = args.voice or DEFAULT_VOICES[args.engine]
    output = args.output or OUTPUT / args.engine
    try:
        if args.prepare:
            from .catalog import inspect_engine, model_assets
            if args.engine == "kokoro":
                import subprocess
                subprocess.run([sys.executable, "-m", "pion_audio.download"], check=True)
            else:
                model_assets("melo", local_only=False)
            profile = profile_for(args.engine, voice, args.speed, args.model_dir)
            if stopped or (args.stop_file is not None and args.stop_file.exists()):
                return 0
            from .core import wav_info
            with output_lock(output):
                model = load_engine(args.engine, args.model_dir, voice, args.speed)
                model.synthesize("你好。", output / "check.wav")
                wav_info(output / "check.wav")
            report = inspect_engine(args.engine)
            atomic_json(OUTPUT / args.engine / "prepared.json", report["signature"])
            print("Model và dữ liệu giọng đã sẵn sàng.", flush=True)
            return 0
        if args.engine == "melo" and (OUTPUT / "melo" / "prepared.json").exists():
            import os
            os.environ.setdefault("HF_HUB_OFFLINE", "1")
        items = load_items(args.input)
        print("Đang kiểm tra model và nạp bộ tạo giọng…", flush=True)
        profile = profile_for(args.engine, voice, args.speed, args.model_dir)
        with output_lock(output):
            result = run_batch(items, profile, output,
                               lambda: load_engine(args.engine, args.model_dir, voice, args.speed),
                               lambda: stopped or (args.stop_file is not None and args.stop_file.exists()))
        return 1 if result["status"] in ("completed_with_errors", "failed") else 0
    except Exception as error:
        print(f"Không thể tạo audio: {error}", file=sys.stderr, flush=True)
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
