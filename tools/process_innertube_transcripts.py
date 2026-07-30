#!/usr/bin/env python3
"""Convert InnerTube transcript JSON into timestamped text and fishing research candidates."""

from __future__ import annotations

import argparse
import html
import json
import math
import re
from pathlib import Path
from typing import Any, Iterable

SPACE_RE = re.compile(r"\s+")
BAD_FILENAME_RE = re.compile(r"[^\w\-. ()\[\]]+", re.UNICODE)

DOMAIN_TERMS = {
    "etet", "alapoz", "ráetet", "kosár", "feeder", "method", "úszó", "rakós", "match",
    "csali", "horog", "előke", "zsinór", "ólom", "szerelék", "forgó", "kapocs", "gumiz",
    "dob", "klipsz", "táv", "ritmus", "ütem", "perc", "másodperc", "pontos", "pontosság",
    "mélység", "meder", "iszap", "kavics", "törés", "padka", "part", "helykeres", "szonár",
    "áraml", "sodrás", "folyó", "állóvíz", "csatorna", "tó", "víztározó", "bányató",
    "hőmérséklet", "hideg", "meleg", "évszak", "szél", "légnyomás", "front", "vízállás",
    "ponty", "keszeg", "dévér", "karika", "bodorka", "kárász", "amur", "márna", "küsz", "géb",
    "hal", "raj", "kapás", "fáraszt", "merít", "elveszt", "akad", "száj", "táplálkoz",
    "pellet", "bojli", "morzsa", "kenyér", "kukorica", "mag", "csonti", "szúnyog", "giliszta",
    "báb", "élőanyag", "föld", "ragaszt", "aroma", "illat", "íz", "szín", "olaj", "liszt",
    "szemcse", "bont", "felhő", "nedves", "kever", "szita", "erjeszt", "vajsav", "ph",
    "wafter", "pop-up", "popup", "balanced", "csalogat", "szelekt", "bónusz", "átlagméret",
    "verseny", "edzés", "szektor", "pálya", "stratég", "taktik", "vált", "kereső", "terv",
}

ACTION_TERMS = {
    "kell", "érdemes", "fontos", "szükséges", "használ", "válassz", "választ", "növel",
    "csökkent", "sűrít", "ritkít", "vált", "próbál", "figyel", "kerül", "hagyd", "tarts",
    "indul", "kezd", "alapoz", "dob", "etet", "vár", "mér", "keres", "állít", "módosít",
    "működik", "nem működik", "jobb", "rosszabb", "előny", "hátrány", "ok", "miért",
}

CONDITION_TERMS = {
    "ha", "amikor", "amennyiben", "akkor", "esetén", "függ", "kivéve", "mindig", "soha",
    "először", "utána", "közben", "addig", "amíg", "miután", "helyett", "különben",
}

NOISE_TERMS = {
    "iratkozz", "feliratkoz", "lájk", "like", "komment", "szponzor", "támogató", "reklám",
    "podcast", "csatornánk", "kövess", "instagram", "facebook", "nyereményjáték", "köszöntelek",
    "sziasztok", "jó reggelt", "jó estét", "üdvözl", "mikrofon", "kamera", "stúdió",
}


def norm(text: str) -> str:
    return SPACE_RE.sub(" ", html.unescape(text or "")).strip()


def safe_name(value: str, limit: int = 120) -> str:
    value = BAD_FILENAME_RE.sub("_", norm(value).replace("/", "-").replace("\\", "-"))
    return (value[:limit].strip(" ._") or "video")


def stamp(seconds: float | int | None) -> str:
    total = max(0, int(float(seconds or 0)))
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def stems(text: str, terms: Iterable[str]) -> int:
    low = text.casefold()
    return sum(1 for term in terms if term in low)


def candidate_score(text: str) -> int:
    low = text.casefold()
    domain = stems(low, DOMAIN_TERMS)
    action = stems(low, ACTION_TERMS)
    condition = stems(low, CONDITION_TERMS)
    noise = stems(low, NOISE_TERMS)
    numbers = 1 if re.search(r"\b\d+(?:[.,]\d+)?\s*(?:m|cm|mm|g|kg|perc|másodperc|fok|°c|db)\b", low) else 0
    negation = 1 if re.search(r"\b(ne|nem|se|soha)\b", low) else 0
    causal = 1 if any(x in low for x in ("azért", "mert", "emiatt", "ennek az oka", "következ")) else 0
    score = min(domain, 5) + min(action, 3) + min(condition, 2) + numbers + negation + causal
    if noise and domain < 2:
        score -= 4
    if len(text) < 45:
        score -= 1
    return score


def build_blocks(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge caption fragments into readable 15–45 second blocks."""
    blocks: list[dict[str, Any]] = []
    current: list[str] = []
    start = 0.0
    end = 0.0

    def flush() -> None:
        nonlocal current, start, end
        text = norm(" ".join(current))
        if text:
            blocks.append({"start": start, "end": end, "text": text})
        current = []

    for seg in segments:
        text = norm(str(seg.get("text") or ""))
        if not text:
            continue
        seg_start = float(seg.get("start") or 0)
        seg_end = seg_start + float(seg.get("dur") or 0)
        if not current:
            start = seg_start
        current.append(text)
        end = max(end, seg_end)
        joined = " ".join(current)
        duration = end - start
        sentence_end = bool(re.search(r"[.!?…][\"')\]]?$", text))
        if len(joined) >= 520 or duration >= 45 or (duration >= 16 and sentence_end):
            flush()
            end = 0.0
    flush()
    return blocks


def choose_candidates(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for i, block in enumerate(blocks):
        score = candidate_score(block["text"])
        if score < 4:
            continue
        # Include one neighbouring block where it completes an explanation.
        left = blocks[i - 1]["text"] if i > 0 and candidate_score(blocks[i - 1]["text"]) >= 2 else ""
        right = blocks[i + 1]["text"] if i + 1 < len(blocks) and candidate_score(blocks[i + 1]["text"]) >= 2 else ""
        text = norm(" ".join(part for part in (left, block["text"], right) if part))
        item = {
            "start": blocks[i - 1]["start"] if left else block["start"],
            "end": blocks[i + 1]["end"] if right else block["end"],
            "score": score,
            "text": text,
        }
        if selected and item["text"] == selected[-1]["text"]:
            continue
        if selected and item["start"] <= selected[-1]["end"] and item["text"] in selected[-1]["text"]:
            continue
        selected.append(item)
    return selected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_json")
    parser.add_argument("--output", default="research/youtube_transcripts")
    args = parser.parse_args()

    source = json.loads(Path(args.input_json).read_text(encoding="utf-8"))
    results = source.get("results") if isinstance(source, dict) else source
    if not isinstance(results, list):
        raise SystemExit("InnerTube JSON does not contain a results list")

    root = Path(args.output)
    clean_dir = root / "clean_txt"
    clean_dir.mkdir(parents=True, exist_ok=True)

    manifest: list[dict[str, Any]] = []
    combined: list[str] = []
    candidate_lines: list[str] = [
        "HORGÁSZATI SZAKMAI ÁLLÍTÁSJELÖLTEK – AUTOMATIKUS ELSŐ SZŰRÉS",
        "=" * 100,
        "",
        "A blokkok valódi feliratokból származnak. Ez még nem a végleges, normalizált tudásbázis:",
        "a következő fázisban minden jelöltet szakmailag értelmezni, deduplikálni és forrásolni kell.",
        "",
    ]

    extracted = 0
    failed = 0
    total_segments = 0
    total_candidates = 0

    for index, result in enumerate(results, start=1):
        video_id = str(result.get("videoId") or "")
        title = norm(str(result.get("title") or video_id or f"video-{index}"))
        url = str(result.get("url") or f"https://www.youtube.com/watch?v={video_id}")
        error = norm(str(result.get("error") or ""))
        language = str(result.get("language") or "")
        segments = result.get("segments") or []
        if not isinstance(segments, list):
            segments = []

        entry = {
            "index": index,
            "video_id": video_id,
            "title": title,
            "url": url,
            "language": language,
        }

        if error or not segments:
            failed += 1
            entry.update({"status": "failed", "error": error or "empty transcript"})
            manifest.append(entry)
            continue

        extracted += 1
        total_segments += len(segments)
        stem = f"{index:03d}_{video_id}_{safe_name(title)}"
        txt_path = clean_dir / f"{stem}.txt"
        transcript_lines = [
            f"VIDEÓ: {title}",
            f"URL: {url}",
            f"VIDEÓ_ID: {video_id}",
            f"NYELV: {language}",
            "",
        ]
        transcript_lines.extend(
            f"[{stamp(seg.get('start'))}] {norm(str(seg.get('text') or ''))}"
            for seg in segments
            if norm(str(seg.get("text") or ""))
        )
        txt_path.write_text("\n".join(transcript_lines) + "\n", encoding="utf-8")
        combined.extend(["=" * 100, *transcript_lines, ""])

        blocks = build_blocks(segments)
        candidates = choose_candidates(blocks)
        total_candidates += len(candidates)
        candidate_lines.extend([
            "#" * 100,
            f"VIDEÓ: {title}",
            f"URL: {url}",
            f"VIDEÓ_ID: {video_id}",
            f"NYELV: {language}",
            f"JELÖLTEK: {len(candidates)}",
            "",
        ])
        for n, item in enumerate(candidates, start=1):
            candidate_lines.append(
                f"[{video_id}-{n:04d}] [{stamp(item['start'])}–{stamp(item['end'])}] "
                f"[pontszám: {item['score']}] {item['text']}"
            )
            candidate_lines.append("")

        entry.update({
            "status": "caption_extracted",
            "segments": len(segments),
            "blocks": len(blocks),
            "professional_candidates": len(candidates),
            "transcript_file": str(txt_path.relative_to(root)),
        })
        manifest.append(entry)

    root.mkdir(parents=True, exist_ok=True)
    (root / "innertube_response.json").write_text(
        json.dumps(source, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (root / "all_transcripts_timestamped.txt").write_text(
        "\n".join(combined) + "\n", encoding="utf-8"
    )
    (root / "professional_candidates.txt").write_text(
        "\n".join(candidate_lines) + "\n", encoding="utf-8"
    )
    summary = [
        f"Videos returned: {len(results)}",
        f"Captions extracted: {extracted}",
        f"Captions unavailable/failed: {failed}",
        f"Timestamped caption segments: {total_segments}",
        f"Professional candidate blocks: {total_candidates}",
        f"Warnings: {len(source.get('warnings') or []) if isinstance(source, dict) else 0}",
    ]
    (root / "summary.txt").write_text("\n".join(summary) + "\n", encoding="utf-8")
    print("\n".join(summary))
    return 0 if extracted else 2


if __name__ == "__main__":
    raise SystemExit(main())
