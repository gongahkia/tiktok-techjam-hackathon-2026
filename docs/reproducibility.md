# Reproduce FacetFlow

FacetFlow runs locally with Python 3.10–3.14, SQLite FTS5, and no runtime third-party package, credential, GPU, network call, model download, or vector database.

## Clean-machine workflow

```bash
git clone <your-public-repository-url>
cd tiktok-techjam-hackathon-2026
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip build
python -m pip install -e .
```

Download the official `catalog.jsonl.gz` and `SHA256SUMS` from the challenge release, verify the supplied checksum, and place the decompressed catalog at `data/catalog.jsonl`:

```bash
sha256sum -c SHA256SUMS
gzip -dk catalog.jsonl.gz
mv catalog.jsonl data/catalog.jsonl
make verify
```

`make verify` runs warnings-enabled tests, builds the wheel, creates the local SQLite/FTS index, replays the main real-agent demo with explanation output, and runs the supplied official evaluator. It requires the catalog and the public evaluator set already in this repository; agent evaluation itself makes no network request.

## Individual commands

| Goal | Command |
| --- | --- |
| warnings-enabled tests | `make test-warnings` |
| build local index | `make index` |
| official evaluator | `make evaluate` |
| main explained demo | `make demo` |
| all four demo scenarios | `python -m facetflow.demo --scenario all --explain --output reports/demo_sessions.json` |

`FACETFLOW_CACHE_DIR` selects a writable local cache directory. `FACETFLOW_SPARSE_ONLY=1` is the measured production default; setting it to `0` records the documented sparse fallback because no dense artifact is packaged. `Agent.explain(session_id)` is opt-in diagnostic output and is never added to the official `respond` response schema.
