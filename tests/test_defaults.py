from pathlib import Path

from karaoke.cli import main as karaoke_main


def test_pipeline_generates_seven_variants_in_videos(monkeypatch, tmp_path):
    captured: dict[str, list[Path]] = {"audio": [], "video": [], "audit": [], "lyrics": []}
    source = tmp_path / "entrada.mp4"
    source.touch()

    monkeypatch.setattr("sys.argv", ["karaoke", str(source)])
    monkeypatch.setattr("karaoke.cli.extract_audio", lambda *_: tmp_path / "audio.wav")
    monkeypatch.setattr("karaoke.cli.transcribe", lambda *_: [])
    monkeypatch.setattr("karaoke.cli.separate_stems", lambda *_: (tmp_path / "vocals.wav", tmp_path / "instrumental.wav"))
    monkeypatch.setattr("karaoke.cli.detect_notes", lambda *_: [])
    monkeypatch.setattr("karaoke.cli.synchronize", lambda *_: [])
    monkeypatch.setattr("karaoke.cli.render_instrumental_audio", lambda _source, destination, _semitones: captured["audio"].append(destination) or destination)
    monkeypatch.setattr("karaoke.cli.render_video", lambda _video, _audio, destination: captured["video"].append(destination) or destination)
    monkeypatch.setattr("karaoke.cli.write_lyrics_json", lambda _lyrics, destination: captured["lyrics"].append(destination) or destination)
    monkeypatch.setattr("karaoke.cli.write_audit_json", lambda destination, *_: captured["audit"].append(destination) or destination)
    monkeypatch.setattr("karaoke.cli.cleanup_work_dir", lambda *_: None)

    karaoke_main()

    expected = [
        Path("videos/variantes/karaoke") / name
        for name in ("transpose-3", "transpose-2", "transpose-1", "original", "transpose+1", "transpose+2", "transpose+3")
    ]
    assert [path.parent for path in captured["audio"]] == expected
    assert [path.name for path in captured["audio"]] == ["instrumental.m4a"] * 7
    assert [path.parent for path in captured["video"]] == expected
    assert [path.name for path in captured["audit"]] == ["karaoke.audit.json"] * 7
    assert captured["lyrics"] == [Path("videos/variantes/karaoke/lyrics.json")]
