import math

from karaoke.models import SungNote
from karaoke.variants import VARIANT_SEMITONES, transpose_notes, variant_label


def test_transpose_generates_the_seven_requested_offsets():
    assert VARIANT_SEMITONES == (-3, -2, -1, 0, 1, 2, 3)
    assert [variant_label(offset) for offset in VARIANT_SEMITONES] == [
        "transpose-3", "transpose-2", "transpose-1", "original", "transpose+1", "transpose+2", "transpose+3",
    ]


def test_transpose_moves_midi_and_frequency_but_keeps_timing_and_lyric():
    original = SungNote(1.0, 1.5, 60, 261.625565, "teste")
    shifted = transpose_notes([original], -3)[0]

    assert (shifted.start, shifted.end, shifted.midi, shifted.lyric) == (1.0, 1.5, 57, "teste")
    assert math.isclose(shifted.hz, original.hz * 2 ** (-3 / 12))
