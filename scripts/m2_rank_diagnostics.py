#!/usr/bin/env python3
"""Diagnose public rank placement without feeding labels into runtime code."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import random
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from evaluator.local_evaluator import (
    MAX_TURNS,
    TOP_K,
    behavior_for,
    catalog_index,
    coarse_category,
    customer_reply,
    initial_message,
    intent_card,
    load_jsonl,
)
from facetflow.catalog import CatalogIndex, Product, catalog_fingerprint
from facetflow.policy import ClarificationPolicy
from facetflow.retrieval import RankedProduct, RankingAnalysis, ShadowReranker
from facetflow.state import DialogueState


DIAGNOSTIC_VERSION = "m2-rank-diagnostics-v1"
DEPTHS = (10, 20, 50, 100, 300)


def product_summary(product: Product) -> dict:
    return {
        "parent_asin": product.parent_asin,
        "title": product.title,
        "categories": product.categories,
        "product_type": product.product_type,
        "brand": product.brand,
        "materials": list(product.materials),
        "colors": list(product.colors),
        "price": product.price,
    }


def rank_of(items: tuple[RankedProduct, ...] | list[RankedProduct], target: str) -> int | None:
    for position, item in enumerate(items, start=1):
        if item.product.parent_asin == target:
            return position
    return None


def candidate_rank(candidates: tuple[Product, ...], target: str) -> int | None:
    for position, product in enumerate(candidates, start=1):
        if product.parent_asin == target:
            return position
    return None


def component_totals(item: RankedProduct | None) -> dict[str, float]:
    if item is None:
        return {}
    components = item.components
    return {
        "lexical_rank": float(components["lexical_rank_score"]),
        "category": float(components["category"]["score"]),
        "hard_match": sum(float(value["match_score"]) for value in components["hard"]),
        "hard_violation": sum(float(value["violation_score"]) for value in components["hard"]),
        "soft_match": sum(float(value["score"]) for value in components["soft"]),
        "negative_penalty": sum(float(value["penalty"]) for value in components["negative"]),
        "profile": float(components["profile_score"]),
    }


def turn_record(
    analysis,
    target: str,
    state: DialogueState,
    response: dict,
    conversion_allowed: bool,
) -> dict:
    candidate_position = candidate_rank(analysis.candidates, target)
    scored_target = next((item for item in analysis.scored if item.product.parent_asin == target), None)
    unfiltered = sorted(analysis.scored, key=lambda item: (-item.score, item.product.parent_asin))
    pool_target = next((item for item in analysis.pool if item.product.parent_asin == target), None)
    displayed_target = next((item for item in analysis.displayed if item.product.parent_asin == target), None)
    top = analysis.displayed[0] if analysis.displayed else None
    rank_ten = analysis.displayed[min(9, len(analysis.displayed) - 1)] if analysis.displayed else None
    filtered = bool(scored_target and scored_target.hard_violations and analysis.qualified_count)
    return {
        "turn": state.last_turn,
        "conversion_allowed": conversion_allowed,
        "scenario_router": state.scenario,
        "query_terms": state.query_terms(),
        "hard_constraints": [belief.__dict__ for belief in state.hard],
        "soft_preferences": [belief.__dict__ for belief in state.soft],
        "negative_constraints": [belief.__dict__ for belief in state.negative],
        "ask_attribute": response["ask_attribute"],
        "candidate_depth": len(analysis.candidates),
        "candidate_generation_rank": candidate_position,
        "pre_reranking_rank": candidate_position,
        "unfiltered_score_rank": rank_of(unfiltered, target),
        "post_filter_score_rank": rank_of(analysis.pool, target),
        "final_rank": rank_of(analysis.displayed, target),
        "target_filtered": filtered,
        "target": product_summary(scored_target.product) if scored_target else None,
        "top_competitor": product_summary(top.product) if top else None,
        "rank_ten_competitor": product_summary(rank_ten.product) if rank_ten else None,
        "target_components": scored_target.components if scored_target else None,
        "top_components": top.components if top else None,
        "rank_ten_components": rank_ten.components if rank_ten else None,
        "target_vs_rank_ten_score_margin": (
            round(scored_target.score - rank_ten.score, 6) if scored_target and rank_ten else None
        ),
        "target_component_totals": component_totals(scored_target),
        "rank_ten_component_totals": component_totals(rank_ten),
    }


def replay_sample(sample: dict, categories: dict[str, list[str]], products: dict[str, dict], retriever: ShadowReranker) -> dict:
    target = str(sample["ground_truth"]["parent_asin"])
    card = intent_card(products[target])
    seed = f"{sample.get('sample_id', '')}\0{sample.get('scenario_type', '')}"
    behavior = behavior_for(sample["scenario_type"], card, random.Random(seed))
    effective = {**sample, "intent_card": card, "behavior": behavior}
    state = DialogueState.create(f"m2_{sample['sample_id']}", sample["user_profile"])
    policy = ClarificationPolicy()
    disclosed: set[str] = set()
    boundary_used = False
    override_applied = sample["scenario_type"] != "intent_override"
    message = initial_message(effective, coarse_category(categories.get(target, [])), disclosed)
    turns: list[dict] = []
    hit_turn: int | None = None
    analysis_cache: dict[tuple, RankingAnalysis] = {}
    for turn in range(1, MAX_TURNS + 1):
        state.ingest(message, turn)
        signature = state.retrieval_signature()
        analysis = analysis_cache.get(signature)
        if analysis is None:
            analysis = retriever.rank_candidates(state, top_k=TOP_K)
            analysis_cache[signature] = analysis
        decision = policy.decide(state, analysis.displayed)
        if decision.ask_attribute:
            state.asked_attributes.add(decision.ask_attribute)
        response = {
            "ask_attribute": decision.ask_attribute,
            "recommendations": [{"parent_asin": item.product.parent_asin} for item in analysis.displayed],
        }
        state.mark_shown([item["parent_asin"] for item in response["recommendations"]])
        record = turn_record(analysis, target, state, response, override_applied)
        turns.append(record)
        if override_applied and record["final_rank"] is not None:
            hit_turn = turn
            break
        if turn == MAX_TURNS:
            break
        override = behavior.get("override") or {}
        if not override_applied and turn + 1 == int(override.get("turn", 3)):
            override_applied = True
            new_value = str(override.get("new_value", ""))
            if new_value:
                disclosed.add(new_value)
            message = str(override.get("message", "Actually, please ignore my earlier preference."))
        else:
            message, boundary_used = customer_reply(effective, response["ask_attribute"], disclosed, boundary_used)

    final = turns[-1]
    asked_turns = [record["turn"] for record in turns if record["ask_attribute"]]
    rank_before_question = next((record["candidate_generation_rank"] for record in turns if record["ask_attribute"]), None)
    rank_after_question = turns[-1]["candidate_generation_rank"] if asked_turns else None
    if not asked_turns:
        clarification_effect = "not_asked"
    elif len(final["hard_constraints"]) <= 0:
        clarification_effect = "asked_without_resolved_constraint"
    elif rank_before_question is not None and rank_after_question is not None and rank_after_question < rank_before_question:
        clarification_effect = "asked_and_candidate_rank_improved"
    else:
        clarification_effect = "asked_without_candidate_rank_improvement"

    if hit_turn is not None:
        failure_type = None
    elif sample["scenario_type"] == "boundary":
        failure_type = "boundary"
    elif final["candidate_generation_rank"] is None:
        failure_type = "retrieval"
    elif final["target_filtered"]:
        failure_type = "filtering"
    elif any(record["final_rank"] is not None and not record["conversion_allowed"] for record in turns):
        failure_type = "evaluation_timing"
    elif final["scenario_router"] not in {"buying", "browsing", "intent_override", "boundary"}:
        failure_type = "routing"
    else:
        failure_type = "ranking"
    return {
        "sample_id": sample["sample_id"],
        "scenario": sample["scenario_type"],
        "difficulty": sample.get("difficulty_bucket"),
        "target_parent_asin": target,
        "hit_turn": hit_turn,
        "failure_type": failure_type,
        "clarification_effect": clarification_effect,
        "turns": turns,
    }


def recall_summary(records: list[dict]) -> dict:
    result: dict[str, float | int] = {"sample_count": len(records)}
    finals = [record["turns"][-1] for record in records]
    for depth in DEPTHS:
        result[f"candidate_recall_at_{depth}"] = round(
            sum(final["candidate_generation_rank"] is not None and final["candidate_generation_rank"] <= depth for final in finals) / len(finals),
            6,
        ) if finals else 0.0
    return result


def aggregate(records: list[dict]) -> dict:
    misses = [record for record in records if record["failure_type"]]
    by_scenario = {scenario: recall_summary([record for record in records if record["scenario"] == scenario]) for scenario in sorted({record["scenario"] for record in records})}
    failure_counts = Counter(record["failure_type"] for record in misses)
    candidate_ranks = [record["turns"][-1]["candidate_generation_rank"] for record in records if record["turns"][-1]["candidate_generation_rank"]]
    margins = [record["turns"][-1]["target_vs_rank_ten_score_margin"] for record in misses if record["turns"][-1]["target_vs_rank_ten_score_margin"] is not None]
    component_losses: Counter[str] = Counter()
    for record in misses:
        final = record["turns"][-1]
        target_totals = final["target_component_totals"]
        competitor_totals = final["rank_ten_component_totals"]
        for feature, target_value in target_totals.items():
            if competitor_totals.get(feature, 0.0) > target_value:
                component_losses[feature] += 1
    histogram = {
        "1_10": sum(rank <= 10 for rank in candidate_ranks),
        "11_20": sum(11 <= rank <= 20 for rank in candidate_ranks),
        "21_50": sum(21 <= rank <= 50 for rank in candidate_ranks),
        "51_100": sum(51 <= rank <= 100 for rank in candidate_ranks),
        "101_300": sum(101 <= rank <= 300 for rank in candidate_ranks),
        "not_retained": len(records) - len(candidate_ranks),
    }
    return {
        "all_sessions": recall_summary(records),
        "misses": recall_summary(misses),
        "by_scenario": by_scenario,
        "failure_counts": dict(sorted(failure_counts.items())),
        "candidate_rank_histogram": histogram,
        "score_margin": {
            "sample_count": len(margins),
            "mean": round(sum(margins) / len(margins), 6) if margins else None,
            "median": round(sorted(margins)[len(margins) // 2], 6) if margins else None,
        },
        "component_loss_frequency_against_rank_ten": dict(component_losses.most_common()),
        "clarification_effects": dict(Counter(record["clarification_effect"] for record in records)),
    }


def markdown(result: dict) -> str:
    summary = result["summary"]
    lines = [
        "# M2 rank-placement diagnostics",
        "",
        f"Version: `{result['diagnostic_version']}`. Catalog fingerprint: `{result['catalog_sha256']}`. The script replays the public simulator only for post-hoc analysis; production runtime does not read these records.",
        "",
        "## Corrected candidate recall",
        "",
        "| Population | R@10 | R@20 | R@50 | R@100 | R@300 |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, values in (("all terminal sessions", summary["all_sessions"]), ("official misses", summary["misses"])):
        lines.append("| " + name + " | " + " | ".join(f"{values[f'candidate_recall_at_{depth}']:.6f}" for depth in DEPTHS) + " |")
    lines.extend([
        "",
        "## Failure and score-margin summary",
        "",
        f"- official misses: {sum(summary['failure_counts'].values())}; failure types: `{json.dumps(summary['failure_counts'], sort_keys=True)}`.",
        f"- target-versus-displayed-rank-10 score margin: mean `{summary['score_margin']['mean']}`, median `{summary['score_margin']['median']}` across {summary['score_margin']['sample_count']} rankable misses.",
        f"- candidate-rank histogram: `{json.dumps(summary['candidate_rank_histogram'], sort_keys=True)}`.",
        f"- target component lower than displayed rank-10 competitor: `{json.dumps(summary['component_loss_frequency_against_rank_ten'], sort_keys=True)}`. This is descriptive score evidence, not causal attribution.",
        f"- clarification outcomes: `{json.dumps(summary['clarification_effects'], sort_keys=True)}`.",
        "",
        "The machine-readable companion records every official miss with terminal-turn constraints, candidate/pre-filter/post-filter/final ranks, target and competitor facets, feature contributions, filtering status, clarification path, and failure classification. Aggregate values retain all 200 sessions.",
    ])
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", default="data/catalog.jsonl")
    parser.add_argument("--dataset", default="data/public_set.jsonl")
    parser.add_argument("--json-output", default="reports/m2_rank_diagnostics.json")
    parser.add_argument("--markdown-output", default="reports/m2_rank_error_analysis.md")
    parser.add_argument("--cache-dir", default=".facetflow_cache")
    args = parser.parse_args()
    catalog_ids, categories, products = catalog_index(args.catalog)
    del catalog_ids
    index = CatalogIndex(args.catalog, args.cache_dir)
    try:
        records = [replay_sample(sample, categories, products, ShadowReranker(index)) for sample in load_jsonl(args.dataset)]
        result = {
            "diagnostic_version": DIAGNOSTIC_VERSION,
            "catalog_sha256": catalog_fingerprint(args.catalog),
            "candidate_depth": 300,
            "summary": aggregate(records),
            "successful_session_count": sum(record["failure_type"] is None for record in records),
            "records": [record for record in records if record["failure_type"]],
        }
    finally:
        index.close()
    json_path = ROOT / args.json_output
    markdown_path = ROOT / args.markdown_output
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(markdown(result), encoding="utf-8")
    print(json.dumps(result["summary"], indent=2))


if __name__ == "__main__":
    main()
