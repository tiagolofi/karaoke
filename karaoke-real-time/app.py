from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import quote

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from karaoke.evaluation import evaluate_recording

VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov", ".webm", ".avi"}
WEB_DIR = Path(__file__).parent / "web"
MAX_RECORDING_SIZE_BYTES = 50 * 1024 * 1024


def sidecar_audit(video: Path) -> Path:
    return video.with_suffix(".audit.json")


def video_entries(library: Path) -> list[dict[str, object]]:
    return [
        {"name": video.name, "url": f"/media/{quote(video.name)}", "has_audit": sidecar_audit(video).is_file()}
        for video in sorted(library.iterdir(), key=lambda item: item.name.lower())
        if video.is_file() and video.suffix.lower() in VIDEO_EXTENSIONS
    ]


def resolve_video(library: Path, filename: str) -> Path:
    candidate = (library / filename).resolve()
    if candidate.parent != library.resolve() or not candidate.is_file() or candidate.suffix.lower() not in VIDEO_EXTENSIONS:
        raise HTTPException(status_code=404, detail="Vídeo não encontrado")
    return candidate


def recording_suffix(content_type: str | None) -> str:
    if content_type and "wav" in content_type:
        return ".wav"
    if content_type and "ogg" in content_type:
        return ".ogg"
    if content_type and "mp4" in content_type:
        return ".m4a"
    return ".webm"


def create_app(library: Path) -> FastAPI:
    library = library.resolve()
    if not library.is_dir():
        raise NotADirectoryError(f"Biblioteca inexistente: {library}")
    app = FastAPI(title="Karaoke Real Time")

    @app.get("/api/videos")
    def list_videos() -> list[dict[str, object]]:
        return video_entries(library)

    @app.get("/api/videos/{filename}/audit")
    def get_audit(filename: str) -> FileResponse:
        audit = sidecar_audit(resolve_video(library, filename))
        if not audit.is_file():
            raise HTTPException(status_code=404, detail="Auditoria não encontrada")
        return FileResponse(audit, media_type="application/json")

    @app.post("/api/videos/{filename}/evaluate")
    async def evaluate_video(filename: str, request: Request, tolerance_half_steps: int = 1) -> dict[str, int | float]:
        if not 0 <= tolerance_half_steps <= 12:
            raise HTTPException(status_code=422, detail="Tolerância inválida")
        audit = sidecar_audit(resolve_video(library, filename))
        if not audit.is_file():
            raise HTTPException(status_code=404, detail="Auditoria não encontrada")
        recording = await request.body()
        if not recording:
            raise HTTPException(status_code=400, detail="Gravação vazia")
        if len(recording) > MAX_RECORDING_SIZE_BYTES:
            raise HTTPException(status_code=413, detail="Gravação excede o limite de 50 MB")
        try:
            audit_payload = json.loads(audit.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise HTTPException(status_code=500, detail="Auditoria inválida") from error
        with tempfile.TemporaryDirectory(prefix="karaoke-evaluation-") as temporary:
            temporary_path = Path(temporary)
            source = temporary_path / f"performance{recording_suffix(request.headers.get('content-type'))}"
            wav = temporary_path / "performance.wav"
            source.write_bytes(recording)
            try:
                subprocess.run(
                    ["ffmpeg", "-y", "-i", str(source), "-ac", "1", "-ar", "44100", "-c:a", "pcm_s16le", str(wav)],
                    check=True,
                    capture_output=True,
                )
                return evaluate_recording(wav, audit_payload, tolerance_half_steps)
            except (subprocess.CalledProcessError, ValueError) as error:
                raise HTTPException(status_code=422, detail="Não foi possível analisar a gravação") from error

    @app.get("/media/{filename}")
    def get_video(filename: str) -> FileResponse:
        return FileResponse(resolve_video(library, filename))

    app.mount("/assets", StaticFiles(directory=WEB_DIR), name="assets")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(WEB_DIR / "index.html")

    return app


def create_app_from_environment() -> FastAPI:
    """Fábrica importável usada pelo Uvicorn quando a recarga está ativa."""
    return create_app(Path(os.environ.get("KARAOKE_LIBRARY", "videos")))


def main() -> None:
    parser = argparse.ArgumentParser(description="Inicia o WebApp de karaokê em tempo real.")
    parser.add_argument(
        "--library",
        type=Path,
        default=Path("videos"),
        help="Pasta com vídeos e arquivos .audit.json (padrão: videos)",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Endereço do servidor (padrão: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Porta HTTP (padrão: 8000)")
    parser.add_argument("--reload", action="store_true", help="Reinicia ao alterar scripts durante desenvolvimento")
    args = parser.parse_args()
    library = args.library.resolve()
    if args.reload:
        script_dir = str(Path(__file__).parent.resolve())
        os.environ["KARAOKE_LIBRARY"] = str(library)
        os.environ["PYTHONPATH"] = script_dir + os.pathsep + os.environ.get("PYTHONPATH", "")
        uvicorn.run(
            "app:create_app_from_environment",
            factory=True,
            host=args.host,
            port=args.port,
            reload=True,
            reload_dirs=[script_dir],
        )
        return
    uvicorn.run(create_app(library), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
