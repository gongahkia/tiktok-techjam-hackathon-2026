#!/usr/bin/env python3
"""Write deterministic catalog field and facet statistics for FacetFlow."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from facetflow.catalog import FACET_RE
from facetflow.text import flatten, normalize


FIELDS = ("title", "features", "description", "price", "categories", "details", "store")


def profile(catalog: Path) -> dict:
    digest = hashlib.sha256()
    nonempty: Counter[str] = Counter()
    field_types: dict[str, str] = {}
    categories: Counter[str] = Counter()
    detail_keys: Counter[str] = Counter()
    materials: Counter[str] = Counter()
    colors: Counter[str] = Counter()
    title_lengths: list[int] = []
    rows = 0
    with catalog.open(encoding="utf-8") as handle:
        for line in handle:
            digest.update(line.encode("utf-8"))
            product = json.loads(line)
            rows += 1
            for field, value in product.items():
                field_types.setdefault(field, type(value).__name__)
                if value not in (None, "", [], {}):
                    nonempty[field] += 1
            title = str(product.get("title") or "")
            if title:
                title_lengths.append(len(title))
            categories.update(normalize(value) for value in product.get("categories") or [] if normalize(value))
            detail_keys.update(normalize(key) for key in (product.get("details") or {}) if normalize(key))
            text = " ".join(normalize(flatten(product.get(field))) for field in FIELDS)
            for value in FACET_RE.findall(text):
                value = normalize(value)
                if value in {"black", "white", "blue", "red", "pink", "green", "brown", "gray", "purple", "yellow", "orange", "beige", "tan", "gold", "silver", "navy", "ivory", "khaki"}:
                    colors[value] += 1
                else:
                    materials[value] += 1
    title_lengths.sort()
    return {
        "catalog_sha256": digest.hexdigest(),
        "row_count": rows,
        "field_types": field_types,
        "nonempty_counts": dict(sorted(nonempty.items())),
        "title_character_count": {
            "min": min(title_lengths),
            "median": title_lengths[len(title_lengths) // 2],
            "max": max(title_lengths),
        },
        "top_categories": categories.most_common(25),
        "top_detail_keys": detail_keys.most_common(25),
        "materials": materials.most_common(),
        "colors": colors.most_common(),
    }


def markdown(result: dict) -> str:
    coverage = result["nonempty_counts"]
    rows = result["row_count"]
    lines = [
        "# Catalog profile",
        "",
        f"Fingerprint: `{result['catalog_sha256']}`. Rows: `{rows}`.",
        "",
        "## Usable fields",
        "",
        "| Field | Non-empty rows | Use in FacetFlow |",
        "| --- | ---: | --- |",
        f"| title | {coverage.get('title', 0)} | strongest lexical field |",
        f"| categories | {coverage.get('categories', 0)} | category and product-type routing |",
        f"| features | {coverage.get('features', 0)} | requirements and material evidence |",
        f"| details | {coverage.get('details', 0)} | sparse color, material, brand and size evidence |",
        f"| description | {coverage.get('description', 0)} | lower-weight supporting evidence |",
        f"| store | {coverage.get('store', 0)} | brand-like supporting evidence |",
        f"| price | {coverage.get('price', 0)} | budget verification only; sparse |",
        "",
        "Price is intentionally a verifier rather than a mandatory retriever because it is missing for most rows. The catalog JSONL remains the raw-value audit source; the generated index stores normalized fields and is ignored by Git.",
        "",
        "## Frequent extracted facets",
        "",
        "| Material | Rows mentioning it | Color | Rows mentioning it |",
        "| --- | ---: | --- | ---: |",
    ]
    materials = result["materials"]
    colors = result["colors"]
    for position in range(max(len(materials), len(colors))):
        material = materials[position] if position < len(materials) else ("", "")
        color = colors[position] if position < len(colors) else ("", "")
        lines.append(f"| {material[0]} | {material[1]} | {color[0]} | {color[1]} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", default="data/catalog.jsonl")
    parser.add_argument("--json-output", default="reports/catalog_profile.json")
    parser.add_argument("--markdown-output", default="reports/catalog_profile.md")
    args = parser.parse_args()
    result = profile(Path(args.catalog))
    json_path = Path(args.json_output)
    markdown_path = Path(args.markdown_output)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(markdown(result), encoding="utf-8")


if __name__ == "__main__":
    main()
