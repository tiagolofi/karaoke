from karaoke.models import SungNote, TimedText
from karaoke.sync import notes_with_lyrics, synchronize


def test_note_receives_overlapping_lyric():
    lyrics = [TimedText("Olá mundo", 1.0, 3.0)]
    note = SungNote(1.5, 2.0, 60, 261.63)
    assert synchronize(lyrics, [note])[0].lyric == "Olá mundo"


def test_note_outside_lyric_has_empty_text():
    note = SungNote(4.0, 5.0, 60, 261.63)
    assert synchronize([TimedText("oi", 1, 2)], [note])[0].lyric == ""


def test_notes_with_lyrics_removes_notes_outside_transcribed_segments():
    notes = [
        SungNote(1.0, 1.5, 60, 261.63, "cantado"),
        SungNote(3.0, 3.5, 43, 98.0, ""),
    ]

    assert notes_with_lyrics(notes) == [notes[0]]
