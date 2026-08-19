from pathlib import Path

from karaoke.cli import main as karaoke_main


def test_pipeline_default_output_is_in_videos(monkeypatch, tmp_path):
    captured: dict[str, Path] = {}
    source = tmp_path / "entrada.mp4"
    source.touch()

    monkeypatch.setattr("sys.argv", ["karaoke", str(source)])
    monkeypatch.setattr("karaoke.cli.extract_audio", lambda *_: tmp_path / "audio.wav")
    monkeypatch.setattr("karaoke.cli.transcribe", lambda *_: [])
    monkeypatch.setattr("karaoke.cli.separate_stems", lambda *_: (tmp_path / "vocals.wav", tmp_path / "instrumental.wav"))
    monkeypatch.setattr("karaoke.cli.detect_notes", lambda *_: [])
    monkeypatch.setattr("karaoke.cli.synchronize", lambda *_: [])
    monkeypatch.setattr("karaoke.cli.write_lyrics_json", lambda *_: tmp_path / "karaoke.lyrics.json")
    monkeypatch.setattr("karaoke.cli.render_video", lambda *args: captured.setdefault("output", args[-1]))
    monkeypatch.setattr("karaoke.cli.write_audit_json", lambda destination, *_: captured.setdefault("audit", destination))
    monkeypatch.setattr("karaoke.cli.cleanup_work_dir", lambda *_: None)

    karaoke_main()

    assert captured["output"] == Path("videos/karaoke.mp4")
    assert captured["audit"] == Path("videos/karaoke.audit.json")
