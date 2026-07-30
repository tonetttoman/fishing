#!/usr/bin/env python3
"""Collect per-episode Whisper JSON files into research-ready transcript files."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

from process_innertube_transcripts import build_blocks, choose_candidates, norm, safe_name, stamp


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("raw_dir")
    parser.add_argument("--output", default="research/podcast_transcripts")
    args = parser.parse_args()

    raw_dir = Path(args.raw_dir)
    output = Path(args.output)
    clean_dir = output / "clean_txt"
    output.mkdir(parents=True, exist_ok=True)
    clean_dir.mkdir(parents=True, exist_ok=True)

    manifest: list[dict[str, Any]] = []
    combined: list[str] = []
    candidates_out: list[str] = [
        "HORGÁSZATI SZAKMAI ÁLLÍTÁSJELÖLTEK – WHISPER ÁTIRATOKBÓL",
        "=" * 100,
        "",
        "A következő blokkok valódi podcast-hangból készült automatikus átiratok.",
        "A szakmai állításokat a következő fázisban normalizálni, összevonni és ellenőrizni kell.",
        "",
    ]

    transcribed = 0
    failed = 0
    segment_count = 0
    candidate_count = 0
    duration_seconds = 0.0

    json_files = sorted(raw_dir.rglob("*.json"))
    for path in json_files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            manifest.append({"file": str(path), "status": "invalid_json", "error": str(exc)})
            failed += 1
            continue
        if not isinstance(data, dict) or "video_id" not in data:
            continue

        video_id = str(data.get("video_id") or path.stem)
        title = norm(str(data.get("youtube_title") or data.get("podcast_title") or video_id))
        status = str(data.get("status") or "failed")
        segments = data.get("segments") or []
        if status != "transcribed" or not isinstance(segments, list) or not segments:
            failed += 1
            manifest.append({
                "video_id": video_id,
                "title": title,
                "status": "failed",
                "error": data.get("error", "empty transcript"),
            })
            continue

        transcribed += 1
        segment_count += len(segments)
        duration_seconds += float(data.get("audio_duration_seconds") or 0)
        index = next((int(p) for p in path.parts if p.isdigit()), transcribed)
        stem = f"{index:03d}_{video_id}_{safe_name(title)}"
        txt_path = clean_dir / f"{stem}.txt"

        header = [
            f"VIDEÓ: {title}",
            f"YOUTUBE: {data.get('youtube_url', '')}",
            f"PODCAST: {data.get('podcast_title', '')}",
            f"VIDEÓ_ID: {video_id}",
            f"WHISPER_MODELL: {data.get('model', '')}",
            f"FELISMERT_NYELV: {data.get('detected_language', '')}",
            "",
        ]
        body = [f"[{stamp(seg.get('start'))}] {norm(str(seg.get('text') or ''))}" for seg in segments]
        txt_path.write_text("\n".join(header + body) + "\n", encoding="utf-8")
        combined.extend(["=" * 100, *header, *body, ""])

        normalized_segments = []
        for seg in segments:
            start = float(seg.get("start") or 0)
            end = float(seg.get("end") or start)
            normalized_segments.append({
                "start": start,
                "dur": max(0.0, end - start),
                "text": norm(str(seg.get("text") or "")),
            })
        blocks = build_blocks(normalized_segments)
        candidates = choose_candidates(blocks)
        candidate_count += len(candidates)

        candidates_out.extend([
            "#" * 100,
            f"VIDEÓ: {title}",
            f"YOUTUBE: {data.get('youtube_url', '')}",
            f"PODCAST: {data.get('podcast_title', '')}",
            f"VIDEÓ_ID: {video_id}",
            f"JELÖLTEK: {len(candidates)}",
            "",
        ])
        for n, item in enumerate(candidates, start=1):
            candidates_out.append(
                f"[{video_id}-{n:04d}] [{stamp(item['start'])}–{stamp(item['end'])}] "
                f"[pontszám: {item['score']}] {item['text']}"
            )
            candidates_out.append("")

        manifest.append({
            "video_id": video_id,
            "title": title,
            "youtube_url": data.get("youtube_url", ""),
            "podcast_title": data.get("podcast_title", ""),
            "status": "transcribed",
            "segments": len(segments),
            "blocks": len(blocks),
            "professional_candidates": len(candidates),
            "duration_seconds": data.get("audio_duration_seconds", 0),
            "model": data.get("model", ""),
            "transcript_file": str(txt_path.relative_to(output)),
        })

    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output / "all_transcripts_timestamped.txt").write_text(
        "\n".join(combined) + "\n", encoding="utf-8"
    )
    (output / "professional_candidates.txt").write_text(
        "\n".join(candidates_out) + "\n", encoding="utf-8"
    )
    summary = [
        f"Transcript JSON files found: {len(json_files)}",
        f"Episodes transcribed: {transcribed}",
        f"Episodes failed: {failed}",
        f"Audio duration hours: {duration_seconds / 3600:.2f}",
        f"Timestamped segments: {segment_count}",
        f"Professional candidate blocks: {candidate_count}",
    ]
    (output / "summary.txt").write_text("\n".join(summary) + "\n", encoding="utf-8")
    print("\n".join(summary))
    return 0 if transcribed else 2


if __name__ == "__main__":
    raise SystemExit(main())
