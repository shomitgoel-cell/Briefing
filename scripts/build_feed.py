"""Maintain docs/feed.xml (podcast RSS) and docs/index.html across episodes."""

import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

DOCS_DIR = Path(__file__).resolve().parent.parent / "docs"
FEED_PATH = DOCS_DIR / "feed.xml"
EPISODES_DIR = DOCS_DIR / "episodes"
COVER_PATH = DOCS_DIR / "cover.jpg"

MAX_EPISODES_KEPT = 14
PODCAST_TITLE = "Daily Briefing: Geopolitics & Markets"
PODCAST_AUTHOR = "Daily Briefing"
PODCAST_DESCRIPTION = (
    "A 5-minute daily audio briefing covering US geopolitics and markets, "
    "global geopolitics and markets, and the Philippines -- generated fresh "
    "every morning."
)

ITUNES_NS = "http://www.itunes.com/dtds/podcast-1.0.dtd"
ATOM_NS = "http://www.w3.org/2005/Atom"
ET.register_namespace("itunes", ITUNES_NS)
ET.register_namespace("atom", ATOM_NS)


def _itunes_tag(name: str) -> str:
    return f"{{{ITUNES_NS}}}{name}"


def _load_existing_items(feed_path: Path) -> list:
    """Returns a list of existing <item> ElementTree elements, newest first."""
    if not feed_path.exists():
        return []
    tree = ET.parse(feed_path)
    channel = tree.getroot().find("channel")
    if channel is None:
        return []
    return channel.findall("item")


def _prune_old_episodes(items: list, keep: int) -> tuple:
    """Returns (kept_items, removed_guids)."""
    kept = items[:keep]
    removed = items[keep:]
    removed_guids = [it.findtext("guid") for it in removed]
    return kept, removed_guids


def _remove_pruned_audio_files(removed_guids: list) -> None:
    for guid in removed_guids:
        if not guid:
            continue
        filename = guid.rsplit("/", 1)[-1]
        mp3_path = EPISODES_DIR / filename
        if mp3_path.exists():
            mp3_path.unlink()
        json_path = mp3_path.with_suffix(".json")
        if json_path.exists():
            json_path.unlink()


def build_new_item_xml(*, episode_date: str, title: str, description: str,
                        audio_url: str, audio_bytes: int, duration_seconds: float,
                        guid: str) -> ET.Element:
    item = ET.Element("item")
    ET.SubElement(item, "title").text = title
    ET.SubElement(item, "description").text = description
    ET.SubElement(item, "guid", {"isPermaLink": "false"}).text = guid
    pub_date = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
    ET.SubElement(item, "pubDate").text = pub_date
    ET.SubElement(item, "enclosure", {
        "url": audio_url,
        "length": str(audio_bytes),
        "type": "audio/mpeg",
    })
    total_seconds = int(duration_seconds)
    hh, remainder = divmod(total_seconds, 3600)
    mm, ss = divmod(remainder, 60)
    duration_str = f"{hh:02d}:{mm:02d}:{ss:02d}" if hh else f"{mm:02d}:{ss:02d}"
    ET.SubElement(item, _itunes_tag("duration")).text = duration_str
    ET.SubElement(item, _itunes_tag("explicit")).text = "false"
    return item


def update_feed(*, base_url: str, episode_date: str, title: str, description: str,
                 audio_filename: str, audio_bytes: int, duration_seconds: float) -> None:
    base_url = base_url.rstrip("/")
    audio_url = f"{base_url}/episodes/{audio_filename}"
    feed_url = f"{base_url}/feed.xml"
    cover_url = f"{base_url}/cover.jpg"
    guid = audio_url

    existing_items = _load_existing_items(FEED_PATH)
    existing_items = [it for it in existing_items if it.findtext("guid") != guid]

    new_item = build_new_item_xml(
        episode_date=episode_date,
        title=title,
        description=description,
        audio_url=audio_url,
        audio_bytes=audio_bytes,
        duration_seconds=duration_seconds,
        guid=guid,
    )
    all_items = [new_item] + existing_items
    kept_items, removed_guids = _prune_old_episodes(all_items, MAX_EPISODES_KEPT)
    _remove_pruned_audio_files(removed_guids)

    rss = ET.Element("rss", {"version": "2.0"})
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = PODCAST_TITLE
    ET.SubElement(channel, "link").text = base_url + "/"
    ET.SubElement(channel, f"{{{ATOM_NS}}}link", {
        "href": feed_url, "rel": "self", "type": "application/rss+xml",
    })
    ET.SubElement(channel, "language").text = "en-us"
    ET.SubElement(channel, "description").text = PODCAST_DESCRIPTION
    ET.SubElement(channel, _itunes_tag("author")).text = PODCAST_AUTHOR
    ET.SubElement(channel, _itunes_tag("explicit")).text = "false"
    image = ET.SubElement(channel, _itunes_tag("image"))
    image.set("href", cover_url)
    category = ET.SubElement(channel, _itunes_tag("category"))
    category.set("text", "News")
    std_image = ET.SubElement(channel, "image")
    ET.SubElement(std_image, "url").text = cover_url
    ET.SubElement(std_image, "title").text = PODCAST_TITLE
    ET.SubElement(std_image, "link").text = base_url + "/"

    for item in kept_items:
        channel.append(item)

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    tree = ET.ElementTree(rss)
    ET.indent(tree, space="  ")
    tree.write(FEED_PATH, encoding="utf-8", xml_declaration=True)

    _write_index_html(kept_items, feed_url=feed_url)


def _write_index_html(items: list, feed_url: str) -> None:
    episode_rows = []
    for item in items:
        title = escape(item.findtext("title") or "")
        description = escape(item.findtext("description") or "")
        pub_date = escape(item.findtext("pubDate") or "")
        enclosure = item.find("enclosure")
        audio_url = enclosure.get("url") if enclosure is not None else ""
        episode_rows.append(f"""
        <article class="episode">
          <h2>{title}</h2>
          <p class="meta">{pub_date}</p>
          <p>{description}</p>
          <audio controls preload="none" src="{escape(audio_url)}"></audio>
        </article>""")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(PODCAST_TITLE)}</title>
<style>
  body {{ font-family: -apple-system, system-ui, sans-serif; max-width: 640px;
         margin: 2rem auto; padding: 0 1rem; color: #1a1a1a; }}
  h1 {{ font-size: 1.5rem; }}
  .subscribe {{ background: #f2f2f2; padding: 1rem; border-radius: 8px; margin: 1rem 0; }}
  .subscribe code {{ word-break: break-all; }}
  .episode {{ border-top: 1px solid #ddd; padding: 1rem 0; }}
  .meta {{ color: #666; font-size: 0.85rem; }}
  audio {{ width: 100%; margin-top: 0.5rem; }}
</style>
</head>
<body>
<h1>{escape(PODCAST_TITLE)}</h1>
<p>{escape(PODCAST_DESCRIPTION)}</p>
<div class="subscribe">
  <strong>Subscribe on iPhone:</strong> Podcasts app &rarr; Library &rarr; &bull;&bull;&bull;
  &rarr; Follow a Show by URL &rarr; paste:<br>
  <code>{escape(feed_url)}</code>
</div>
{''.join(episode_rows)}
</body>
</html>
"""
    (DOCS_DIR / "index.html").write_text(html, encoding="utf-8")


if __name__ == "__main__":
    update_feed(
        base_url="https://example.github.io/briefing",
        episode_date="2026-09-16",
        title="Test Episode",
        description="Test description",
        audio_filename="2026-09-16.mp3",
        audio_bytes=1234,
        duration_seconds=300,
    )
    print("Wrote", FEED_PATH)
