#!/usr/bin/env python3
"""Transcribe one mapped podcast episode with faster-whisper."""

from __future__ import annotations

import argparse
import json
import os
import traceback
import urllib.request
from pathlib import Path
from typing import Any

USER_AGENT = "Mozilla/5.0 (compatible; FishingResearchBot/1.0; +https://github.com/tonetttoman/fishing)"
INITIAL_PROMPT = (
    "Magyar horgászati szakmai beszélgetés. Fontos szavak: etetőanyag, etetés, feeder, method feeder, "
    "úszós horgászat, rakós bot, matchbot, horog, előke, kosár, csali, pellet, csonti, szúnyoglárva, "
    "giliszta, föld, ponty, keszeg, dévérkeszeg, kárász, amur, márna, folyóvíz, állóvíz, meder, "
    "mélység, helykeresés, táv, dobási ritmus, stratégia, taktika, versenyhorgászat."
)


def download(url: str, destination: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "audio/*,*/*"})
    with urllib.request.urlopen(request, timeout=120) as response, destination.open("wb") as output:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            output.write(chunk)


def find_item(mapping: dict[str, Any], video_id: str) -> dict[str, Any]:
    for item in mapping.get("items") or []:
        if str(item.get("video_id")) == video_id:
            return item
    raise KeyError(f"Video ID not found in mapping: {video_id}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mapping_json")
    parser.add_argument("video_id")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--model", default="small")
    parser.add_argument("--download-root", default=".cache/faster-whisper")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_json = output_dir / f"{args.video_id}.json"
    output_txt = output_dir / f"{args.video_id}.txt"

    mapping = json.loads(Path(args.mapping_json).read_text(encoding="utf-8"))
    item = find_item(mapping, args.video_id)
    payload: dict[str, Any] = {
        "video_id": args.video_id,
        "youtube_title": item.get("youtube_title", ""),
        "youtube_url": item.get("youtube_url", ""),
        "podcast_title": item.get("podcast_title", ""),
        "audio_url": item.get("audio_url", ""),
        "rss_duration": item.get("duration", ""),
        "status": "failed",
        "segments": [],
    }

    audio_path = output_dir / f"{args.video_id}.mp3"
    try:
        audio_url = str(item.get("audio_url") or "")
        if not audio_url:
            raise RuntimeError("No audio URL for this item")
        download(audio_url, audio_path)
        if audio_path.stat().st_size < 100_000:
            raise RuntimeError(f"Downloaded audio is unexpectedly small: {audio_path.stat().st_size} bytes")

        from faster_whisper import WhisperModel

        cpu_threads = max(1, os.cpu_count() or 2)
        model = WhisperModel(
            args.model,
            device="cpu",
            compute_type="int8",
            cpu_threads=cpu_threads,
            num_workers=1,
            download_root=args.download_root,
        )
        segments, info = model.transcribe(
            str(audio_path),
            language="hu",
            beam_size=5,
            best_of=5,
            vad_filter=True,
            vad_parameters={
                "min_silence_duration_ms": 450,
                "speech_pad_ms": 250,
            },
            condition_on_previous_text=True,
            initial_prompt=INITIAL_PROMPT,
            word_timestamps=False,
        )

        rows = []
        for segment in segments:
            text = " ".join(str(segment.text or "").split())
            if not text:
                continue
            rows.append({
                "start": round(float(segment.start), 3),
                "end": round(float(segment.end), 3),
                "text": text,
                "avg_logprob": round(float(segment.avg_logprob), 5),
                "no_speech_prob": round(float(segment.no_speech_prob), 5),
            })

        if not rows:
            raise RuntimeError("Whisper returned no transcript segments")

        payload.update({
            "status": "transcribed",
            "detected_language": info.language,
            "language_probability": round(float(info.language_probability), 5),
            "audio_duration_seconds": round(float(info.duration), 3),
            "audio_size_bytes": audio_path.stat().st_size,
            "model": args.model,
            "segments": rows,
        })

        lines = [
            f"VIDEÓ: {payload['youtube_title']}",
            f"YOUTUBE: {payload['youtube_url']}",
            f"PODCAST: {payload['podcast_title']}",
            f"VIDEÓ_ID: {args.video_id}",
            f"WHISPER_MODELL: {args.model}",
            "",
        ]
        for row in rows:
            total = int(row["start"])
            hour, rem = divmod(total, 3600)
            minute, second = divmod(rem, 60)
            lines.append(f"[{hour:02d}:{minute:02d}:{second:02d}] {row['text']}")
        output_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except Exception as exc:
        payload["error"] = f"{type(exc).__name__}: {exc}"
        payload["traceback"] = traceback.format_exc(limit=20)
        output_txt.write_text(
            "\n".join([
                f"VIDEÓ: {payload['youtube_title']}",
                f"VIDEÓ_ID: {args.video_id}",
                "STATUS: failed",
                f"ERROR: {payload['error']}",
            ]) + "\n",
            encoding="utf-8",
        )
    finally:
        output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        try:
            audio_path.unlink()
        except FileNotFoundError:
            pass

    print(json.dumps({
        "video_id": args.video_id,
        "status": payload["status"],
        "segments": len(payload.get("segments") or []),
        "error": payload.get("error", ""),
    }, ensure_ascii=False))
    # Always return success so one broken episode does not cancel the matrix.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
