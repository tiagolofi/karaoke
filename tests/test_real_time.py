import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "karaoke-real-time"))

import app as realtime_app
from app import sidecar_audit, sidecar_lyrics, video_entries


def test_sidecar_audit_and_video_discovery(tmp_path):
    video = tmp_path / "video-pronto-1.mp4"
    video.touch()
    (tmp_path / "ignorar.txt").touch()
    (tmp_path / "video-pronto-1.audit.json").write_text("{}")
    assert sidecar_audit(video) == tmp_path / "video-pronto-1.audit.json"
    assert sidecar_lyrics(video) == tmp_path / "video-pronto-1.lyrics.json"
    assert video_entries(tmp_path) == [{"name": video.name, "url": "/media/video-pronto-1.mp4", "has_audit": True}]


def test_reload_uses_importable_application_factory(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(sys, "argv", ["app.py", "--reload", "--library", str(tmp_path)])
    monkeypatch.setattr(realtime_app.uvicorn, "run", lambda *args, **kwargs: calls.append((args, kwargs)))

    realtime_app.main()

    args, kwargs = calls[0]
    assert args == ("app:create_app_from_environment",)
    assert kwargs["factory"] is True
    assert kwargs["reload"] is True
    assert os.environ["KARAOKE_LIBRARY"] == str(tmp_path.resolve())
