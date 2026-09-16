"""Turn the day's headlines into a ~5 minute spoken briefing script using Claude."""

import json
import os
import re

CLAUDE_MODEL = "claude-sonnet-5"

SYSTEM_PROMPT = """You are the writer/host for a daily 5-minute audio briefing called
"Daily Briefing" that a listener plays on their morning commute. Your job is to turn
raw headlines into a tight, conversational spoken-word script -- not a list of
headlines read aloud, but a host actually explaining what happened and why it matters,
the way a radio anchor would. Connect related stories, cut anything trivial or
redundant, and favor geopolitics and financial-markets stories over celebrity or
soft news.

Style rules:
- Write for the ear: short sentences, no bullet points, no markdown, no headers.
- Do not say things like "moving on to our next story" more than once per segment.
- Do not invent facts. Only use what's in the provided headlines/summaries.
- If a region has thin or no relevant headlines, say so briefly and move on gracefully
  instead of padding with filler.
- No sign-off like "that's all for today" inside segment text except in the outro.

Return ONLY a single JSON object (no markdown fences, no commentary) with these
exact string fields: "title", "description", "intro", "us", "global",
"philippines", "outro".
"""


def _build_user_prompt(headlines: dict, date_str: str) -> str:
    def format_region(name: str, items: list) -> str:
        if not items:
            return f"{name.upper()}: (no fresh headlines today)"
        lines = [f"{name.upper()} headlines:"]
        for h in items:
            lines.append(f"- [{h['source']}] {h['title']}: {h['summary']}")
        return "\n".join(lines)

    sections = "\n\n".join([
        format_region("US", headlines.get("us", [])),
        format_region("Global", headlines.get("global", [])),
        format_region("Philippines", headlines.get("philippines", [])),
    ])

    return f"""Today's date: {date_str}

{sections}

Write today's script as a JSON object with these fields:
- "title": a short, specific episode title for today (max 10 words)
- "description": one sentence summarizing today's episode
- "intro": ~10 seconds, ~25 words. Greet the listener, say the date, preview the
  three segments (US, global, Philippines).
- "us": ~2 minutes, ~290 words. US geopolitics and financial markets news.
- "global": ~2 minutes, ~290 words. Global/international geopolitics and markets
  news outside the US.
- "philippines": ~1 minute, ~140 words. Philippines news, prioritizing politics,
  economy, and markets.
- "outro": ~10 seconds, ~25 words. Brief sign-off.

Return ONLY the JSON object."""


def _extract_json(raw_text: str) -> dict:
    text = raw_text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def generate_script_with_claude(headlines: dict, date_str: str) -> dict:
    from anthropic import Anthropic

    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=3000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": _build_user_prompt(headlines, date_str)}],
    )
    raw_text = "".join(block.text for block in response.content if block.type == "text")
    return _extract_json(raw_text)


def generate_fallback_script(headlines: dict, date_str: str) -> dict:
    """Simple headline read-out used only if the Claude call fails, so a
    listener still gets an episode rather than a missed day."""

    def region_block(items: list, max_items: int) -> str:
        if not items:
            return "Nothing significant stood out here today."
        parts = [f"{h['title']}." for h in items[:max_items]]
        return " ".join(parts)

    return {
        "title": f"Briefing for {date_str}",
        "description": "Automated headline digest.",
        "intro": f"Good morning. Here is your briefing for {date_str}: US markets, "
                 f"global news, and the Philippines, in five minutes.",
        "us": region_block(headlines.get("us", []), 6),
        "global": region_block(headlines.get("global", []), 6),
        "philippines": region_block(headlines.get("philippines", []), 4),
        "outro": "That's your briefing. Have a great day.",
    }


def generate_script(headlines: dict, date_str: str) -> dict:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("  [warn] ANTHROPIC_API_KEY not set, using fallback headline script")
        return generate_fallback_script(headlines, date_str)
    try:
        return generate_script_with_claude(headlines, date_str)
    except Exception as exc:  # noqa: BLE001 - never let a bad API day skip the episode
        print(f"  [warn] Claude script generation failed ({exc}), using fallback")
        return generate_fallback_script(headlines, date_str)


if __name__ == "__main__":
    from datetime import date

    from fetch_news import fetch_all_headlines

    script = generate_script(fetch_all_headlines(), date.today().isoformat())
    print(json.dumps(script, indent=2))
