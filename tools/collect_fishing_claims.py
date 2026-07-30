#!/usr/bin/env python3
"""Collect per-video normalized claims into final TXT and JSONL knowledge files."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_dir")
    parser.add_argument("--output", default="research/fishing_knowledge")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)

    videos: list[dict[str, Any]] = []
    all_claims: list[dict[str, Any]] = []
    failed_batches = 0
    candidate_blocks = 0

    for path in sorted(input_dir.rglob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(data, dict) or "video_id" not in data or "claims" not in data:
            continue
        claims = data.get("claims") or []
        if not isinstance(claims, list):
            continue
        candidate_blocks += int(data.get("candidate_blocks") or 0)
        failed_batches += len(data.get("failed_batches") or [])
        all_claims.extend(claim for claim in claims if isinstance(claim, dict))
        videos.append({
            "video_id": data.get("video_id"),
            "claims": len(claims),
            "candidate_blocks": data.get("candidate_blocks", 0),
            "failed_batches": len(data.get("failed_batches") or []),
            "source_file": str(path),
        })

    order = {"high": 0, "medium": 1, "low": 2}
    all_claims.sort(key=lambda c: (str(c.get("title", "")), str(c.get("start", "")), order.get(str(c.get("confidence", "low")), 3)))

    with (output / "fishing_knowledge_records.jsonl").open("w", encoding="utf-8") as handle:
        for claim in all_claims:
            export = dict(claim)
            export.pop("source_block", None)
            handle.write(json.dumps(export, ensure_ascii=False) + "\n")

    lines = [
        "HORGÁSZATI STRATÉGIAI TUDÁSBÁZIS – FORRÁSHŰ SZAKMAI ÁLLÍTÁSOK",
        "=" * 100,
        "",
        "A rekordok nyilvános videófeliratokból készültek. Az állítások nem szó szerinti idézetek,",
        "hanem időbélyeggel ellátott, forráshű magyar parafrázisok. Az automatikus átirat és a",
        "gépi strukturálás miatt a rekordokat az alkalmazás végleges adatbázisába emelés előtt",
        "szakmai mintavétellel és lehetőség szerint a videórészlettel is ellenőrizni kell.",
        "",
    ]

    current_video = None
    for claim in all_claims:
        video_id = claim.get("video_id")
        if video_id != current_video:
            current_video = video_id
            lines.extend([
                "#" * 100,
                f"VIDEÓ: {claim.get('title', '')}",
                f"URL: {claim.get('url', '')}",
                f"VIDEÓ_ID: {video_id}",
                "",
            ])
        lines.extend([
            str(claim.get("claim_id", "")),
            f"IDŐ: {claim.get('start', '')}–{claim.get('end', '')}",
            f"KATEGÓRIA: {claim.get('category', '')}",
            f"SZAKMAI ÁLLÍTÁS: {claim.get('statement', '')}",
            f"ALKALMAZÁSI FELTÉTEL: {claim.get('conditions', '')}",
            f"JAVASOLT MŰVELET: {claim.get('recommended_action', '')}",
            f"INDOK / VÁRT HATÁS: {claim.get('reason_effect', '')}",
            f"KIVÉTEL / KORLÁT: {claim.get('exception', '')}",
            f"BIZONYOSSÁG: {claim.get('confidence', '')}",
            "",
        ])

    (output / "horgaszati_szakmai_allitasok_teljes.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    categories = Counter(str(c.get("category", "other")) for c in all_claims)
    confidence = Counter(str(c.get("confidence", "low")) for c in all_claims)
    by_video = defaultdict(int)
    for claim in all_claims:
        by_video[str(claim.get("video_id", ""))] += 1

    summary = {
        "videos_with_results": len(videos),
        "candidate_blocks": candidate_blocks,
        "knowledge_records": len(all_claims),
        "failed_model_batches": failed_batches,
        "categories": dict(categories.most_common()),
        "confidence": dict(confidence.most_common()),
        "claims_per_video": dict(sorted(by_video.items())),
    }
    (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "summary.txt").write_text(
        "\n".join([
            f"Videos with results: {len(videos)}",
            f"Candidate blocks reviewed: {candidate_blocks}",
            f"Source-faithful knowledge records: {len(all_claims)}",
            f"Failed model batches: {failed_batches}",
            f"High confidence: {confidence.get('high', 0)}",
            f"Medium confidence: {confidence.get('medium', 0)}",
            f"Low confidence: {confidence.get('low', 0)}",
        ]) + "\n",
        encoding="utf-8",
    )
    print((output / "summary.txt").read_text(encoding="utf-8"))
    return 0 if all_claims else 2


if __name__ == "__main__":
    raise SystemExit(main())
