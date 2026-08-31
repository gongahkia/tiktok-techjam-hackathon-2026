#!/usr/bin/env python3
"""Classify public-evaluator misses without changing evaluator semantics."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import random
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluator.local_evaluator import (
    MAX_TURNS,
    TOP_K,
    behavior_for,
    catalog_index,
    coarse_category,
    customer_reply,
    initial_message,
    intent_card,
)
from starter.agent import Agent


def replay_final_state(agent: Agent, sample: dict, categories: dict[str, list[str]], products: dict[str, dict]) -> tuple[object, str]:
    target = str(sample["ground_truth"]["parent_asin"])
    card = intent_card(products[target])
    behavior = behavior_for(sample["scenario_type"], card, random.Random(f"{sample.get('sample_id', '')}\0{sample.get('scenario_type', '')}"))
    effective = {**sample, "intent_card": card, "behavior": behavior}
    session_id = f"analysis_{sample['sample_id']}"
    agent.reset(session_id, sample["user_profile"])
    disclosed: set[str] = set()
    boundary_used = False
    override_applied = sample["scenario_type"] != "intent_override"
    message = initial_message(effective, coarse_category(categories.get(target, [])), disclosed)
    for turn in range(1, MAX_TURNS + 1):
        response = agent.respond(session_id, message, turn, TOP_K)
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
            message, boundary_used = customer_reply(effective, response.get("ask_attribute"), disclosed, boundary_used)
    return agent.sessions[session_id], target


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", required=True)
    parser.add_argument("--dataset", default="data/public_set.jsonl")
    parser.add_argument("--catalog", default="data/catalog.jsonl")
    parser.add_argument("--output", default="reports/error_analysis.md")
    args = parser.parse_args()
    result = json.loads(Path(args.result).read_text(encoding="utf-8"))
    samples = {
        item["sample_id"]: item
        for item in (json.loads(line) for line in Path(args.dataset).read_text(encoding="utf-8").splitlines() if line)
    }
    _, categories, products = catalog_index(args.catalog)
    agent = Agent(args.catalog)
    buckets: Counter[str] = Counter()
    by_scenario: Counter[str] = Counter()
    by_difficulty: Counter[str] = Counter()
    details: list[tuple[str, str, str]] = []
    for session in result["sessions"]:
        if session["hit"]:
            continue
        sample = samples[session["sample_id"]]
        state, target = replay_final_state(agent, sample, categories, products)
        if sample["scenario_type"] == "boundary":
            bucket = "boundary: no preference supplied"
        else:
            retrieved = agent.catalog.search(state.query_terms(), limit=300)
            candidate_ids = {item.parent_asin for item in retrieved}
            if target not in candidate_ids:
                bucket = "candidate generation: target outside bounded lexical pool"
            else:
                ranked = agent.retriever.retrieve(state, 300).ranked
                target_item = next((item for item in ranked if item.product.parent_asin == target), None)
                if target_item and target_item.hard_violations:
                    bucket = "constraint verification: target conflicts with retained state"
                else:
                    bucket = "reranking: target retrieved below Top-10"
        buckets[bucket] += 1
        by_scenario[sample["scenario_type"]] += 1
        by_difficulty[sample.get("difficulty_bucket", "unknown")] += 1
        details.append((sample["sample_id"], sample["scenario_type"], bucket))

    lines = [
        "# Public evaluator error analysis",
        "",
        f"Source result: `{args.result}`. This report classifies only the {sum(buckets.values())} missed public sessions; it does not alter the evaluator or agent.",
        "",
        "## Primary buckets",
        "",
        "| Bucket | Misses |",
        "| --- | ---: |",
        *[f"| {bucket} | {count} |" for bucket, count in buckets.most_common()],
        "",
        "## Misses by scenario and public difficulty label",
        "",
        "| Dimension | Count |",
        "| --- | ---: |",
        *[f"| scenario: {name} | {count} |" for name, count in sorted(by_scenario.items())],
        *[f"| difficulty: {name} | {count} |" for name, count in sorted(by_difficulty.items())],
        "",
        "## Interpretation",
        "",
        "Boundary sessions provide no preference after the agent asks, so exact-product recovery from a broad category is intrinsically underdetermined. Reranking misses are candidates that lexical retrieval found but whose deterministic score placed them below the first ten; this is the largest non-boundary bucket and the next ranking-analysis target. Candidate-generation misses are smaller, so a semantic expansion ablation is lower priority. This public breakdown is diagnostic only and must not become per-sample agent logic.",
        "",
        "## Reproducible missed-session classifications",
        "",
        "| Sample | Scenario | Bucket |",
        "| --- | --- | --- |",
        *[f"| {sample_id} | {scenario} | {bucket} |" for sample_id, scenario, bucket in details],
        "",
    ]
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
