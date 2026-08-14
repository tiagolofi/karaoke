from __future__ import annotations

import argparse
from pathlib import Path

from .audit import write_audit_json
from .audio import extract_audio, separate_stems
from .pitch import detect_notes
from .render import render_video, write_ass
from .sync import synchronize
from .transcribe import transcribe


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera um vídeo de karaokê com letras e notas cantadas.")
    parser.add_argument("video", type=Path, help="Arquivo de vídeo de entrada")
    parser.add_argument("-o", "--output", type=Path, default=Path("karaoke.mp4"))
    parser.add_argument("--work-dir", type=Path, default=Path(".karaoke-work"))
    parser.add_argument(
        "--audit-json",
        type=Path,
        default=None,
        help="Arquivo JSON da linha do tempo para auditoria (padrão: <work-dir>/audit.json)",
    )
    parser.add_argument("--model", default="small", help="Modelo Whisper (padrão: small)")
    parser.add_argument("--language", default=None, help="Idioma ISO-639-1, ex.: pt")
    args = parser.parse_args()
    if not args.video.is_file():
        parser.error(f"Vídeo inexistente: {args.video}")

    audio = extract_audio(args.video, args.work_dir / "audio.wav")
    lyrics = transcribe(audio, args.model, args.language)
    vocals, instrumental = separate_stems(audio, args.work_dir / "stems")
    notes = synchronize(lyrics, detect_notes(str(vocals)))
    subtitles = write_ass(lyrics, notes, args.work_dir / "karaoke.ass")
    render_video(args.video, instrumental, subtitles, args.output)
    audit_path = write_audit_json(args.audit_json or args.work_dir / "audit.json", args.video, lyrics, notes)
    print(f"Vídeo pronto: {args.output.resolve()}")
    print(f"Faixa instrumental: {instrumental.resolve()}")
    print(f"Auditoria de legendas: {audit_path.resolve()}")


if __name__ == "__main__":
    main()
