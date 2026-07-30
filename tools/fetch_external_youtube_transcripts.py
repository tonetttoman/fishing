#!/usr/bin/env python3
"""Fetch public captions for playlist items blocked on GitHub datacenter IPs.

Uses the documented no-key text endpoint at youtube-transcript.ai. It only requests
public caption tracks and does not bypass private, members-only, or disabled captions.
"""

from __future__ import annotations

import argparse
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
TIMESTAMP_RE = re.compile(r"^\[(?P<stamp>\d{1,2}:\d{2}(?::\d{2})?)\]\s*(?P<text>.*)$")


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
                if response.status == 200 and TIMESTAMP_RE.search(body, re.MULTILINE):
                    return body, url, content_type
                errors.append(f"{url}: unusable response ({len(body)} bytes, {content_type})")
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


def parse_markdown(body: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw_line in body.splitlines():
        line = raw_line.strip()
        match = TIMESTAMP_RE.match(line)
        if not match:
            continue
        text = " ".join(match.group("text").split())
        if not text:
            continue
        rows.append({
            "start": seconds_from_stamp(match.group("stamp")),
            "text": text,
        })
    return rows


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
                "error": "provider response contained no timestamped transcript rows",
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
            "raw_file": str(raw_path.relative_to(output)),
            "transcript_file": str(txt_path.relative_to(output)),
        })
        time.sleep(4)

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
