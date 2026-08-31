# Judge quick start

## What you need

- Python 3.10–3.14 with SQLite FTS5
- The official `catalog.jsonl.gz` and `SHA256SUMS` release files

No API key, network service, model download, GPU, or runtime third-party package is required after the catalogue download.

## Run the real offline demo

```bash
git clone <final-repository-url>
cd tiktok-techjam-hackathon-2026
sha256sum -c SHA256SUMS
gzip -dk catalog.jsonl.gz
mv catalog.jsonl data/catalog.jsonl
make demo
```

`make demo` launches the real production `Agent` with `FACETFLOW_USE_OPENAI=0`, prints a terminal-friendly preference-memory session, and closes its catalogue resources. Its first run builds an ignored SQLite/FTS cache in `.facetflow_cache`; later runs reuse the fingerprinted cache. Initialization timing is host-dependent, so no universal timing claim is made.

For the four focused scenarios used in a recording:

```bash
FACETFLOW_USE_OPENAI=0 FACETFLOW_SPARSE_ONLY=1 \
  python3 -m facetflow.demo --scenario all --explain --format terminal \
  --catalog data/catalog.jsonl --cache-dir .facetflow_cache
```

If the catalogue is missing, the demo prints the exact expected path and points to `data/README.md`. The optional `--output reports/demo_sessions.json` writes a JSON recording fixture; it does not alter the official response format.

## Verify the package

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip build
python -m pip install -e .
make test-warnings
make build
make evaluate
```

The evaluator uses `data/public_set.jsonl` and writes `reports/repro_evaluation.json`. It is forced offline, reports zero prompt/completion tokens, and must not be used as a private-score claim.

## Troubleshooting

| Symptom | Action |
| --- | --- |
| `catalog not found` | Download the official archive, verify `SHA256SUMS`, and place it at `data/catalog.jsonl`. |
| SQLite/FTS cache rebuild | Keep `.facetflow_cache` writable; delete only a known corrupted cache file, then rerun. |
| `No module named build` | Install the optional build tool with `python -m pip install build`; it is not required at runtime. |
| Different host timing | Treat timing as host-dependent and compare only equivalent clean-cache conditions. |
