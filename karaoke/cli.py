from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from .audit import write_audit_json
from .audio import extract_audio, separate_stems
from .pitch import detect_notes
from .render import render_instrumental_audio, render_video, write_lyrics_json
from .sync import notes_with_lyrics, synchronize
from .transcribe import transcribe
from .variants import VARIANT_SEMITONES, transpose_notes, variant_directory


def cleanup_work_dir(work_dir: Path, protected_files: list[Path]) -> None:
    """Remove intermediários sem permitir que artefatos finais sejam apagados."""
    resolved_work_dir = work_dir.resolve()
    if resolved_work_dir == resolved_work_dir.parent:
        raise ValueError("Diretório de trabalho inseguro para remoção.")
    if any(item.resolve().is_relative_to(resolved_work_dir) for item in protected_files):
        raise ValueError("Um artefato final está dentro do diretório de trabalho.")
    if resolved_work_dir.exists():
        shutil.rmtree(resolved_work_dir)


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera sete variantes de karaokê, do transpose -3 ao +3.")
    parser.add_argument("video", type=Path, help="Arquivo de vídeo de entrada")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("videos/karaoke.mp4"),
        help="Nome da coleção de variantes (padrão: karaoke, derivado deste caminho)",
    )
    parser.add_argument("--work-dir", type=Path, default=Path(".karaoke-work"))
    parser.add_argument(
        "--variants-dir",
        type=Path,
        default=Path("videos/variantes"),
        help="Pasta das coleções de variantes (padrão: videos/variantes)",
    )
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
        help="Obsoleto: cada variante recebe seu próprio audit no diretório de variantes.",
    )
    parser.add_argument(
        "--lyrics-json",
        type=Path,
        default=None,
        help="Obsoleto: cada variante recebe seu próprio lyrics no diretório de variantes.",
    )
    parser.add_argument("--model", default="small", help="Modelo Whisper (padrão: small)")
    parser.add_argument("--language", default=None, help="Idioma ISO-639-1, ex.: pt")
    args = parser.parse_args()
    if not args.video.is_file():
        parser.error(f"Vídeo inexistente: {args.video}")

    if args.audit_json or args.lyrics_json:
        parser.error("--audit-json e --lyrics-json não são compatíveis com a geração de variantes.")

    audio = extract_audio(args.video, args.work_dir / "audio.wav")
    vocals, instrumental = separate_stems(audio, args.work_dir / "stems", args.models_dir)
    lyrics = transcribe(vocals, args.model, args.language)
    notes = notes_with_lyrics(synchronize(lyrics, detect_notes(str(vocals))))
    collection_dir = args.variants_dir / args.output.stem
    protected_files: list[Path] = []
    lyrics_path = write_lyrics_json(lyrics, collection_dir / "lyrics.json")
    protected_files.append(lyrics_path)
    for semitones in VARIANT_SEMITONES:
        destination = variant_directory(args.variants_dir, args.output.stem, semitones)
        audio_path = render_instrumental_audio(instrumental, destination / "instrumental.m4a", semitones)
        video_path = render_video(args.video, audio_path, destination / "karaoke.mp4")
        audit_path = write_audit_json(
            destination / "karaoke.audit.json",
            args.video,
            video_path,
            lyrics,
            transpose_notes(notes, semitones),
        )
        protected_files.extend([audio_path, video_path, audit_path])
        print(f"Variante {semitones:+d}: {video_path.resolve()}")
    print(f"Coleção de variantes: {collection_dir.resolve()}")
    print(f"Modelos baixados: {args.models_dir.resolve()}")
    if not args.keep_work_dir:
        cleanup_work_dir(args.work_dir, protected_files)
        print(f"Intermediários removidos: {args.work_dir.resolve()}")


if __name__ == "__main__":
    main()
