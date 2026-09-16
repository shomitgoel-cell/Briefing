"""Pull recent headlines for each region from free public RSS feeds."""

import re
import socket
from pathlib import Path

import feedparser
import yaml

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "feeds.yaml"
FETCH_TIMEOUT_SECONDS = 10
MAX_ENTRIES_PER_FEED = 8
MAX_HEADLINES_PER_REGION = 12


def _clean_text(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", text).strip()


def _matches_keywords(title: str, summary: str, keywords: list) -> bool:
    if not keywords:
        return True
    haystack = f"{title} {summary}".lower()
    return any(kw.lower() in haystack for kw in keywords)


def _fetch_feed(url: str):
    socket.setdefaulttimeout(FETCH_TIMEOUT_SECONDS)
    try:
        parsed = feedparser.parse(url)
        if parsed.bozo and not parsed.entries:
            return []
        return parsed.entries[:MAX_ENTRIES_PER_FEED]
    except Exception as exc:  # noqa: BLE001 - a single flaky feed must never break the run
        print(f"  [warn] failed to fetch {url}: {exc}")
        return []


def fetch_region_headlines(region_config: dict) -> list:
    keywords = region_config.get("keywords") or []
    headlines = []
    seen_titles = set()

    for feed in region_config.get("feeds", []):
        entries = _fetch_feed(feed["url"])
        for entry in entries:
            title = _clean_text(getattr(entry, "title", ""))
            summary = _clean_text(getattr(entry, "summary", "") or getattr(entry, "description", ""))
            if not title or title.lower() in seen_titles:
                continue
            if not _matches_keywords(title, summary, keywords):
                continue
            seen_titles.add(title.lower())
            headlines.append({
                "source": feed["name"],
                "title": title,
                "summary": summary[:300],
            })

    return headlines[:MAX_HEADLINES_PER_REGION]


def fetch_all_headlines() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    result = {}
    for region in ("us", "global", "philippines"):
        print(f"Fetching headlines for: {region}")
        result[region] = fetch_region_headlines(config[region])
        print(f"  -> {len(result[region])} headlines")
    return result


if __name__ == "__main__":
    import json

    print(json.dumps(fetch_all_headlines(), indent=2))
