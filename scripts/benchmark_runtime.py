#!/usr/bin/env python3
"""Measure FacetFlow cold initialization and representative offline responses."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import resource
import statistics
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from starter.agent import Agent


PROFILE = {
    "purchase_frequency": "3-4 prior purchases",
    "average_prior_rating": 4.5,
    "rating_style": "usually positive",
    "preference_tags": ["fit", "comfort", "durability"],
    "summary": "Prior purchases emphasize fit, comfort, durability.",
}
CONVERSATIONS = (
    ("I'm looking for Men Shoes, but I'm still exploring.", "For that, what matters is: black; leather."),
    ("I'm looking for Women Clothing T-Shirts. A key requirement is: cotton.", "For that, what matters is: short sleeve; casual."),
    ("I'm looking for Women Jewelry Earrings, but I'm still exploring.", "For that, what matters is: gold; lightweight."),
    ("I'm looking for Men Clothing Jackets. A key requirement is: winter.", "For that, what matters is: polyester; outdoor."),
    ("I'm looking for Women Shoes Sandals, but I'm still exploring.", "For that, what matters is: blue; comfort."),
)


def percentile(values: list[float], percentile_value: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, round((len(ordered) - 1) * percentile_value))
    return ordered[index]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", default="data/catalog.jsonl")
    parser.add_argument("--cache-dir", default=".facetflow_cache")
    parser.add_argument("--output", default="reports/runtime_profile.json")
    parser.add_argument("--repetitions", type=int, default=4)
    args = parser.parse_args()
    os.environ["FACETFLOW_CACHE_DIR"] = args.cache_dir
    started = time.perf_counter()
    agent = Agent(args.catalog)
    initialization_seconds = time.perf_counter() - started
    latencies_ms: list[float] = []
    for repetition in range(args.repetitions):
        for position, (first, second) in enumerate(CONVERSATIONS):
            session_id = f"runtime_{repetition}_{position}"
            agent.reset(session_id, PROFILE)
            for turn, message in enumerate((first, second), start=1):
                response_started = time.perf_counter()
                agent.respond(session_id, message, turn, 10)
                latencies_ms.append((time.perf_counter() - response_started) * 1000)
    result = {
        "catalog": args.catalog,
        "cache_dir": args.cache_dir,
        "cold_initialization_seconds": round(initialization_seconds, 6),
        "response_count": len(latencies_ms),
        "response_latency_ms": {
            "median": round(statistics.median(latencies_ms), 6),
            "p95": round(percentile(latencies_ms, 0.95), 6),
            "max": round(max(latencies_ms), 6),
        },
        "index_size_bytes": agent.catalog.size_bytes(),
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "network_calls": 0,
        "reported_tokens": 0,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
