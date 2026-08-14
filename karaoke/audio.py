from __future__ import annotations

import subprocess
from pathlib import Path


def extract_audio(video: Path, output: Path) -> Path:
    """Extrai áudio PCM mono, ideal para Whisper e análise tonal."""
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(video), "-vn", "-ac", "1", "-ar", "44100", "-c:a", "pcm_s16le", str(output)],
        check=True,
    )
    return output


def separate_stems(audio: Path, output_dir: Path) -> tuple[Path, Path]:
    """Separa vocais e instrumental com Audio Separator."""
    from audio_separator.separator import Separator

    output_dir.mkdir(parents=True, exist_ok=True)
    model_dir = output_dir / "models"
    model_dir.mkdir(exist_ok=True)
    separator = Separator(output_dir=str(output_dir), model_file_dir=str(model_dir), output_format="WAV")
    separator.load_model(model_filename="Kim_Vocal_2.onnx")
    output_paths = [Path(item) for item in separator.separate(str(audio))]
    output_paths = [item if item.is_absolute() else output_dir / item for item in output_paths]
    vocals = next((item for item in output_paths if "vocal" in item.name.lower()), None)
    instrumental = next(
        (item for item in output_paths if any(name in item.name.lower() for name in ("instrumental", "karaoke", "no_vocals"))),
        None,
    )
    if not vocals or not vocals.is_file():
        raise FileNotFoundError("Audio Separator não produziu a faixa vocal.")
    if not instrumental or not instrumental.is_file():
        raise FileNotFoundError("Audio Separator não produziu a faixa instrumental.")
    return vocals, instrumental
