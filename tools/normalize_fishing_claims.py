#!/usr/bin/env python3
"""Turn transcript candidate blocks into source-faithful fishing knowledge records."""

from __future__ import annotations

import argparse
import difflib
import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.S | re.I)
SPACE_RE = re.compile(r"\s+")

SYSTEM_PROMPT = """Te horgászati tudásmérnök vagy. Automatikus magyar videóátiratból készítesz forráshű adatbázis-rekordokat.

Kötelező szabályok:
1. Csak a kapott szövegben egyértelműen elhangzó szakmai horgászati állítást rögzíts.
2. Ne használj külső tudást, és ne egészítsd ki a forrást valószínűnek tűnő részletekkel.
3. Ne rögzíts bemutatkozást, életrajzot, versenyeredményt, reklámot, viccet, terméknevet önmagában vagy társalgási tölteléket.
4. Egy rekord egyetlen önálló szakmai állítás legyen. Az ismétléseket vond össze.
5. Az állítást rövid, természetes magyar mondatban, saját szavakkal fogalmazd meg; ne idézd hosszasan az átiratot.
6. Az automatikus átirat hibás lehet. Egyértelmű szövegkörnyezetben javíthatsz nyilvánvaló horgászati szóhibát, de bizonytalan részletet hagyj ki.
7. Különítsd el a feltételt, a javasolt műveletet, a várt hatást/indokot és a kivételt. Az üres mező értéke legyen üres szöveg.
8. A block_id értékét pontosan másold át. A forrás időbélyegét nem kell újra megadnod.
9. Egy blokkhoz legfeljebb 3 rekordot adj. Ha nincs benne használható állítás, ne adj rekordot.
10. A confidence csak high, medium vagy low lehet. High: közvetlen és konkrét kijelentés. Medium: egyértelmű, de részben környezetfüggő. Low: az átirat bizonytalan vagy hiányos.

Kategóriák: feeding, rhythm, location, distance, depth, water, weather, target_fish, bait, groundbait, rig, hook, line, feeder, float, presentation, fish_behavior, switching, competition, fish_care, other.

Kizárólag érvényes JSON objektumot adj ebben a formában:
{"claims":[{"block_id":"...","category":"feeding","statement":"...","conditions":"...","recommended_action":"...","reason_effect":"...","exception":"...","confidence":"high"}]}"""


def clean_text(value: Any) -> str:
    return SPACE_RE.sub(" ", str(value or "")).strip()


def request_chat(server: str, messages: list[dict[str, str]], max_tokens: int = 2200) -> str:
    payload = {
        "model": "local-model",
        "messages": messages,
        "temperature": 0.05,
        "top_p": 0.85,
        "max_tokens": max_tokens,
        "seed": 42,
        "response_format": {"type": "json_object"},
    }
    request = urllib.request.Request(
        server.rstrip("/") + "/v1/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=600) as response:
        data = json.loads(response.read().decode("utf-8"))
    return str(data["choices"][0]["message"]["content"])


def parse_json_content(content: str) -> dict[str, Any]:
    content = content.strip()
    fenced = JSON_FENCE_RE.search(content)
    if fenced:
        content = fenced.group(1).strip()
    start = content.find("{")
    end = content.rfind("}")
    if start >= 0 and end > start:
        content = content[start : end + 1]
    parsed = json.loads(content)
    if not isinstance(parsed, dict):
        raise ValueError("The model response is not a JSON object")
    return parsed


def normalize_claim(raw: dict[str, Any], block_map: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    block_id = clean_text(raw.get("block_id"))
    if block_id not in block_map:
        return None
    statement = clean_text(raw.get("statement"))
    if len(statement) < 18:
        return None
    category = clean_text(raw.get("category")) or "other"
    allowed_categories = {
        "feeding", "rhythm", "location", "distance", "depth", "water", "weather", "target_fish",
        "bait", "groundbait", "rig", "hook", "line", "feeder", "float", "presentation",
        "fish_behavior", "switching", "competition", "fish_care", "other",
    }
    if category not in allowed_categories:
        category = "other"
    confidence = clean_text(raw.get("confidence")).lower()
    if confidence not in {"high", "medium", "low"}:
        confidence = "low"
    block = block_map[block_id]
    return {
        "claim_id": "",
        "block_id": block_id,
        "video_id": block["video_id"],
        "title": block["title"],
        "url": block["url"],
        "start": block["start"],
        "end": block["end"],
        "category": category,
        "statement": statement,
        "conditions": clean_text(raw.get("conditions")),
        "recommended_action": clean_text(raw.get("recommended_action")),
        "reason_effect": clean_text(raw.get("reason_effect")),
        "exception": clean_text(raw.get("exception")),
        "confidence": confidence,
        "source_block": block["text"],
    }


def normalized_key(value: str) -> str:
    value = value.casefold()
    value = re.sub(r"[^a-záéíóöőúüű0-9 ]+", " ", value)
    return SPACE_RE.sub(" ", value).strip()


def deduplicate(claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
    kept: list[dict[str, Any]] = []
    for claim in claims:
        key = normalized_key(claim["statement"] + " " + claim["conditions"] + " " + claim["recommended_action"])
        duplicate = False
        for existing in kept[-120:]:
            if claim["category"] != existing["category"]:
                continue
            other = normalized_key(existing["statement"] + " " + existing["conditions"] + " " + existing["recommended_action"])
            if key == other or difflib.SequenceMatcher(None, key, other).ratio() >= 0.91:
                duplicate = True
                break
        if not duplicate:
            kept.append(claim)
    for index, claim in enumerate(kept, start=1):
        claim["claim_id"] = f"{claim['video_id']}-C{index:04d}"
    return kept


def build_batch_prompt(batch: list[dict[str, Any]]) -> str:
    parts = ["Dolgozd fel az alábbi forrásblokkokat a rendszerutasítás szerint:\n"]
    for block in batch:
        parts.extend([
            f"BLOCK_ID: {block['block_id']}",
            f"IDŐ: {block['start']}–{block['end']}",
            f"SZÖVEG: {block['text']}",
            "---",
        ])
    return "\n".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("candidate_json")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--server", default="http://127.0.0.1:8080")
    parser.add_argument("--batch-size", type=int, default=6)
    args = parser.parse_args()

    candidate_path = Path(args.candidate_json)
    blocks = json.loads(candidate_path.read_text(encoding="utf-8"))
    if not isinstance(blocks, list):
        raise SystemExit("Candidate file must contain a JSON list")
    block_map = {str(block["block_id"]): block for block in blocks}
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    video_id = str(blocks[0]["video_id"] if blocks else candidate_path.stem)

    claims: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    batches = [blocks[i : i + args.batch_size] for i in range(0, len(blocks), args.batch_size)]

    for index, batch in enumerate(batches, start=1):
        prompt = build_batch_prompt(batch)
        last_error = ""
        parsed: dict[str, Any] | None = None
        for attempt in range(1, 4):
            try:
                content = request_chat(
                    args.server,
                    [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                )
                parsed = parse_json_content(content)
                break
            except Exception as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                time.sleep(2 * attempt)
        if parsed is None:
            failures.append({"batch": index, "block_ids": [b["block_id"] for b in batch], "error": last_error})
            continue
        raw_claims = parsed.get("claims") or []
        if not isinstance(raw_claims, list):
            failures.append({"batch": index, "block_ids": [b["block_id"] for b in batch], "error": "claims is not a list"})
            continue
        for raw in raw_claims:
            if not isinstance(raw, dict):
                continue
            claim = normalize_claim(raw, block_map)
            if claim:
                claims.append(claim)
        print(f"{video_id}: batch {index}/{len(batches)}, claims={len(claims)}", flush=True)

    claims = deduplicate(claims)
    payload = {
        "video_id": video_id,
        "candidate_blocks": len(blocks),
        "claims": claims,
        "failed_batches": failures,
    }
    (output_dir / f"{video_id}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = []
    if blocks:
        lines.extend([f"VIDEÓ: {blocks[0]['title']}", f"URL: {blocks[0]['url']}", f"VIDEÓ_ID: {video_id}", ""])
    for claim in claims:
        lines.extend([
            claim["claim_id"],
            f"IDŐ: {claim['start']}–{claim['end']}",
            f"KATEGÓRIA: {claim['category']}",
            f"ÁLLÍTÁS: {claim['statement']}",
            f"FELTÉTEL: {claim['conditions']}",
            f"JAVASOLT MŰVELET: {claim['recommended_action']}",
            f"INDOK / VÁRT HATÁS: {claim['reason_effect']}",
            f"KIVÉTEL / KORLÁT: {claim['exception']}",
            f"BIZONYOSSÁG: {claim['confidence']}",
            "",
        ])
    if failures:
        lines.extend(["FELDOLGOZÁSI HIBÁK", json.dumps(failures, ensure_ascii=False, indent=2), ""])
    (output_dir / f"{video_id}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"video_id": video_id, "blocks": len(blocks), "claims": len(claims), "failed_batches": len(failures)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
