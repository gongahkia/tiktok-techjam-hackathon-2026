#!/usr/bin/env python3
"""Run deterministic M2 shadow-ranking evaluation from the locked manifest."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import random
import statistics
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from facetflow.catalog import CatalogIndex, catalog_fingerprint
from facetflow.policy import ClarificationPolicy
from facetflow.retrieval import M1_RERANKER_CONFIG, RerankerConfig, SparseRetriever
from facetflow.state import Belief, DialogueState


RUNNER_VERSION = "m2-shadow-runner-v1"
DEPTHS = (10, 20, 50, 100, 300)


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def load_config(path: str | None) -> RerankerConfig:
    if path is None:
        return M1_RERANKER_CONFIG
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return RerankerConfig(**raw)


def validate_manifest(manifest: dict, catalog_path: str) -> None:
    if manifest["catalog_sha256"] != catalog_fingerprint(catalog_path):
        raise RuntimeError("manifest catalog fingerprint does not match the requested catalog")
    observed = digest({key: value for key, value in manifest.items() if key != "manifest_sha256"})
    if observed != manifest["manifest_sha256"]:
        raise RuntimeError("manifest semantic fingerprint mismatch")
    targets = {split: set() for split in ("train", "development", "holdout")}
    for case in manifest["cases"]:
        target = case.get("target_parent_asin")
        if target:
            targets[case["split"]].add(target)
    if targets["train"] & targets["development"] or targets["train"] & targets["holdout"] or targets["development"] & targets["holdout"]:
        raise RuntimeError("manifest target overlap across splits")


def blank_state(case_id: str, spec: dict) -> DialogueState:
    state = DialogueState.create(case_id, {"preference_tags": []})
    state.scenario = spec["scenario"]
    state.category_text = spec["category_text"]
    return state


def apply_spec(state: DialogueState, spec: dict, turn: int) -> None:
    state.last_turn = turn
    state.scenario = spec["scenario"]
    state.category_text = spec["category_text"]
    for source, destination, confidence in (("hard", state.hard, 0.96), ("soft", state.soft, 0.65)):
        for item in spec[source]:
            candidate = Belief(item["attribute"], item["value"], confidence, turn, "shadow")
            state._add(candidate, hard=source == "hard")
    for item in spec["negative"]:
        candidate = Belief(item["attribute"], item["value"], 0.96, turn, "shadow_negative")
        if not any(existing.attribute == candidate.attribute and existing.value == candidate.value for existing in state.negative):
            state.negative.append(candidate)


def rank_position(ids: list[str], accepted: set[str]) -> int | None:
    for position, value in enumerate(ids, start=1):
        if value in accepted:
            return position
    return None


def candidate_position(analysis, accepted: set[str]) -> int | None:
    return rank_position([product.parent_asin for product in analysis.candidates], accepted)


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, round((len(ordered) - 1) * fraction))]


def bootstrap_interval(values: list[float], seed: str, samples: int = 400) -> dict:
    if not values:
        return {"mean": None, "low": None, "high": None, "samples": 0}
    rng = random.Random(seed)
    means = [sum(rng.choice(values) for _ in values) / len(values) for _ in range(samples)]
    return {
        "mean": round(sum(values) / len(values), 6),
        "low": round(percentile(means, 0.025), 6),
        "high": round(percentile(means, 0.975), 6),
        "samples": samples,
    }


def evaluate_case(case: dict, retriever: SparseRetriever, policy: ClarificationPolicy) -> dict:
    acceptance = case["acceptance"]
    accepted = set(acceptance["acceptable_parent_asins"])
    analyses = []
    state = blank_state(case["case_id"], case["state_turns"][0])
    started = time.perf_counter()
    if case["family"] == "metamorphic":
        for turn, spec in enumerate(case["state_turns"], start=1):
            variant = blank_state(f"{case['case_id']}_{turn}", spec)
            apply_spec(variant, spec, turn)
            analyses.append((variant, retriever.rank_candidates(variant, top_k=10)))
    else:
        for turn, spec in enumerate(case["state_turns"], start=1):
            apply_spec(state, spec, turn)
            analyses.append((state, retriever.rank_candidates(state, top_k=10)))
    elapsed_ms = (time.perf_counter() - started) * 1000
    final_state, final_analysis = analyses[-1]
    displayed_ids = [item.product.parent_asin for item in final_analysis.displayed]
    final_rank = rank_position(displayed_ids, accepted)
    candidate_rank = candidate_position(final_analysis, accepted)
    hard_violation_count = sum(item.hard_violations > 0 for item in final_analysis.displayed)
    hard_negative_ids = set(acceptance.get("hard_negative_parent_asins", []))
    initial_rank = rank_position([item.product.parent_asin for item in analyses[0][1].displayed], accepted)
    asks = [policy.decide(current_state, analysis.displayed).ask_attribute for current_state, analysis in analyses]
    result = {
        "case_id": case["case_id"],
        "split": case["split"],
        "family": case["family"],
        "group_key": case["group_key"],
        "acceptance_mode": acceptance["mode"],
        "target_parent_asin": case["target_parent_asin"],
        "final_rank": final_rank,
        "candidate_rank": candidate_rank,
        "displayed_ids": displayed_ids,
        "hard_violation_count": hard_violation_count,
        "negative_hard_negative_displayed": bool(hard_negative_ids & set(displayed_ids)),
        "initial_rank": initial_rank,
        "ranking_moved_toward_target": bool(initial_rank is None or final_rank is not None and final_rank < initial_rank),
        "unnecessary_question": bool(final_rank is not None and asks[-1] is not None),
        "asks": asks,
        "latency_ms": round(elapsed_ms, 6),
        "final_state": {
            "scenario": final_state.scenario,
            "hard": [belief.__dict__ for belief in final_state.hard],
            "negative": [belief.__dict__ for belief in final_state.negative],
            "query_terms": final_state.query_terms(),
        },
    }
    if case["family"] == "browsing_session":
        product_types = [item.product.product_type for item in final_analysis.displayed]
        result["browsing_unique_product_types"] = len(set(product_types))
        result["browsing_diversity"] = len(set(product_types)) / len(product_types) if product_types else 0.0
    if case["family"] == "intent_override":
        old = case["override"]["old_value"]
        result["override_success"] = final_rank is not None
        result["stale_preference_reappeared"] = any(old in belief.value.split() for belief in final_state.hard)
    if case["family"] == "metamorphic":
        first_ids = [item.product.parent_asin for item in analyses[0][1].displayed]
        first_rank = rank_position(first_ids, accepted)
        union = set(first_ids) | set(displayed_ids)
        result["metamorphic_top_k_overlap"] = len(set(first_ids) & set(displayed_ids)) / len(union) if union else 1.0
        result["metamorphic_target_rank_consistent"] = first_rank == final_rank
    if case["family"] == "boundary":
        result["boundary_false_positive_recommendation"] = bool(displayed_ids)
    return result


def summarize(results: list[dict]) -> dict:
    target_cases = [result for result in results if result["target_parent_asin"]]
    exact_cases = [result for result in target_cases if result["acceptance_mode"] != "acceptable_set"]
    browsing = [result for result in results if result["family"] == "browsing_session"]
    overrides = [result for result in results if result["family"] == "intent_override"]
    boundaries = [result for result in results if result["family"] == "boundary"]
    metamorphic = [result for result in results if result["family"] == "metamorphic"]
    latencies = [result["latency_ms"] for result in results]
    rates = {
        "hit_rate_at_10": [float(result["final_rank"] is not None) for result in exact_cases],
        "mrr": [0.0 if result["final_rank"] is None else 1.0 / result["final_rank"] for result in exact_cases],
        "acceptable_set_recall_at_10": [float(result["final_rank"] is not None) for result in browsing],
    }
    summary = {
        "sample_counts": {"all": len(results), "target": len(target_cases), "exact": len(exact_cases), "browsing": len(browsing)},
        "confidence_intervals": {name: bootstrap_interval(values, f"m2-bootstrap-{name}") for name, values in rates.items()},
        "candidate_recall": {
            f"at_{depth}": round(sum(result["candidate_rank"] is not None and result["candidate_rank"] <= depth for result in target_cases) / len(target_cases), 6)
            for depth in DEPTHS
        },
        "hard_constraint_violation_rate": round(sum(result["hard_violation_count"] for result in results) / max(1, sum(len(result["displayed_ids"]) for result in results)), 6),
        "negative_constraint_violation_rate": round(sum(result["negative_hard_negative_displayed"] for result in results if result["family"] == "hard_negative_ranking") / max(1, sum(result["family"] == "hard_negative_ranking" for result in results)), 6),
        "override_success_rate": round(sum(result.get("override_success", False) for result in overrides) / max(1, len(overrides)), 6),
        "stale_preference_reappearance_rate": round(sum(result.get("stale_preference_reappeared", False) for result in overrides) / max(1, len(overrides)), 6),
        "boundary_false_positive_recommendation_rate": round(sum(result.get("boundary_false_positive_recommendation", False) for result in boundaries) / max(1, len(boundaries)), 6),
        "metamorphic": {
            "mean_top_k_overlap": round(statistics.fmean(result["metamorphic_top_k_overlap"] for result in metamorphic), 6) if metamorphic else 0.0,
            "target_rank_consistency": round(sum(result["metamorphic_target_rank_consistent"] for result in metamorphic) / max(1, len(metamorphic)), 6),
        },
        "browsing": {
            "mean_diversity": round(statistics.fmean(result["browsing_diversity"] for result in browsing), 6) if browsing else 0.0,
            "mean_unique_product_types": round(statistics.fmean(result["browsing_unique_product_types"] for result in browsing), 6) if browsing else 0.0,
        },
        "unnecessary_question_rate": round(sum(result["unnecessary_question"] for result in results) / max(1, len(results)), 6),
        "ranking_movement_after_meaningful_change": round(sum(result["ranking_moved_toward_target"] for result in results if result["family"] in {"buying_session", "intent_override"}) / max(1, sum(result["family"] in {"buying_session", "intent_override"} for result in results)), 6),
        "latency_ms": {"median": round(statistics.median(latencies), 6), "p95": round(percentile(latencies, 0.95) or 0.0, 6)},
    }
    summary["by_family"] = {}
    for family in sorted({result["family"] for result in results}):
        family_results = [result for result in results if result["family"] == family]
        family_targets = [result for result in family_results if result["target_parent_asin"]]
        ranks = [result["final_rank"] for result in family_targets]
        summary["by_family"][family] = {
            "sample_count": len(family_results),
            "hit_rate_at_10": round(sum(rank is not None for rank in ranks) / max(1, len(ranks)), 6),
            "mrr": round(sum(0.0 if rank is None else 1.0 / rank for rank in ranks) / max(1, len(ranks)), 6),
            "candidate_recall_at_300": round(sum(result["candidate_rank"] is not None for result in family_targets) / max(1, len(family_targets)), 6),
            "hard_violation_rate": round(sum(result["hard_violation_count"] for result in family_results) / max(1, sum(len(result["displayed_ids"]) for result in family_results)), 6),
        }
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default="data/m2_shadow_manifest.json")
    parser.add_argument("--catalog", default="data/catalog.jsonl")
    parser.add_argument("--cache-dir", default=".facetflow_cache")
    parser.add_argument("--split", choices=("all", "train", "development", "holdout"), default="all")
    parser.add_argument("--config-json")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    manifest = json.loads((ROOT / args.manifest).read_text(encoding="utf-8"))
    validate_manifest(manifest, args.catalog)
    config = load_config(args.config_json)
    cases = [case for case in manifest["cases"] if args.split == "all" or case["split"] == args.split]
    index = CatalogIndex(args.catalog, args.cache_dir)
    try:
        retriever = SparseRetriever(index, config)
        policy = ClarificationPolicy()
        results = [evaluate_case(case, retriever, policy) for case in cases]
    finally:
        index.close()
    payload = {
        "runner_version": RUNNER_VERSION,
        "manifest_sha256": manifest["manifest_sha256"],
        "catalog_sha256": manifest["catalog_sha256"],
        "split": args.split,
        "config": asdict(config),
        "summary": summarize(results),
        "cases": results,
    }
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload["summary"], indent=2))


if __name__ == "__main__":
    main()
