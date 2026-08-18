from karaoke.models import TimedText
from karaoke.render import write_ass


def test_ass_includes_only_lyrics(tmp_path):
    subtitles = write_ass([TimedText("teste", 1.0, 2.0)], tmp_path / "karaoke.ass")

    content = subtitles.read_text(encoding="utf-8")
    assert "Dialogue: 0,0:00:01.00,0:00:02.00,Lyric" in content
    assert "Nota:" not in content
    assert "Style: Lyric,Arial,52,&H0000FFFF,&H0000FFFF,&H00000000,&H00000000" in content
    assert "Style: Note" not in content
