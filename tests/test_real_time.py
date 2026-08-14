import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "karaoke-real-time"))

from app import sidecar_audit, video_entries


def test_sidecar_audit_and_video_discovery(tmp_path):
    video = tmp_path / "video-pronto-1.mp4"
    video.touch()
    (tmp_path / "ignorar.txt").touch()
    (tmp_path / "video-pronto-1.audit.json").write_text("{}")
    assert sidecar_audit(video) == tmp_path / "video-pronto-1.audit.json"
    assert video_entries(tmp_path) == [{"name": video.name, "url": "/media/video-pronto-1.mp4", "has_audit": True}]
