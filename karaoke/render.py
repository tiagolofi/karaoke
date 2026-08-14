from __future__ import annotations

import subprocess
from pathlib import Path

from .audit import midi_to_note_name
from .models import SungNote, TimedText


def _stamp(seconds: float) -> str:
    centiseconds = round(seconds * 100)
    hours, remainder = divmod(centiseconds, 360000)
    minutes, remainder = divmod(remainder, 6000)
    return f"{hours}:{minutes:02d}:{remainder // 100:02d}.{remainder % 100:02d}"


def write_ass(lyrics: list[TimedText], notes: list[SungNote], destination: Path) -> Path:
    """Cria legendas ASS: letra central e nota MIDI na faixa inferior."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    header = """[Script Info]\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\n\n[V4+ Styles]\nFormat: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding\nStyle: Lyric,Arial,52,&H0000FFFF,&H0000FFFF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,5,1,2,80,80,145,1\nStyle: Note,Arial,32,&H0000FFFF,&H0000FFFF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,5,1,2,80,80,70,1\n\n[Events]\nFormat: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n"""
    events = [f"Dialogue: 0,{_stamp(x.start)},{_stamp(x.end)},Lyric,,0,0,0,,{x.text.replace(',', '\\,')}" for x in lyrics]
    events += [
        f"Dialogue: 1,{_stamp(x.start)},{_stamp(x.end)},Note,,0,0,0,,"
        f"Nota: {midi_to_note_name(x.midi)} · MIDI {x.midi} · {x.hz:.1f} Hz"
        for x in notes
    ]
    destination.write_text(header + "\n".join(events) + "\n", encoding="utf-8")
    return destination


def render_video(video: Path, instrumental: Path, subtitles: Path, destination: Path) -> Path:
    """Queima legendas e substitui o áudio original pelo instrumental."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    escaped = str(subtitles).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(video), "-i", str(instrumental),
            "-map", "0:v:0", "-map", "1:a:0", "-vf", f"ass='{escaped}'",
            "-map_metadata", "0", "-c:v", "libx264", "-c:a", "aac", "-shortest", str(destination),
        ],
        check=True,
    )
    return destination
