from __future__ import annotations

import subprocess
from pathlib import Path

from .models import SungNote, TimedText


def _stamp(seconds: float) -> str:
    centiseconds = round(seconds * 100)
    hours, remainder = divmod(centiseconds, 360000)
    minutes, remainder = divmod(remainder, 6000)
    return f"{hours}:{minutes:02d}:{remainder // 100:02d}.{remainder % 100:02d}"


def write_ass(lyrics: list[TimedText], notes: list[SungNote], destination: Path) -> Path:
    """Cria legendas ASS: letra central e nota MIDI na faixa inferior."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    header = """[Script Info]\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\n\n[V4+ Styles]\nFormat: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding\nStyle: Lyric,Arial,52,&H00FFFFFF,&H0000FFFF,&H80000000,&H80000000,1,0,0,0,100,100,0,0,1,3,1,2,80,80,145,1\nStyle: Note,Arial,32,&H0000FFFF,&H0000FFFF,&H80000000,&H80000000,1,0,0,0,100,100,0,0,1,2,1,2,80,80,70,1\n\n[Events]\nFormat: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n"""
    events = [f"Dialogue: 0,{_stamp(x.start)},{_stamp(x.end)},Lyric,,0,0,0,,{x.text.replace(',', '\\,')}" for x in lyrics]
    events += [f"Dialogue: 1,{_stamp(x.start)},{_stamp(x.end)},Note,,0,0,0,,Nota: {x.midi} ({x.hz:.1f} Hz)" for x in notes]
    destination.write_text(header + "\n".join(events) + "\n", encoding="utf-8")
    return destination


def render_video(video: Path, subtitles: Path, destination: Path) -> Path:
    """Queima as legendas sincronizadas no vídeo original via FFmpeg/libass."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    escaped = str(subtitles).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
    subprocess.run(["ffmpeg", "-y", "-i", str(video), "-vf", f"ass='{escaped}'", "-c:a", "copy", str(destination)], check=True)
    return destination
