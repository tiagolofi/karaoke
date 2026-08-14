from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from .audit import write_audit_json
from .audio import extract_audio, separate_stems
from .pitch import detect_notes
from .render import render_video, write_ass
from .sync import synchronize
from .transcribe import transcribe


def cleanup_work_dir(work_dir: Path, protected_files: list[Path]) -> None:
    """Remove intermediários sem permitir que resultados finais sejam apagados."""
    resolved_work_dir = work_dir.resolve()
    if resolved_work_dir == resolved_work_dir.parent:
        raise ValueError("Diretório de trabalho inseguro para remoção.")
    if any(item.resolve().is_relative_to(resolved_work_dir) for item in protected_files):
        raise ValueError("O vídeo final ou a auditoria está dentro do diretório de trabalho.")
    if resolved_work_dir.exists():
        shutil.rmtree(resolved_work_dir)


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera um vídeo de karaokê com letras e notas cantadas.")
    parser.add_argument("video", type=Path, help="Arquivo de vídeo de entrada")
    parser.add_argument("-o", "--output", type=Path, default=Path("karaoke.mp4"))
    parser.add_argument("--work-dir", type=Path, default=Path(".karaoke-work"))
    parser.add_argument(
        "--models-dir",
        type=Path,
        default=Path("modelos-baixados"),
        help="Diretório persistente de modelos baixados (padrão: modelos-baixados)",
    )
    parser.add_argument("--keep-work-dir", action="store_true", help="Preserva os arquivos intermediários para depuração")
    parser.add_argument(
        "--audit-json",
        type=Path,
        default=None,
        help="Arquivo JSON da auditoria (padrão: <vídeo-final>.audit.json)",
    )
    parser.add_argument("--model", default="small", help="Modelo Whisper (padrão: small)")
    parser.add_argument("--language", default=None, help="Idioma ISO-639-1, ex.: pt")
    args = parser.parse_args()
    if not args.video.is_file():
        parser.error(f"Vídeo inexistente: {args.video}")

    audio = extract_audio(args.video, args.work_dir / "audio.wav")
    lyrics = transcribe(audio, args.model, args.language)
    vocals, instrumental = separate_stems(audio, args.work_dir / "stems", args.models_dir)
    notes = synchronize(lyrics, detect_notes(str(vocals)))
    subtitles = write_ass(lyrics, notes, args.work_dir / "karaoke.ass")
    render_video(args.video, instrumental, subtitles, args.output)
    audit_destination = args.audit_json or args.output.with_suffix(".audit.json")
    audit_path = write_audit_json(
        audit_destination,
        args.video,
        args.output,
        lyrics,
        notes,
    )
    print(f"Vídeo pronto: {args.output.resolve()}")
    print(f"Faixa instrumental: {instrumental.resolve()}")
    print(f"Modelos baixados: {args.models_dir.resolve()}")
    print(f"Auditoria de legendas: {audit_path.resolve()}")
    if not args.keep_work_dir:
        cleanup_work_dir(args.work_dir, [args.output, audit_path])
        print(f"Intermediários removidos: {args.work_dir.resolve()}")


if __name__ == "__main__":
    main()
