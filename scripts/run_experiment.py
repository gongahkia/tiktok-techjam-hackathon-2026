#!/usr/bin/env python3
"""Run the unmodified official evaluator with timing metadata."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import platform
import resource
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluator.local_evaluator import catalog_index, evaluate, load_jsonl
from starter.agent import Agent


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", default="data/catalog.jsonl")
    parser.add_argument("--dataset", default="data/public_set.jsonl")
    parser.add_argument("--output", required=True)
    parser.add_argument("--experiment-id", required=True)
    args = parser.parse_args()

    started = time.perf_counter()
    samples = load_jsonl(args.dataset)
    catalog_ids, categories, products = catalog_index(args.catalog)
    agent = Agent(args.catalog)
    result = evaluate(agent, samples, catalog_ids, categories, products)
    result["facetflow_run"] = {
        "experiment_id": args.experiment_id,
        "command": "scripts/run_experiment.py",
        "python": platform.python_version(),
        "wall_seconds": round(time.perf_counter() - started, 6),
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key != "sessions"}, indent=2))


if __name__ == "__main__":
    main()
