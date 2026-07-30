#!/usr/bin/env python3
"""Fetch captions for playlist items unavailable through YouTube datacenter IPs.

Uses the documented public API at getvideotranscript.com only for public video IDs.
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

API = "https://getvideotranscript.com/api/youtube"
UA = "Mozilla/5.0 (compatible; FishingResearchBot/1.0; +https://github.com/tonetttoman/fishing)"


def stamp(seconds: float | int | None) -> str:
    value = max(0, int(float(seconds or 0)))
    hour, rem = divmod(value, 3600)
    minute, second = divmod(rem, 60)
    return f"{hour:02d}:{minute:02d}:{second:02d}"


def request_transcript(video_id: str, retries: int = 4) -> tuple[dict[str, Any] | None, str]:
    url = API + "?" + urllib.parse.urlencode({"video_id": video_id})
    last_error = ""
    for attempt in range(1, retries + 1):
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": UA,
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=300) as response:
                body = response.read().decode("utf-8", errors="replace")
            return json.loads(body), ""
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:2000]
            last_error = f"HTTP {exc.code}: {body}"
            if exc.code in {400, 404}:
                break
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
        time.sleep(min(30, 3 * attempt))
    return None, last_error


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("audio_map_json")
    parser.add_argument("--output", default="research/external_youtube_transcripts")
    args = parser.parse_args()

    mapping = json.loads(Path(args.audio_map_json).read_text(encoding="utf-8"))
    unmatched = [item for item in mapping.get("items") or [] if item.get("status") != "matched"]
    output = Path(args.output)
    clean = output / "clean_txt"
    raw = output / "raw_json"
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
        data, error = request_transcript(video_id)
        if data is None:
            failed += 1
            manifest.append({
                "index": item.get("index"),
                "video_id": video_id,
                "title": title,
                "status": "failed",
                "error": error,
            })
            continue

        (raw / f"{video_id}.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        transcript = data.get("transcript") or data.get("entries") or data.get("segments") or []
        if not data.get("success", True) or not isinstance(transcript, list) or not transcript:
            failed += 1
            manifest.append({
                "index": item.get("index"),
                "video_id": video_id,
                "title": title,
                "status": "failed",
                "error": str(data.get("error") or data.get("message") or "empty transcript"),
            })
            continue

        rows = []
        for entry in transcript:
            if not isinstance(entry, dict):
                continue
            text = " ".join(str(entry.get("text") or "").split())
            if not text:
                continue
            start = float(entry.get("start") or entry.get("offset") or 0)
            duration = float(entry.get("duration") or entry.get("dur") or 0)
            rows.append({"start": start, "duration": duration, "text": text})
        if not rows:
            failed += 1
            manifest.append({
                "index": item.get("index"),
                "video_id": video_id,
                "title": title,
                "status": "failed",
                "error": "transcript response contained no usable rows",
            })
            continue

        extracted += 1
        total_entries += len(rows)
        lines = [
            f"VIDEÓ: {title}",
            f"URL: {item.get('youtube_url', '')}",
            f"VIDEÓ_ID: {video_id}",
            "FORRÁS: getvideotranscript.com nyilvános transcript API",
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
            "transcript_file": str(txt_path.relative_to(output)),
        })
        time.sleep(2)

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
