#!/usr/bin/env python3
"""Audit tracked release files for secrets, forbidden artifacts, size, and docs links."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]
MAX_FILE_BYTES = 5 * 1024 * 1024
SECRET_PATTERNS = {
    "openai_key": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "aws_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
}
FORBIDDEN_NAMES = {"catalog.jsonl", ".env", ".env.local"}
MARKDOWN_LINK = re.compile(r"(?<!!)\[[^]]*\]\(([^)]+)\)")


def tracked_files() -> list[Path]:
    output = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT)
    return [ROOT / item for item in output.decode("utf-8").split("\0") if item]


def link_findings(path: Path) -> list[dict]:
    findings = []
    for match in MARKDOWN_LINK.finditer(path.read_text(encoding="utf-8")):
        target = match.group(1).split("#", 1)[0].strip("<>")
        if not target or "://" in target or target.startswith("mailto:"):
            continue
        resolved = (path.parent / target).resolve()
        if not resolved.exists():
            findings.append({"file": str(path.relative_to(ROOT)), "target": target})
    return findings


def audit() -> dict:
    findings = {"secrets": [], "forbidden_artifacts": [], "oversized_files": [], "broken_links": []}
    for path in tracked_files():
        relative = str(path.relative_to(ROOT))
        if path.name in FORBIDDEN_NAMES or path.suffix in {".sqlite", ".sqlite3", ".pyc"} or "__pycache__" in path.parts:
            findings["forbidden_artifacts"].append(relative)
        if path.stat().st_size > MAX_FILE_BYTES:
            findings["oversized_files"].append({"file": relative, "bytes": path.stat().st_size})
        if path.suffix in {".py", ".md", ".json", ".toml", ".yml", ".yaml"}:
            text = path.read_text(encoding="utf-8", errors="ignore")
            for name, pattern in SECRET_PATTERNS.items():
                if pattern.search(text):
                    findings["secrets"].append({"file": relative, "pattern": name})
        if path.suffix == ".md":
            findings["broken_links"].extend(link_findings(path))
    return {
        "audit_version": "m3-release-audit-v1",
        "tracked_file_count": len(tracked_files()),
        "max_file_bytes": MAX_FILE_BYTES,
        "findings": findings,
        "passed": not any(findings.values()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="reports/m3_hygiene_audit.json")
    args = parser.parse_args()
    result = audit()
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
