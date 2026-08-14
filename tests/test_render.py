from karaoke.models import SungNote, TimedText
from karaoke.render import write_ass


def test_ass_includes_chromatic_note_name(tmp_path):
    subtitles = write_ass(
        [TimedText("teste", 1.0, 2.0)],
        [SungNote(1.2, 1.5, 61, 277.183)],
        tmp_path / "karaoke.ass",
    )

    assert "Nota: C#4 · MIDI 61 · 277.2 Hz" in subtitles.read_text(encoding="utf-8")
    content = subtitles.read_text(encoding="utf-8")
    assert "Style: Lyric,Arial,52,&H0000FFFF,&H0000FFFF,&H00000000,&H00000000" in content
    assert "Style: Note,Arial,32,&H0000FFFF,&H0000FFFF,&H00000000,&H00000000" in content
