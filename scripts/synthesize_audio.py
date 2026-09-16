"""Convert the script's segments into a single narrated MP3 using edge-tts."""

import asyncio
import tempfile
from pathlib import Path

import edge_tts
from pydub import AudioSegment

VOICE = "en-US-AndrewNeural"
SEGMENT_ORDER = ["intro", "us", "global", "philippines", "outro"]
SILENCE_BETWEEN_SEGMENTS_MS = 900
EXPORT_BITRATE = "96k"


async def _synthesize_segment(text: str, out_path: Path) -> None:
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(str(out_path))


def synthesize_episode(script: dict, output_mp3_path: Path) -> float:
    """Renders the script to output_mp3_path and returns duration in seconds."""

    output_mp3_path.parent.mkdir(parents=True, exist_ok=True)
    silence = AudioSegment.silent(duration=SILENCE_BETWEEN_SEGMENTS_MS)
    combined = AudioSegment.empty()

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_dir_path = Path(tmp_dir)
        for i, key in enumerate(SEGMENT_ORDER):
            text = (script.get(key) or "").strip()
            if not text:
                continue
            segment_path = tmp_dir_path / f"{key}.mp3"
            asyncio.run(_synthesize_segment(text, segment_path))
            segment_audio = AudioSegment.from_file(segment_path, format="mp3")
            if len(combined) > 0:
                combined += silence
            combined += segment_audio

    combined.export(output_mp3_path, format="mp3", bitrate=EXPORT_BITRATE)
    return len(combined) / 1000.0


if __name__ == "__main__":
    import json
    import sys

    script_json_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("script.json")
    out_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("episode.mp3")
    with open(script_json_path, "r", encoding="utf-8") as f:
        script = json.load(f)
    duration = synthesize_episode(script, out_path)
    print(f"Wrote {out_path} ({duration:.1f}s)")
