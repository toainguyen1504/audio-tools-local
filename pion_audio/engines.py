"""Load only the selected engine, in its own Python environment."""
from pathlib import Path


class KokoroEngine:
    def __init__(self, model_dir: Path, voice: str, speed: float):
        import soundfile as sf
        from kokoro_onnx import Kokoro
        from misaki import zh

        self.sf, self.voice, self.speed = sf, voice, speed
        self.model = Kokoro(str(model_dir / "kokoro-v1.1-zh.onnx"),
                            str(model_dir / "voices-v1.1-zh.bin"),
                            vocab_config=str(model_dir / "config.json"))
        if voice not in self.model.get_voices():
            raise ValueError(f"Giọng không có trong model: {voice}")
        self.g2p = zh.ZHG2P(version="1.1")

    def synthesize(self, text: str, destination: Path):
        phonemes, _ = self.g2p(text)
        if not phonemes or not phonemes.strip():
            raise ValueError("Không chuyển được nội dung thành ngữ âm.")
        audio, rate = self.model.create(phonemes, voice=self.voice,
                                       speed=self.speed, is_phonemes=True)
        self.sf.write(str(destination), audio, rate, subtype="PCM_16")


class MeloEngine:
    def __init__(self, model_dir: Path, voice: str, speed: float):
        import os
        nltk_data = model_dir.parent / "nltk_data"
        if nltk_data.is_dir():
            os.environ.setdefault("NLTK_DATA", str(nltk_data))
        import torch
        from melo.api import TTS

        torch.set_num_threads(min(4, os.cpu_count() or 1))
        self.speed = speed
        self.model = TTS(language="ZH", device="cpu")
        self.speaker = self.model.hps.data.spk2id[voice]

    def synthesize(self, text: str, destination: Path):
        self.model.tts_to_file(text, self.speaker, str(destination), speed=self.speed)


def load_engine(name: str, model_dir: Path, voice: str, speed: float):
    return {"kokoro": KokoroEngine, "melo": MeloEngine}[name](model_dir, voice, speed)
