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


def separate_vocals(audio: Path, output_dir: Path) -> Path:
    """Separa voz com Audio Separator, compatível com Python 3.12."""
    from audio_separator.separator import Separator

    output_dir.mkdir(parents=True, exist_ok=True)
    model_dir = output_dir / "models"
    model_dir.mkdir(exist_ok=True)
    separator = Separator(output_dir=str(output_dir), model_file_dir=str(model_dir), output_format="WAV", output_single_stem="Vocals")
    separator.load_model(model_filename="Kim_Vocal_2.onnx")
    outputs = separator.separate(str(audio))
    if not outputs:
        raise RuntimeError("Audio Separator não produziu a faixa vocal.")
    vocal = Path(outputs[0])
    if not vocal.is_absolute():
        vocal = output_dir / vocal
    if not vocal.is_file():
        raise FileNotFoundError(f"Faixa vocal não encontrada: {vocal}")
    return vocal
