"""Orchestrates one end-to-end run: fetch news -> write script -> synthesize
audio -> update the podcast feed. Designed to be run once per day by the
GitHub Actions workflow (or manually for testing)."""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_feed import EPISODES_DIR, update_feed  # noqa: E402
from fetch_news import fetch_all_headlines  # noqa: E402
from generate_script import generate_script  # noqa: E402
from make_cover import make_cover_if_missing  # noqa: E402
from synthesize_audio import synthesize_episode  # noqa: E402

EPISODE_TIMEZONE = ZoneInfo("Asia/Manila")


def _resolve_base_url() -> str:
    override = os.environ.get("PODCAST_BASE_URL")
    if override:
        return override.rstrip("/")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if "/" in repo:
        owner, name = repo.split("/", 1)
        return f"https://{owner}.github.io/{name}"
    return "https://example.github.io/briefing"


def main() -> None:
    make_cover_if_missing()

    episode_date = datetime.now(EPISODE_TIMEZONE).date().isoformat()
    print(f"Building episode for {episode_date} (Asia/Manila)")

    headlines = fetch_all_headlines()
    script = generate_script(headlines, episode_date)

    audio_filename = f"{episode_date}.mp3"
    audio_path = EPISODES_DIR / audio_filename
    duration_seconds = synthesize_episode(script, audio_path)
    audio_bytes = audio_path.stat().st_size
    print(f"Synthesized {audio_path} ({duration_seconds:.1f}s, {audio_bytes} bytes)")

    update_feed(
        base_url=_resolve_base_url(),
        episode_date=episode_date,
        title=script.get("title") or f"Briefing for {episode_date}",
        description=script.get("description") or "Daily geopolitics and markets briefing.",
        audio_filename=audio_filename,
        audio_bytes=audio_bytes,
        duration_seconds=duration_seconds,
    )

    script_path = Path(__file__).resolve().parent.parent / "docs" / "episodes" / f"{episode_date}.json"
    script_path.write_text(json.dumps(script, indent=2), encoding="utf-8")

    print("Done.")


if __name__ == "__main__":
    main()
