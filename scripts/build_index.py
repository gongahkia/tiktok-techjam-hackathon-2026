#!/usr/bin/env python3
"""Build FacetFlow's local, versioned SQLite/FTS catalog cache."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from facetflow.catalog import CatalogIndex, catalog_fingerprint


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", default="data/catalog.jsonl")
    parser.add_argument("--cache-dir", default=".facetflow_cache")
    args = parser.parse_args()
    index = CatalogIndex(args.catalog, args.cache_dir)
    try:
        print(json.dumps({
            "catalog": str(index.catalog_path),
            "catalog_sha256": catalog_fingerprint(index.catalog_path),
            "index": str(index.path),
            "index_size_bytes": index.size_bytes(),
        }, indent=2))
    finally:
        index.close()


if __name__ == "__main__":
    main()
