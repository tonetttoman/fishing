#!/usr/bin/env python3
"""Match the 45 YouTube playlist entries to public Parti-Arcok podcast RSS audio files."""

from __future__ import annotations

import argparse
import difflib
import html
import json
import re
import unicodedata
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

LOOKUP_URL = "https://itunes.apple.com/lookup?id=1560177340&entity=podcast"
UA = "Mozilla/5.0 (compatible; FishingResearchBot/1.0; +https://github.com/tonetttoman/fishing)"


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=60) as response:
        return response.read()


def strip_accents(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in value if not unicodedata.combining(ch))


def normalize_title(value: str) -> str:
    value = html.unescape(value or "").casefold()
    value = strip_accents(value)
    replacements = (
        "parti-arcok podcast", "parti arcok podcast", "parti-arcok live extra",
        "parti arcok live extra", "parti-arcok live", "parti arcok live",
        "vendegem", "vendeg", "podcast", "live+", "live",
    )
    for item in replacements:
        value = value.replace(item, " ")
    value = value.replace("×", " x ").replace("–", "-").replace("—", "-")
    value = re.sub(r"\b(resz|episode|epizod)\b", " ", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def leading_episode_number(value: str) -> int | None:
    match = re.match(r"^\s*(\d{1,3})\s*[.):-]", value or "")
    return int(match.group(1)) if match else None


def walter_part(value: str) -> int | None:
    low = strip_accents((value or "").casefold())
    if "walter" not in low:
        return None
    match = re.search(r"(?:walter[^\d]{0,80})?(\d{1,2})\s*\.?(?:\s*resz)", low)
    if match:
        return int(match.group(1))
    match = re.search(r"-\s*(\d{1,2})\s*-", low)
    return int(match.group(1)) if match else None


def tokens(value: str) -> set[str]:
    return {part for part in normalize_title(value).split() if len(part) > 1}


def similarity(a: str, b: str) -> float:
    na, nb = normalize_title(a), normalize_title(b)
    seq = difflib.SequenceMatcher(None, na, nb).ratio()
    ta, tb = tokens(a), tokens(b)
    overlap = len(ta & tb) / max(1, len(ta | tb))
    containment = len(ta & tb) / max(1, min(len(ta), len(tb)))
    return 100.0 * (0.45 * seq + 0.30 * overlap + 0.25 * containment)


def find_text_ending(item: ET.Element, suffix: str) -> str:
    for child in item.iter():
        if child.tag.casefold().endswith(suffix.casefold()) and child.text:
            return child.text.strip()
    return ""


def parse_feed(feed_bytes: bytes) -> list[dict[str, Any]]:
    root = ET.fromstring(feed_bytes)
    episodes: list[dict[str, Any]] = []
    for item in root.findall(".//item"):
        title = find_text_ending(item, "title")
        enclosure = None
        for child in item:
            if child.tag.casefold().endswith("enclosure") and child.attrib.get("url"):
                enclosure = child
                break
        audio_url = enclosure.attrib.get("url", "") if enclosure is not None else ""
        if not title or not audio_url:
            continue
        episodes.append({
            "title": title,
            "audio_url": audio_url,
            "audio_type": enclosure.attrib.get("type", "") if enclosure is not None else "",
            "audio_length": enclosure.attrib.get("length", "") if enclosure is not None else "",
            "guid": find_text_ending(item, "guid"),
            "published": find_text_ending(item, "pubDate"),
            "duration": find_text_ending(item, "duration"),
            "episode_number": leading_episode_number(title),
            "walter_part": walter_part(title),
        })
    return episodes


def match_episode(title: str, episodes: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, float, str]:
    number = leading_episode_number(title)
    wpart = walter_part(title)

    candidates = episodes
    reason = "fuzzy_title"
    if number is not None:
        numbered = [ep for ep in episodes if ep.get("episode_number") == number]
        if numbered:
            candidates = numbered
            reason = "episode_number"
    elif wpart is not None:
        walter = [ep for ep in episodes if ep.get("walter_part") == wpart and "walter" in normalize_title(ep["title"])]
        if walter:
            candidates = walter
            reason = "walter_part"

    if not candidates:
        return None, 0.0, "no_candidate"
    ranked = sorted(((similarity(title, ep["title"]), ep) for ep in candidates), key=lambda x: x[0], reverse=True)
    score, best = ranked[0]

    threshold = 45.0 if reason in {"episode_number", "walter_part"} else 62.0
    if score < threshold:
        return None, score, reason + "_below_threshold"
    return best, score, reason


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("playlist_json")
    parser.add_argument("--output", default="research/podcast_audio_map.json")
    args = parser.parse_args()

    lookup = json.loads(fetch(LOOKUP_URL).decode("utf-8"))
    results = lookup.get("results") or []
    if not results or not results[0].get("feedUrl"):
        raise SystemExit("Apple lookup did not return a podcast feedUrl")
    feed_url = results[0]["feedUrl"]
    episodes = parse_feed(fetch(feed_url))

    playlist = json.loads(Path(args.playlist_json).read_text(encoding="utf-8"))
    entries = playlist.get("entries") or []
    mapping: list[dict[str, Any]] = []
    matched = 0

    for index, entry in enumerate(entries, start=1):
        video_id = str(entry.get("id") or "")
        title = str(entry.get("title") or video_id)
        episode, score, reason = match_episode(title, episodes)
        row: dict[str, Any] = {
            "index": index,
            "video_id": video_id,
            "youtube_title": title,
            "youtube_url": f"https://www.youtube.com/watch?v={video_id}",
            "match_score": round(score, 2),
            "match_reason": reason,
            "status": "matched" if episode else "unmatched",
        }
        if episode:
            matched += 1
            row.update({
                "podcast_title": episode["title"],
                "audio_url": episode["audio_url"],
                "audio_type": episode["audio_type"],
                "audio_length": episode["audio_length"],
                "guid": episode["guid"],
                "published": episode["published"],
                "duration": episode["duration"],
            })
        mapping.append(row)

    payload = {
        "podcast_name": results[0].get("collectionName", "Parti-Arcok Podcast"),
        "feed_url": feed_url,
        "rss_episode_count": len(episodes),
        "playlist_video_count": len(entries),
        "matched_count": matched,
        "unmatched_count": len(entries) - matched,
        "items": mapping,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = output.with_suffix(".summary.txt")
    summary.write_text(
        "\n".join([
            f"Podcast feed: {feed_url}",
            f"RSS episodes: {len(episodes)}",
            f"Playlist videos: {len(entries)}",
            f"Matched audio episodes: {matched}",
            f"Unmatched videos: {len(entries) - matched}",
        ]) + "\n",
        encoding="utf-8",
    )
    print(summary.read_text(encoding="utf-8"))
    return 0 if matched else 2


if __name__ == "__main__":
    raise SystemExit(main())
