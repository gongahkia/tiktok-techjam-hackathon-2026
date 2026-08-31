#!/usr/bin/env python3
"""Generate the locked, catalog-derived M2 shadow evaluation manifest."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from facetflow.catalog import _brand, _facet_values, _product_type, catalog_fingerprint
from facetflow.text import flatten, normalize, tokens


GENERATOR_VERSION = "m2-shadow-generator-v2"
SEED = "facetflow-m2-shadow-seed-v2-2026-08-31"
SPLITS = ("train", "development", "holdout")
TEMPLATES = {
    "train": "catalog_anchor_compact_v1",
    "development": "catalog_anchor_context_v1",
    "holdout": "catalog_anchor_discovery_v1",
}


def stable_number(*parts: str) -> int:
    return int(hashlib.sha256("\0".join(parts).encode("utf-8")).hexdigest()[:16], 16)


def split_for(group_key: str) -> str:
    bucket = stable_number(SEED, "split", group_key) % 10
    return "train" if bucket < 6 else "development" if bucket < 8 else "holdout"


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def belief(attribute: str, value: str) -> dict:
    return {"attribute": attribute, "value": value}


def state_spec(category: str, hard: list[dict] | None = None, soft: list[dict] | None = None, negative: list[dict] | None = None, scenario: str = "buying") -> dict:
    return {
        "scenario": scenario,
        "category_text": category,
        "hard": hard or [],
        "soft": soft or [],
        "negative": negative or [],
    }


def load_products(path: Path) -> list[dict]:
    document_frequency: Counter[str] = Counter()
    raw_products: list[dict] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            raw = json.loads(line)
            all_text = " ".join(normalize(flatten(raw.get(field))) for field in ("title", "categories", "features", "details", "description", "store"))
            document_frequency.update({term for term in tokens(all_text) if len(term) >= 4})
            raw_products.append(raw)
    products: list[dict] = []
    for raw in raw_products:
        title = normalize(raw.get("title"))
        categories = normalize(flatten(raw.get("categories")))
        features = normalize(flatten(raw.get("features")))
        details = normalize(flatten(raw.get("details")))
        description = normalize(flatten(raw.get("description")))
        store = normalize(raw.get("store"))
        all_text = " ".join((title, categories, features, details, store, description))
        materials, colors = _facet_values(all_text)
        distinctive = sorted((term for term in set(tokens(title)) if document_frequency[term] == 1 and len(term) >= 4), key=lambda value: stable_number(SEED, str(raw["parent_asin"]), value))
        if not distinctive:
            continue
        product_type = _product_type(categories, title)
        brand = _brand(store, details)
        if not product_type or product_type == "product":
            continue
        products.append({
            "parent_asin": str(raw["parent_asin"]),
            "title": title,
            "product_type": product_type,
            "brand": brand,
            "materials": list(materials),
            "colors": list(colors),
            "distinctive_token": distinctive[0],
        })
    return products


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", default="data/catalog.jsonl")
    parser.add_argument("--output", default="data/m2_shadow_manifest.json")
    parser.add_argument("--anchors", type=int, default=180)
    args = parser.parse_args()
    if args.anchors < 90:
        raise ValueError("--anchors must be at least 90 to support scenario-level holdout analysis")
    catalog_path = Path(args.catalog)
    products = load_products(catalog_path)
    by_type: dict[str, list[dict]] = defaultdict(list)
    by_type_attribute: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for product in products:
        by_type[product["product_type"]].append(product)
        for material in product["materials"]:
            by_type_attribute[(product["product_type"], "material", material)].append(product)
        for color in product["colors"]:
            by_type_attribute[(product["product_type"], "color", color)].append(product)

    selected = sorted(products, key=lambda product: stable_number(SEED, "anchor", product["parent_asin"]))[:args.anchors]
    cases: list[dict] = []
    boundary_groups: set[str] = set()
    for sequence, product in enumerate(selected):
        group_key = f"{product['brand']}|{product['product_type']}"
        split = split_for(group_key)
        template = TEMPLATES[split]
        attributes = [("material", value) for value in product["materials"]] + [("color", value) for value in product["colors"]]
        primary_attribute = attributes[0] if attributes else None
        feature = belief("feature", product["distinctive_token"])
        primary = belief(*primary_attribute) if primary_attribute else None
        base = {
            "split": split,
            "group_key": group_key,
            "template_id": template,
            "target_parent_asin": product["parent_asin"],
            "target_summary": {key: product[key] for key in ("product_type", "brand", "materials", "colors", "distinctive_token")},
        }
        exact_state = state_spec(product["product_type"], [item for item in (primary, feature) if item])
        cases.append({
            **base,
            "case_id": f"anchor_{sequence:04d}",
            "family": "product_anchor",
            "acceptance": {"mode": "exact", "acceptable_parent_asins": [product["parent_asin"]]},
            "state_turns": [exact_state],
            "query_text": f"{template}: identify a {product['product_type']} using catalog-grounded brand, attribute, and title evidence.",
        })
        if primary:
            kind, value = primary_attribute
            alternatives = [candidate for candidate in by_type[product["product_type"]] if value not in candidate[f"{kind}s"]]
            opposite_values = sorted({candidate_value for candidate in by_type[product["product_type"]] for candidate_value in candidate[f"{kind}s"] if candidate_value != value and candidate_value not in product[f"{kind}s"]})
            if alternatives and opposite_values:
                negative_value = opposite_values[stable_number(SEED, "negative-value", product["parent_asin"]) % len(opposite_values)]
                negative_candidates = [candidate for candidate in alternatives if negative_value in candidate[f"{kind}s"]]
                negative = (negative_candidates or alternatives)[stable_number(SEED, "negative", product["parent_asin"]) % len(negative_candidates or alternatives)]
                cases.append({
                    **base,
                    "case_id": f"negative_{sequence:04d}",
                    "family": "hard_negative_ranking",
                    "acceptance": {
                        "mode": "exact_with_hard_negative",
                        "acceptable_parent_asins": [product["parent_asin"]],
                        "hard_negative_parent_asins": [negative["parent_asin"]],
                    },
                    "state_turns": [state_spec(product["product_type"], [item for item in (primary, feature) if item], negative=[belief(kind, negative_value)])],
                    "query_text": f"{template}: select the matching {product['product_type']} while excluding an otherwise plausible conflicting {kind}.",
                })
            acceptable = by_type_attribute[(product["product_type"], kind, value)]
            acceptable_ids = sorted(candidate["parent_asin"] for candidate in acceptable)[:50]
            cases.append({
                **base,
                "case_id": f"buying_{sequence:04d}",
                "family": "buying_session",
                "acceptance": {"mode": "exact", "acceptable_parent_asins": [product["parent_asin"]]},
                "state_turns": [
                    state_spec(product["product_type"], scenario="buying"),
                    state_spec(product["product_type"], [primary], scenario="buying"),
                    exact_state,
                ],
                "query_text": f"{template}: progressively narrow a purchase from category to {kind} to a distinctive product concept.",
            })
            cases.append({
                **base,
                "case_id": f"browsing_{sequence:04d}",
                "family": "browsing_session",
                "acceptance": {"mode": "acceptable_set", "acceptable_parent_asins": acceptable_ids},
                "state_turns": [state_spec(product["product_type"], [primary], scenario="browsing")],
                "query_text": f"{template}: discover varied relevant {product['product_type']} options satisfying a catalog-derived {kind} preference.",
            })
            if opposite_values:
                old_value = opposite_values[stable_number(SEED, "override", product["parent_asin"]) % len(opposite_values)]
                cases.append({
                    **base,
                    "case_id": f"override_{sequence:04d}",
                    "family": "intent_override",
                    "acceptance": {"mode": "exact", "acceptable_parent_asins": [product["parent_asin"]]},
                    "state_turns": [
                        state_spec(product["product_type"], [belief(kind, old_value)], scenario="intent_override"),
                        state_spec(product["product_type"], [primary, feature], scenario="intent_override"),
                    ],
                    "override": {"attribute": kind, "old_value": old_value, "new_value": value},
                    "query_text": f"{template}: replace an earlier {kind} preference and verify stale preference removal.",
                })
        cases.append({
            **base,
            "case_id": f"metamorphic_{sequence:04d}",
            "family": "metamorphic",
            "acceptance": {"mode": "exact", "acceptable_parent_asins": [product["parent_asin"]]},
            "state_turns": [
                exact_state,
                state_spec(product["product_type"], list(reversed(exact_state["hard"])), scenario=exact_state["scenario"]),
            ],
            "transformations": ["constraint_order", "casing_punctuation", "polite_filler", "singular_plural"],
            "query_text": f"{template}: preserve ranking under equivalent constraint expression transformations.",
        })
        if group_key not in boundary_groups:
            boundary_groups.add(group_key)
            cases.append({
                "case_id": f"boundary_{len(boundary_groups):04d}",
                "split": split,
                "group_key": group_key,
                "template_id": template,
                "family": "boundary",
                "target_parent_asin": None,
                "target_summary": None,
                "acceptance": {"mode": "boundary", "acceptable_parent_asins": []},
                "state_turns": [state_spec("", scenario="boundary")],
                "query_text": f"{template}: request an impossible or out-of-domain item without fabricating a catalog match.",
            })

    split_cases = {split: [case for case in cases if case["split"] == split] for split in SPLITS}
    target_sets = {
        split: {case["target_parent_asin"] for case in split_cases[split] if case["target_parent_asin"]}
        for split in SPLITS
    }
    if target_sets["train"] & target_sets["development"] or target_sets["train"] & target_sets["holdout"] or target_sets["development"] & target_sets["holdout"]:
        raise RuntimeError("target parent_asin overlap across shadow splits")
    manifest = {
        "generator_version": GENERATOR_VERSION,
        "seed": SEED,
        "catalog_sha256": catalog_fingerprint(catalog_path),
        "split_policy": "brand|product_type group hash: 60% train, 20% development, 20% holdout",
        "template_policy": "split-specific template IDs are held out by split",
        "template_ids": TEMPLATES,
        "cases": sorted(cases, key=lambda case: case["case_id"]),
        "split_fingerprints": {split: digest(split_cases[split]) for split in SPLITS},
        "split_counts": {split: len(split_cases[split]) for split in SPLITS},
        "family_counts": dict(sorted(Counter(case["family"] for case in cases).items())),
    }
    manifest["manifest_sha256"] = digest({key: value for key, value in manifest.items() if key != "manifest_sha256"})
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "manifest_sha256": manifest["manifest_sha256"],
        "split_counts": manifest["split_counts"],
        "family_counts": manifest["family_counts"],
    }, indent=2))


if __name__ == "__main__":
    main()
