"""Replay deterministic FacetFlow demonstrations using the real offline agent."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .agent import Agent


PROFILE = {
    "purchase_frequency": "3-4 prior purchases",
    "average_prior_rating": 4.5,
    "rating_style": "usually positive",
    "preference_tags": ["fit", "comfort", "durability"],
    "summary": "Prior purchases emphasize fit, comfort, durability.",
}

SCENARIOS = {
    "main": (
        "Preference memory, verified exclusion, and a material override.",
        (
            "I'm looking for Men Shoes, but I'm still exploring.",
            "For that, what matters is: black; leather.",
            "Actually, ignore my earlier preference. What I need is: cotton.",
            "I need something without leather.",
        ),
    ),
    "buying": (
        "A focused purchase request with two explicit catalog constraints.",
        (
            "I'm looking for Women Clothing T-Shirts. A key requirement is: cotton.",
            "For that, what matters is: short sleeve; casual.",
        ),
    ),
    "browsing": (
        "Broad discovery followed by a preference that narrows the diverse starting set.",
        (
            "I'm looking for Men Shoes, but I'm still exploring.",
            "For that, what matters is: blue; comfort.",
        ),
    ),
    "boundary": (
        "A non-shopping request that exercises the contract-safe boundary response.",
        ("I'm looking for something outside shopping, but I'm still exploring.",),
    ),
}


def product_summary(agent: Agent, recommendations: list[dict]) -> list[dict]:
    products = agent.catalog.products_by_id(item["parent_asin"] for item in recommendations)
    return [
        {
            "parent_asin": product.parent_asin,
            "title": product.title,
            "materials": list(product.materials),
            "colors": list(product.colors),
            "product_type": product.product_type,
        }
        for product in products
    ]


def replay(name: str, catalog: str, top_k: int, explain: bool) -> dict:
    description, messages = SCENARIOS[name]
    agent = Agent(catalog)
    try:
        session_id = f"demo_{name}"
        agent.reset(session_id, PROFILE)
        turns = []
        for turn, message in enumerate(messages, start=1):
            response = agent.respond(session_id, message, turn, top_k)
            record = {
                "turn": turn,
                "user": message,
                "assistant": response["message"],
                "ask_attribute": response["ask_attribute"],
                "products": product_summary(agent, response["recommendations"]),
            }
            if explain:
                record["explain"] = agent.explain(session_id)
            turns.append(record)
        return {"scenario": name, "description": description, "turns": turns}
    finally:
        agent.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=(*SCENARIOS, "all"), default="main")
    parser.add_argument("--catalog", default="data/catalog.jsonl")
    parser.add_argument("--cache-dir")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--explain", action="store_true")
    parser.add_argument("--output", help="optional JSON file for recording a demo fixture")
    args = parser.parse_args()
    if args.cache_dir:
        os.environ["FACETFLOW_CACHE_DIR"] = args.cache_dir
    names = tuple(SCENARIOS) if args.scenario == "all" else (args.scenario,)
    payload = {"scenarios": [replay(name, args.catalog, args.top_k, args.explain) for name in names]}
    rendered = json.dumps(payload, indent=2) + "\n"
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
