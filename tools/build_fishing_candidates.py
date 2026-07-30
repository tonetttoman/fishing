#!/usr/bin/env python3
"""Build high-recall technical candidate blocks from cleaned fishing transcripts."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

TIME_RE = re.compile(r"^\[(\d{2}:\d{2}:\d{2})\]\s*(.*)$")
SENTENCE_RE = re.compile(r"(?<=[.!?…])\s+(?=(?:>>\s*)?[A-ZÁÉÍÓÖŐÚÜŰ0-9])")
SPACE_RE = re.compile(r"\s+")

STRONG_TERMS = {
    "etetőanyag", "etetés", "etetni", "alapozás", "ráetetés", "ütemes etetés", "etetőkosár",
    "feeder", "method", "hosszúelők", "úszó", "rakós", "matchbot", "bolognai", "spicc",
    "horog", "előke", "zsinór", "szerelék", "kosár", "ólmozás", "úszótest", "forgó", "kapocs",
    "dobás", "dobási", "klipsz", "klipszel", "távolság", "horgásztáv", "ritmus", "ütem",
    "mélység", "meder", "iszap", "kavics", "törés", "padka", "helykeresés", "szonár", "radar",
    "áramlás", "sodrás", "folyóvíz", "állóvíz", "csatorna", "víztározó", "bányató", "kubik",
    "vízhőmérséklet", "hőmérséklet", "vízállás", "front", "légnyomás", "szélirány", "vízréteg",
    "ponty", "keszeg", "dévér", "bodorka", "karikakeszeg", "kárász", "amur", "márna", "küsz", "géb",
    "kapás", "fárasztás", "halvesztés", "bónuszhal", "célhal", "szelektálás", "halraj", "táplálkozás",
    "pellet", "bojli", "morzsa", "kenyér", "kukorica", "mag", "csonti", "szúnyoglárva", "giliszta",
    "báb", "élőanyag", "etetőföld", "föld", "ragasztott", "aroma", "vajsav", "wafter", "pop-up",
    "szemcse", "bontás", "felhő", "nedvesítés", "keverés", "szitálás", "erjesztés", "olajtartalom",
    "stratégia", "taktika", "tervváltás", "távváltás", "helyváltás", "módszerváltás", "keresőhorgászat",
}

ACTION_TERMS = {
    "kell", "érdemes", "fontos", "szükséges", "célszerű", "használ", "választ", "növel", "csökkent",
    "sűrít", "ritkít", "vált", "próbál", "figyel", "kerül", "tart", "indul", "kezd", "alapoz",
    "dob", "etet", "vár", "mér", "keres", "állít", "módosít", "rövidít", "hosszabbít", "csíp",
    "működik", "nem működik", "jobb", "rosszabb", "előny", "hátrány", "megoldás", "hiba", "ok",
}

CONDITION_TERMS = {
    "ha ", "amikor", "amennyiben", "akkor", "esetén", "függ", "kivéve", "mindig", "soha", "először",
    "utána", "közben", "addig", "amíg", "miután", "helyett", "különben", "hideg víz", "meleg víz",
    "sekély", "mély", "gyors víz", "lassú víz", "sok hal", "kevés hal", "apróhal", "nagyhal",
}

NOISE_TERMS = {
    "iratkozz", "feliratkoz", "lájk", "komment", "szponzor", "támogató", "reklám", "podcast",
    "csatornánk", "kövess", "instagram", "facebook", "nyereményjáték", "köszöntelek", "sziasztok",
    "jó estét", "jó reggelt", "mikrofon", "kamera", "stúdió", "adás elején", "nézőink", "műsorvezető",
}

UNITS_RE = re.compile(r"\b\d+(?:[.,]\d+)?\s*(?:m|cm|mm|g|kg|perc|másodperc|fok|°c|db|szem|liter)\b", re.I)


def clean(text: str) -> str:
    text = text.replace(">>", " ").replace("[zene]", " ").replace("[nevetés]", " ")
    return SPACE_RE.sub(" ", text).strip()


def term_hits(text: str, terms: set[str]) -> set[str]:
    low = text.casefold()
    return {term for term in terms if term in low}


def score_block(text: str) -> tuple[int, dict[str, Any]]:
    strong = term_hits(text, STRONG_TERMS)
    action = term_hits(text, ACTION_TERMS)
    conditions = term_hits(text, CONDITION_TERMS)
    noise = term_hits(text, NOISE_TERMS)
    units = bool(UNITS_RE.search(text))
    causal = any(term in text.casefold() for term in ("mert", "azért", "emiatt", "ennek az oka", "következ"))
    negation = bool(re.search(r"\b(?:nem|ne|soha|tilos)\b", text.casefold()))
    score = min(len(strong), 6) * 2 + min(len(action), 3) + min(len(conditions), 2) + int(units) + int(causal) + int(negation)
    if noise and len(strong) < 2:
        score -= 6
    if len(text) < 55:
        score -= 2
    return score, {
        "strong_terms": sorted(strong),
        "action_terms": sorted(action),
        "condition_terms": sorted(conditions),
        "has_numeric_unit": units,
        "has_causal_language": causal,
        "has_negation": negation,
    }


def split_sentences(text: str) -> list[str]:
    text = clean(text)
    if not text:
        return []
    pieces = SENTENCE_RE.split(text)
    return [clean(piece) for piece in pieces if clean(piece)]


def build_blocks(segments: list[dict[str, str]]) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    current: list[str] = []
    start = "00:00:00"
    end = "00:00:00"

    def flush() -> None:
        nonlocal current, start, end
        text = clean(" ".join(current))
        if text:
            score, signals = score_block(text)
            if score >= 4 and signals["strong_terms"]:
                blocks.append({"start": start, "end": end, "text": text, "score": score, "signals": signals})
        current = []

    for segment in segments:
        sentences = split_sentences(segment["text"])
        for sentence in sentences:
            if not current:
                start = segment["time"]
            prospective = clean(" ".join(current + [sentence]))
            if current and len(prospective) > 1200:
                flush()
                start = segment["time"]
            current.append(sentence)
            end = segment["time"]
            if len(" ".join(current)) >= 550 and sentence.endswith((".", "?", "!", "…")):
                flush()
    flush()
    return blocks


def parse_transcript(path: Path) -> tuple[dict[str, str], list[dict[str, str]]]:
    header: dict[str, str] = {}
    segments: list[dict[str, str]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = TIME_RE.match(line)
        if match:
            text = clean(match.group(2))
            if text:
                segments.append({"time": match.group(1), "text": text})
        elif ": " in line and not segments:
            key, value = line.split(": ", 1)
            header[key.strip()] = value.strip()
    return header, segments


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("transcript_dir")
    parser.add_argument("--output", default="research/fishing_candidates")
    args = parser.parse_args()

    source_dir = Path(args.transcript_dir)
    output = Path(args.output)
    per_video = output / "per_video"
    per_video.mkdir(parents=True, exist_ok=True)

    manifest: list[dict[str, Any]] = []
    combined: list[str] = []
    total_blocks = 0

    for path in sorted(source_dir.glob("*.txt")):
        header, segments = parse_transcript(path)
        video_id = header.get("VIDEÓ_ID", path.stem.split("_")[-1])
        title = header.get("VIDEÓ", path.stem)
        url = header.get("URL", f"https://www.youtube.com/watch?v={video_id}")
        blocks = build_blocks(segments)
        rows = []
        for number, block in enumerate(blocks, start=1):
            rows.append({
                "block_id": f"{video_id}-{number:04d}",
                "video_id": video_id,
                "title": title,
                "url": url,
                **block,
            })
        (per_video / f"{video_id}.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        manifest.append({
            "video_id": video_id, "title": title, "url": url,
            "source_file": str(path), "segments": len(segments), "candidate_blocks": len(rows),
            "candidate_file": str((per_video / f"{video_id}.json").relative_to(output)),
        })
        total_blocks += len(rows)
        combined.extend([
            "=" * 100, f"VIDEÓ: {title}", f"URL: {url}", f"VIDEÓ_ID: {video_id}",
            f"SZAKMAI JELÖLTBLOKKOK: {len(rows)}", "",
        ])
        for row in rows:
            combined.append(f"[{row['block_id']}] [{row['start']}–{row['end']}] [pontszám: {row['score']}] {row['text']}")
            combined.append("")

    output.mkdir(parents=True, exist_ok=True)
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "all_candidate_blocks.txt").write_text("\n".join(combined) + "\n", encoding="utf-8")
    summary = [
        f"Videos processed: {len(manifest)}",
        f"High-recall professional candidate blocks: {total_blocks}",
    ]
    (output / "summary.txt").write_text("\n".join(summary) + "\n", encoding="utf-8")
    print("\n".join(summary))
    return 0 if manifest else 2


if __name__ == "__main__":
    raise SystemExit(main())
