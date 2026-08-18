from __future__ import annotations

import argparse
import os
from pathlib import Path
from urllib.parse import quote

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov", ".webm", ".avi"}
WEB_DIR = Path(__file__).parent / "web"


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
