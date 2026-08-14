import json

from karaoke.audit import midi_to_note_name, write_audit_json
from karaoke.models import SungNote, TimedText


def test_audit_json_contains_ordered_timeline(tmp_path):
    destination = tmp_path / "audit.json"
    write_audit_json(
        destination,
        tmp_path / "video.mp4",
        tmp_path / "video-pronto.mp4",
        [TimedText("primeira frase", 1.25, 2.5)],
        [SungNote(1.5, 1.8, 60, 261.625, "primeira frase")],
    )

    data = json.loads(destination.read_text(encoding="utf-8"))
    assert data["schema_version"] == 1
    assert data["rendered_video"]["filename"] == "video-pronto.mp4"
    assert data["lyrics"][0]["text"] == "primeira frase"
    assert data["notes"][0]["midi"] == 60
    assert data["notes"][0]["note_name"] == "C4"
    assert [event["type"] for event in data["timeline"]] == ["lyric", "note"]


def test_midi_to_note_name_covers_naturals_and_sharps():
    assert midi_to_note_name(60) == "C4"
    assert midi_to_note_name(61) == "C#4"
    assert midi_to_note_name(71) == "B4"
