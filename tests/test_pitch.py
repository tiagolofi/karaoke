import numpy as np

from karaoke.pitch import median_filter_pitch


def test_median_filter_removes_an_isolated_pitch_outlier():
    g4 = 391.995
    f_sharp4 = 369.994
    filtered = median_filter_pitch(
        np.array([g4, g4, f_sharp4, g4, g4]),
        np.array([True, True, True, True, True]),
    )

    assert filtered[2] == g4


def test_median_filter_keeps_unvoiced_frames_unchanged():
    frequencies = np.array([391.995, np.nan, 391.995])
    filtered = median_filter_pitch(frequencies, np.array([True, False, True]))

    assert np.isnan(filtered[1])
