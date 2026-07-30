#!/usr/bin/env python3
"""Extract public YouTube playlist captions and produce clean timestamped TXT files.

The script uses yt-dlp for playlist metadata and subtitle retrieval. It does not
circumvent access controls and only processes public captions exposed by YouTube.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

TAG_RE = re.compile(r"<[^>]+>")
TIMING_RE = re.compile(
    r"^(?P<start>\d{2}:\d{2}:\d{2}[.,]\d{3})\s+-->\s+(?P<end>\d{2}:\d{2}:\d{2}[.,]\d{3})"
)
SPACE_RE = re.compile(r"\s+")
BAD_FILENAME_RE = re.compile(r"[^\w\-. ()\[\]]+", re.UNICODE)


def run(cmd: list[str], *, capture: bool = False, check: bool = True) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(cmd), flush=True)
    return subprocess.run(
        cmd,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
        check=check,
    )


def safe_name(value: str, limit: int = 110) -> str:
    value = html.unescape(value).replace("/", "-").replace("\\", "-")
    value = BAD_FILENAME_RE.sub("_", value)
    value = SPACE_RE.sub(" ", value).strip(" ._")
    return (value[:limit].rstrip() or "video")


def normalize_caption(text: str) -> str:
    text = html.unescape(TAG_RE.sub("", text))
    text = text.replace("\u200b", "").replace("\ufeff", "")
    return SPACE_RE.sub(" ", text).strip()


def vtt_to_segments(path: Path) -> list[tuple[str, str]]:
    """Return (start_timestamp, text) pairs while removing rolling-caption duplicates."""
    raw = path.read_text(encoding="utf-8", errors="replace").splitlines()
    segments: list[tuple[str, str]] = []
    i = 0
    while i < len(raw):
        match = TIMING_RE.match(raw[i].strip())
        if not match:
            i += 1
            continue
        start = match.group("start").replace(",", ".")
        i += 1
        text_lines: list[str] = []
        while i < len(raw) and raw[i].strip():
            line = raw[i].strip()
            if not line.startswith(("NOTE", "STYLE", "REGION")):
                text_lines.append(line)
            i += 1
        text = normalize_caption(" ".join(text_lines))
        if text:
            if segments and text == segments[-1][1]:
                i += 1
                continue
            if segments and text.startswith(segments[-1][1]) and len(text) > len(segments[-1][1]):
                segments[-1] = (segments[-1][0], text)
            elif segments and segments[-1][1].startswith(text):
                pass
            else:
                segments.append((start, text))
        i += 1
    return segments


def choose_vtt(files: list[Path]) -> Path | None:
    if not files:
        return None
    priorities = (".hu-orig.vtt", ".hu.vtt", ".hu-HU.vtt", ".en-orig.vtt", ".en.vtt")
    for suffix in priorities:
        for path in files:
            if path.name.endswith(suffix):
                return path
    return sorted(files)[0]


def get_playlist(url: str) -> dict[str, Any]:
    result = run(
        [
            "yt-dlp",
            "--js-runtimes",
            "node",
            "--flat-playlist",
            "--dump-single-json",
            "--no-warnings",
            url,
        ],
        capture=True,
    )
    return json.loads(result.stdout)


def extract_one(video_id: str, base: Path, retries: int, sleep_seconds: float) -> tuple[Path | None, str]:
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    pattern = str(base) + ".%(language)s.%(ext)s"
    cmd = [
        "yt-dlp",
        "--js-runtimes",
        "node",
        "--skip-download",
        "--write-subs",
        "--write-auto-subs",
        "--sub-langs",
        "hu.*,hu,en.*,en",
        "--sub-format",
        "vtt/best",
        "--no-overwrites",
        "--retries",
        str(retries),
        "--fragment-retries",
        str(retries),
        "--sleep-requests",
        str(sleep_seconds),
        "--output",
        pattern,
        video_url,
    ]
    proc = run(cmd, capture=True, check=False)
    files = list(base.parent.glob(base.name + ".*.vtt"))
    chosen = choose_vtt(files)
    message = (proc.stderr or proc.stdout or "").strip()[-4000:]
    return chosen, message


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("playlist_url")
    parser.add_argument("--output", default="youtube_transcripts")
    parser.add_argument("--retries", type=int, default=5)
    parser.add_argument("--sleep", type=float, default=1.25)
    args = parser.parse_args()

    root = Path(args.output)
    raw_dir = root / "raw_vtt"
    txt_dir = root / "clean_txt"
    raw_dir.mkdir(parents=True, exist_ok=True)
    txt_dir.mkdir(parents=True, exist_ok=True)

    playlist = get_playlist(args.playlist_url)
    entries = playlist.get("entries") or []
    (root / "playlist.json").write_text(
        json.dumps(playlist, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    manifest: list[dict[str, Any]] = []
    combined: list[str] = []

    for position, entry in enumerate(entries, start=1):
        video_id = str(entry.get("id") or "").strip()
        title = str(entry.get("title") or video_id or f"video-{position}")
        if not video_id:
            manifest.append({"index": position, "title": title, "status": "missing_video_id"})
            continue

        stem = f"{position:03d}_{video_id}_{safe_name(title)}"
        base = raw_dir / stem
        print(f"\n[{position}/{len(entries)}] {title} ({video_id})", flush=True)
        vtt, diagnostic = extract_one(video_id, base, args.retries, args.sleep)

        if vtt is None:
            manifest.append(
                {
                    "index": position,
                    "video_id": video_id,
                    "title": title,
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                    "status": "no_caption_retrieved",
                    "diagnostic": diagnostic,
                }
            )
            time.sleep(args.sleep)
            continue

        segments = vtt_to_segments(vtt)
        txt_path = txt_dir / f"{stem}.txt"
        header = [
            f"VIDEÓ: {title}",
            f"URL: https://www.youtube.com/watch?v={video_id}",
            f"VIDEÓ_ID: {video_id}",
            f"FELIRAT_FÁJL: {vtt.name}",
            "",
        ]
        body = [f"[{stamp}] {text}" for stamp, text in segments]
        txt_path.write_text("\n".join(header + body) + "\n", encoding="utf-8")

        manifest.append(
            {
                "index": position,
                "video_id": video_id,
                "title": title,
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "status": "caption_extracted",
                "caption_file": str(vtt.relative_to(root)),
                "transcript_file": str(txt_path.relative_to(root)),
                "segments": len(segments),
            }
        )
        combined.extend(["=" * 100, *header, *body, ""])
        time.sleep(args.sleep)

    (root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (root / "all_transcripts_timestamped.txt").write_text(
        "\n".join(combined) + "\n", encoding="utf-8"
    )

    ok = sum(item["status"] == "caption_extracted" for item in manifest)
    missing = len(manifest) - ok
    summary = [
        f"Playlist: {playlist.get('title', '')}",
        f"Playlist URL: {args.playlist_url}",
        f"Videos listed: {len(entries)}",
        f"Captions extracted: {ok}",
        f"Captions unavailable/failed: {missing}",
    ]
    (root / "summary.txt").write_text("\n".join(summary) + "\n", encoding="utf-8")
    print("\n" + "\n".join(summary), flush=True)
    return 0 if entries else 2


if __name__ == "__main__":
    sys.exit(main())
