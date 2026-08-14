import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "karaoke-real-time"))

from reference import ReferenceNote, audit_path_for, find_videos, note_at
from scoring import PitchScore, cents_difference


def test_cents_difference_for_equal_frequency():
    assert cents_difference(440.0, 440.0) == 0.0


def test_score_counts_pitch_within_tolerance():
    expected = ReferenceNote(0, 1, 69, 440.0, "A4", "")
    score = PitchScore()
    score.evaluate(440.0, expected, 50)
    score.evaluate(466.16, expected, 50)
    assert score.correct == 1
    assert score.evaluated == 2
    assert score.rate == 50.0


def test_note_at_uses_reference_time_window():
    note = ReferenceNote(5, 6, 60, 261.63, "C4", "oi")
    assert note_at([note], 5.5) == note
    assert note_at([note], 6.0) is None


def test_sidecar_audit_and_video_discovery(tmp_path):
    video = tmp_path / "video-pronto-1.mp4"
    video.touch()
    (tmp_path / "ignorar.txt").touch()
    assert audit_path_for(video) == tmp_path / "video-pronto-1.audit.json"
    assert find_videos(tmp_path) == [video]
