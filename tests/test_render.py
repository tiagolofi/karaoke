import json

from karaoke.models import TimedText
from karaoke.render import write_lyrics_json


def test_lyrics_json_is_editable_and_contains_only_lyrics(tmp_path):
    subtitles = write_lyrics_json([TimedText("teste", 1.0, 2.0)], tmp_path / "karaoke.lyrics.json")

    payload = json.loads(subtitles.read_text(encoding="utf-8"))
    assert payload == {"schema_version": 1, "lyrics": [{"start": 1.0, "end": 2.0, "text": "teste"}]}
