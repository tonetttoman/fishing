#!/usr/bin/env python3
"""Fetch public captions for playlist items blocked on GitHub datacenter IPs.

Uses the documented no-key text endpoint at youtube-transcript.ai. It only requests
public caption tracks and does not bypass private, members-only, or disabled captions.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

API_TEMPLATE = "https://youtube-transcript.ai/transcript/{video_id}.txt"
UA = "Mozilla/5.0 (compatible; FishingResearchBot/1.0; +https://github.com/tonetttoman/fishing)"
# Accept [1:23], **[1:23]**, - [1:23], and timestamp links such as [1:23](...).
TIMESTAMP_TOKEN_RE = re.compile(r"\[(?P<stamp>\d{1,2}:\d{2}(?::\d{2})?)\]")
MARKDOWN_LINK_RE = re.compile(r"\]\([^)]*\)")
MARKDOWN_DECORATION_RE = re.compile(r"^[\s>*#_`~-]+|[\s*_`~]+$")


def seconds_from_stamp(value: str) -> int:
    parts = [int(part) for part in value.split(":")]
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    return 0


def stamp(seconds: float | int | None) -> str:
    value = max(0, int(float(seconds or 0)))
    hour, rem = divmod(value, 3600)
    minute, second = divmod(rem, 60)
    return f"{hour:02d}:{minute:02d}:{second:02d}"


def request_text(video_id: str, retries: int = 5) -> tuple[str | None, str, str]:
    base = API_TEMPLATE.format(video_id=urllib.parse.quote(video_id, safe=""))
    attempts = [base + "?lang=hu", base]
    errors: list[str] = []
    for url in attempts:
        for attempt in range(1, retries + 1):
            request = urllib.request.Request(
                url,
                headers={
                    "User-Agent": UA,
                    "Accept": "text/markdown,text/plain;q=0.9,*/*;q=0.5",
                },
            )
            try:
                with urllib.request.urlopen(request, timeout=180) as response:
                    body = response.read().decode("utf-8", errors="replace")
                    content_type = response.headers.get("content-type", "")
                    status = response.status
                if status == 200 and body.strip():
                    return body, url, content_type
                errors.append(f"{url}: empty response ({len(body)} bytes, {content_type})")
                break
            except urllib.error.HTTPError as exc:
                body = exc.read().decode("utf-8", errors="replace")[:1500]
                errors.append(f"{url}: HTTP {exc.code}: {body}")
                if exc.code in {400, 404}:
                    break
                if exc.code == 429:
                    time.sleep(min(90, 15 * attempt))
                else:
                    time.sleep(min(30, 3 * attempt))
            except Exception as exc:
                errors.append(f"{url}: {type(exc).__name__}: {exc}")
                time.sleep(min(30, 3 * attempt))
    return None, "", " | ".join(errors[-8:])


def clean_markdown_text(value: str) -> str:
    value = html.unescape(value)
    value = MARKDOWN_LINK_RE.sub("]", value)
    value = MARKDOWN_DECORATION_RE.sub("", value)
    value = value.replace("**", "").replace("__", "").replace("`", "")
    return " ".join(value.split()).strip(" -–—|:")


def parse_markdown(body: str) -> list[dict[str, Any]]:
    """Parse timestamps whether each cue is on one line or spans paragraphs."""
    matches = list(TIMESTAMP_TOKEN_RE.finditer(body))
    rows: list[dict[str, Any]] = []
    for index, match in enumerate(matches):
        start_of_text = match.end()
        end_of_text = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        text = clean_markdown_text(body[start_of_text:end_of_text])
        # Ignore metadata/header timestamps and accidental URL fragments.
        if not text or text.lower().startswith(("source video", "language", "duration", "words")):
            continue
        if len(text) > 5000:
            # A false timestamp match in a header should not swallow the transcript.
            continue
        rows.append({
            "start": seconds_from_stamp(match.group("stamp")),
            "text": text,
        })

    # Keep chronological transcript cues and remove exact duplicates.
    cleaned: list[dict[str, Any]] = []
    last_start = -1
    last_text = ""
    for row in rows:
        if row["start"] < last_start:
            continue
        if row["text"] == last_text:
            continue
        cleaned.append(row)
        last_start = row["start"]
        last_text = row["text"]
    return cleaned


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("audio_map_json")
    parser.add_argument("--output", default="research/external_youtube_transcripts")
    args = parser.parse_args()

    mapping = json.loads(Path(args.audio_map_json).read_text(encoding="utf-8"))
    unmatched = [item for item in mapping.get("items") or [] if item.get("status") != "matched"]
    output = Path(args.output)
    clean = output / "clean_txt"
    raw = output / "raw_markdown"
    clean.mkdir(parents=True, exist_ok=True)
    raw.mkdir(parents=True, exist_ok=True)

    manifest: list[dict[str, Any]] = []
    combined: list[str] = []
    extracted = 0
    failed = 0
    total_entries = 0

    for n, item in enumerate(unmatched, start=1):
        video_id = str(item.get("video_id") or "")
        title = str(item.get("youtube_title") or video_id)
        print(f"[{n}/{len(unmatched)}] {title} ({video_id})", flush=True)
        body, provider_url, error = request_text(video_id)
        if body is None:
            failed += 1
            manifest.append({
                "index": item.get("index"),
                "video_id": video_id,
                "title": title,
                "status": "failed",
                "error": error,
            })
            continue

        raw_path = raw / f"{video_id}.txt"
        raw_path.write_text(body, encoding="utf-8")
        rows = parse_markdown(body)
        if not rows:
            failed += 1
            manifest.append({
                "index": item.get("index"),
                "video_id": video_id,
                "title": title,
                "status": "failed",
                "response_bytes": len(body.encode("utf-8")),
                "response_prefix": body[:1200],
                "error": "provider response contained no parseable timestamped transcript rows",
            })
            continue

        extracted += 1
        total_entries += len(rows)
        lines = [
            f"VIDEÓ: {title}",
            f"URL: {item.get('youtube_url', '')}",
            f"VIDEÓ_ID: {video_id}",
            "FORRÁS: youtube-transcript.ai kulcs nélküli transcript végpont",
            "",
        ]
        lines.extend(f"[{stamp(row['start'])}] {row['text']}" for row in rows)
        txt_path = clean / f"{int(item.get('index') or 0):03d}_{video_id}.txt"
        txt_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        combined.extend(["=" * 100, *lines, ""])
        manifest.append({
            "index": item.get("index"),
            "video_id": video_id,
            "title": title,
            "status": "caption_extracted",
            "entries": len(rows),
            "provider_url": provider_url,
            "response_bytes": len(body.encode("utf-8")),
            "raw_file": str(raw_path.relative_to(output)),
            "transcript_file": str(txt_path.relative_to(output)),
        })
        time.sleep(3)

    output.mkdir(parents=True, exist_ok=True)
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output / "all_transcripts_timestamped.txt").write_text(
        "\n".join(combined) + "\n", encoding="utf-8"
    )
    summary = [
        f"YouTube-only videos attempted: {len(unmatched)}",
        f"Captions extracted: {extracted}",
        f"Captions failed/unavailable: {failed}",
        f"Timestamped entries: {total_entries}",
    ]
    (output / "summary.txt").write_text("\n".join(summary) + "\n", encoding="utf-8")
    print("\n".join(summary))
    return 0 if extracted else 2


if __name__ == "__main__":
    raise SystemExit(main())
