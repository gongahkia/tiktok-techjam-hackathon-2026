# FacetFlow — offline conversational shopping retrieval

FacetFlow is a competition submission for TikTok TechJam 2026 Track 4. It turns vague shopping intent into a small, verified set of frozen-catalog products, remembers corrections, and asks only one high-value clarification when the current candidate set remains ambiguous.

The thesis is simple: the useful innovation is a deterministic retrieval-and-dialogue policy, not an LLM-agent swarm. Field-aware lexical search broadens a request; typed state and constraint verification narrow it; a turn-aware question policy avoids withholding recommendations when it can already provide useful options.

## Competition constraints

The official evaluator uses a fixed 50,000-product Clothing, Shoes & Jewelry catalog, exact `parent_asin` matching, ten turns maximum, and a public 200-session development set. Private scoring may run offline. See [the official specification](docs/competition_specification.md), [contract](docs/agent_api_contract.json), and [submission rules](docs/submission_rules.md).

FacetFlow's default execution has no network, API key, model download, vector database, or generative model dependency. It uses only the Python standard library and SQLite FTS5.

## Architecture

```text
catalog JSONL -> fingerprinted SQLite FTS cache -> bounded sparse candidates
user message -> typed belief state -> constraint verifier / reranker -> valid Top-K IDs
                                        |                      |
                                        +-> question value ----+-> concise contract response
```

The implementation is described in [docs/architecture.md](docs/architecture.md). `starter/agent.py` remains the official thin entry point; the substantive code is in `facetflow/`.

- Catalog normalization retains the immutable JSONL as its raw audit source and creates an ignored, versioned local cache.
- Dialogue state tracks category context, hard/soft/negative beliefs, profile priors, provenance, clears, overrides, prior questions, and seen products.
- Retrieval uses weighted title/category/features/details FTS, phrase-like coverage boosts, explicit material/color/budget checks, deterministic tie breaks, and controlled browsing diversity.
- The clarification policy estimates product-type entropy and applies a turn-cost penalty. It asks at most one question and supplies recommendations in that same turn.

There is intentionally no dense model in the default configuration. It has not yet earned its initialization time, cache size, memory, or offline distribution cost against the measured sparse core. The cache means individual queries do not scan the 50,000-row catalog.

## Setup

Python 3.10–3.14 is supported; the measured environment used Python 3.14.7. There are no runtime third-party dependencies.

```bash
python3 -m unittest discover -v
python3 scripts/build_index.py --catalog data/catalog.jsonl --cache-dir .facetflow_cache
python3 -m evaluator.local_evaluator --catalog data/catalog.jsonl --dataset data/public_set.jsonl --output results.json
```

Download `catalog.jsonl.gz` and `SHA256SUMS` from the challenge release, verify the release checksum, then decompress it to the ignored local path:

```bash
sha256sum -c SHA256SUMS
gzip -dk catalog.jsonl.gz
mv catalog.jsonl data/catalog.jsonl
```

For an auditable measurement with runtime metadata:

```bash
python3 scripts/profile_catalog.py
python3 scripts/run_experiment.py \
  --experiment-id sparse-stateful-bounded-v1 \
  --output reports/experiment_sparse_stateful_v1.json
python3 scripts/analyze_errors.py \
  --result reports/experiment_sparse_stateful_v1.json
```

`FACETFLOW_CACHE_DIR` can point the derived index at a writable local cache. `FACETFLOW_SPARSE_ONLY=1` selects the measured default; `0` currently records an explicit sparse fallback because no dense artifact is packaged. `FACETFLOW_USE_OPENAI=0` is compatible with the default path; FacetFlow does not inspect an API key or make an API call.

## Measured public results

The reproduced unmodified starter baseline is recorded in [reports/baseline_metrics.json](reports/baseline_metrics.json). The final three-run evidence is in [reports/final_evaluation.md](reports/final_evaluation.md) and the exact official outputs are `reports/final_evaluation_run{1,2,3}.json`.

| Configuration | HitRate@10 | MRR | MTTC | Technical score |
| --- | ---: | ---: | ---: | ---: |
| Official weak BM25 baseline | 0.125000 | 0.068034 | 9.810000 | 0.106710 |
| FacetFlow final offline configuration | 0.530000 | 0.325290 | 6.200000 | 0.458587 |
| Initial stateful sparse experiment (not final) | 0.550000 | 0.347373 | 6.035000 | 0.478512 |

| Scenario | Baseline HitRate@10 | FacetFlow final HitRate@10 |
| --- | ---: | ---: |
| Buying | 0.237500 | 0.625000 |
| Browsing | 0.025000 | 0.575000 |
| Intent override | 0.133333 | 0.333333 |
| Boundary | 0.000000 | 0.000000 |

The three final official runs were byte-identical. Clean-cache profiling measured 15.67s agent initialization, 405.73ms median response latency, 442.26ms p95, 93.8 MiB agent RSS, and a 205.6 MiB derived index; the end-to-end official evaluator used 84.74–99.11s and 225,676–226,644 KiB RSS. Zero tokens were reported. Full ablation and repeated-final-run evidence is in the final evaluation report.

## M2 generalization audit

M2 keeps the M1 reranker as the default. It adds score-level inspection and a catalog-only, split shadow suite to test small ranking changes without fitting public evaluator messages or labels. Three predeclared candidates—lexical dampening, category emphasis, and adaptive hard-constraint emphasis—did not clear the locked development gate, so none was promoted. The selected unchanged M1 configuration scored exact HitRate@10/MRR of 1.000000/1.000000 and browsing acceptable recall@10 of 0.695652 on the one-time 182-case shadow holdout. See [the generalization result](reports/m2_generalization_results.md), [the ablation ledger](reports/m2_reranker_ablations.md), [the locked-suite design](reports/m2_shadow_eval_design.md), and [the decision record](docs/adr/0002-m2-reranker-decision.md).

Reproduce the shadow checks with:

```bash
FACETFLOW_USE_OPENAI=0 FACETFLOW_SPARSE_ONLY=1 \
  python3 scripts/m2_run_shadow_eval.py \
  --manifest data/m2_shadow_manifest.json --catalog data/catalog.jsonl \
  --split development --output reports/m2_shadow_m1_development.json
```

## A compact multi-turn example

1. Customer: “I’m looking for men’s shoes, but I’m still exploring.”
2. FacetFlow: returns diverse catalog-grounded starting options and asks: “Which single requirement matters most for this choice?”
3. Customer: “For that, what matters is: black; leather.”
4. FacetFlow: records both hard beliefs, verifies them against catalog text/facets, stops asking, and returns the deterministic best matching IDs.
5. Customer: “Actually, ignore my earlier preference. What I need is: cotton.”
6. FacetFlow: clears the initial soft preference, retains category context, and ranks from the updated belief state rather than replaying stale chat text.

## Limitations and next work

Boundary sessions with no preference remain underdetermined under exact-product scoring. The present system is lexical-first and small typo/variant normalization is intentionally limited. The M2 audit found most public misses are ranking-stage but did not justify any tested reranker change; future work needs a newly locked catalog-only suite before testing a different candidate-generation or ranking approach.

No paid API calls have been made. Optional online development tooling is not implemented, so there is no API cost.

## Demo and Devpost notes

For a three-minute demo, show the belief-state trace across the example above, contrast it with stateless retrieval, then display the public metric table and offline command. The accompanying Devpost material should disclose the frozen-data scope, zero runtime API cost, cache build step, benchmark command, and the boundary limitation rather than claiming private-set performance.
