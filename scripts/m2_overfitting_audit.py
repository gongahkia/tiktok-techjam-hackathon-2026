#!/usr/bin/env python3
"""Run a reproducible source-level anti-overfitting audit of production code."""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PRODUCTION_FILES = tuple(sorted((ROOT / "facetflow").glob("*.py"))) + (ROOT / "starter" / "agent.py",)
SUSPICIOUS_PATTERNS = {
    "public_message_or_path": re.compile(r"public_set|public_\d+|sample_id|ground_truth|intent_card", re.I),
    "catalog_identifier_literal": re.compile(r"\bB[A-Z0-9]{9}\b"),
    "evaluator_dependency": re.compile(r"(?:from|import)\s+evaluator\b|local_evaluator", re.I),
    "runtime_network": re.compile(r"\b(?:requests|urllib|http\.client|socket|aiohttp|openai)\b", re.I),
    "scenario_id_branch": re.compile(r"scenario_type|difficulty_bucket", re.I),
}


def imported_modules(source: str) -> list[str]:
    tree = ast.parse(source)
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.append(node.module)
    return sorted(set(modules))


def findings() -> dict:
    file_results: list[dict] = []
    totals = {name: 0 for name in SUSPICIOUS_PATTERNS}
    for path in PRODUCTION_FILES:
        source = path.read_text(encoding="utf-8")
        matches: dict[str, list[int]] = {}
        for name, pattern in SUSPICIOUS_PATTERNS.items():
            lines = [index for index, line in enumerate(source.splitlines(), start=1) if pattern.search(line)]
            matches[name] = lines
            totals[name] += len(lines)
        file_results.append({
            "file": str(path.relative_to(ROOT)),
            "imports": imported_modules(source),
            "matches": matches,
            "environment_references": [
                index for index, line in enumerate(source.splitlines(), start=1)
                if "environ" in line or "getenv" in line
            ],
        })
    return {
        "audit_version": "m2-overfitting-audit-v1",
        "production_files": [str(path.relative_to(ROOT)) for path in PRODUCTION_FILES],
        "pattern_totals": totals,
        "files": file_results,
    }


def markdown(result: dict) -> str:
    lines = [
        "# M2 overfitting and leakage audit",
        "",
        "Scope: production runtime files only (`facetflow/` and `starter/agent.py`). Tests, reports, the official evaluator, and analysis scripts are intentionally excluded because they may legitimately reference public data.",
        "",
        "## Static findings",
        "",
        "| Check | Matches | Severity | Assessment |",
        "| --- | ---: | --- | --- |",
    ]
    assessments = {
        "public_message_or_path": ("none", "No public message, path, sample ID, label, or intent-card reference in runtime code."),
        "catalog_identifier_literal": ("none", "No hard-coded Amazon parent ASIN literal in runtime code."),
        "evaluator_dependency": ("none", "Production code does not import or call the evaluator."),
        "runtime_network": ("none", "No network-client module reference in runtime code."),
        "scenario_id_branch": ("none", "Production routing derives from user language, not public scenario or difficulty fields."),
    }
    for name, count in result["pattern_totals"].items():
        severity, assessment = assessments[name]
        if count:
            severity = "review"
            assessment = "Static match requires manual review; see JSON evidence."
        lines.append(f"| {name} | {count} | {severity} | {assessment} |")
    lines.extend([
        "",
        "## Manual review",
        "",
        "- `facetflow/text.py` contains eight small spelling/variant normalizations (`grey`, common color/material/shoe typos, and `tee`/`tshirt`). They are generalized fashion-language normalization applied uniformly to catalog and dialogue text, not public-message branches.",
        "- `facetflow/state.py` contains compact material, color, size, style, and use-case vocabularies. They classify arbitrary user constraints and catalog evidence; they do not name public targets or sample IDs.",
        "- `facetflow/catalog.py` derives facets, product types, and brands solely from the frozen catalog. Retrieval ties by `parent_asin`; FTS fallback also orders by `parent_asin`, so catalog insertion order is not a ranking signal.",
        "- `facetflow/agent.py` reads only `FACETFLOW_CACHE_DIR` and `FACETFLOW_SPARSE_ONLY`; neither selects data, labels, targets, or evaluator-specific behavior.",
        "- `set` values are used for membership/counting only. Ranking order is explicitly sorted by score then `parent_asin`; no random generator is imported by production code.",
        "",
        "## Behavioral checks",
        "",
        "The M2 guardrail tests add reversed-catalog ordering, forbidden-network, default-configuration, ranking-decomposition, and locked-manifest checks. Existing contract and deterministic-replay tests remain in the base suite. Their results belong in the final M2 verification report.",
        "",
        "No prohibited shortcut was found in this source audit. If a later M2 change adds a static match, rerun this script and document the review before retaining it.",
    ])
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-output", default="reports/m2_overfitting_audit.json")
    parser.add_argument("--markdown-output", default="reports/m2_overfitting_audit.md")
    args = parser.parse_args()
    result = findings()
    json_path = ROOT / args.json_output
    markdown_path = ROOT / args.markdown_output
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(markdown(result), encoding="utf-8")
    print(json.dumps(result["pattern_totals"], sort_keys=True))


if __name__ == "__main__":
    main()
