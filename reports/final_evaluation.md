# FacetFlow final evaluation

## Configuration and reproducibility

- Repository base commit: `3407835` (`main` before FacetFlow changes).
- Python: `3.14.7`; runtime dependencies: Python standard library only.
- Catalog: 50,000 rows, SHA-256 `da979b05a68af864cb0dcf9ee6a81c010c7e66a57978ad286c7a2e005fc69a67`.
- Final cache schema: `facetflow-catalog-v3`; 215,601,152 bytes in the clean runtime profile.
- Final command (run three times): `FACETFLOW_USE_OPENAI=0 FACETFLOW_SPARSE_ONLY=1 FACETFLOW_CACHE_DIR=/tmp/facetflow-final-normalized-v3-20260831 python3 -m evaluator.local_evaluator --catalog data/catalog.jsonl --dataset data/public_set.jsonl --output reports/final_evaluation_runN.json`.

The three official outputs are byte-identical: SHA-256 `92036d26b0e13e7a7d51b1423fdc85022c516965bcf7f0e79308d09d88891ff9`. This establishes deterministic evaluator behavior for identical catalog, state, and input.

## Overall metrics

| Configuration | HitRate@10 | MRR | MTTC | Efficiency | Technical score |
| --- | ---: | ---: | ---: | ---: | ---: |
| Reproduced weak BM25 baseline | 0.125000 | 0.068034 | 9.810000 | 0.119000 | 0.106710 |
| Final FacetFlow offline sparse configuration | 0.530000 | 0.325290 | 6.200000 | 0.480000 | 0.458587 |
| Difference | +0.405000 | +0.257256 | -3.610000 | +0.361000 | +0.351877 |

The final configuration exceeds every mandatory public benchmark: overall technical score, HitRate@10, MRR, and browsing HitRate@10.

## Scenario metrics

| Scenario | Baseline HitRate@10 | Final HitRate@10 | Baseline MRR | Final MRR | Baseline MTTC | Final MTTC |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Buying | 0.237500 | 0.625000 | 0.126508 | 0.389826 | 8.625000 | 5.112500 |
| Browsing | 0.025000 | 0.575000 | 0.004514 | 0.358070 | 10.750000 | 5.812500 |
| Intent override | 0.133333 | 0.333333 | 0.104167 | 0.174206 | 10.066667 | 8.533333 |
| Boundary | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 11.000000 | 11.000000 |

Buying and override behavior improve materially over baseline; no material regression relative to the baseline is present. Browsing improves by 0.55 HitRate@10, exceeding the aspirational 0.15 target.

## Runtime and offline behavior

`python3 scripts/benchmark_runtime.py --catalog data/catalog.jsonl --cache-dir /tmp/facetflow-runtime-clean-v3-20260831 --output reports/runtime_profile.json --repetitions 4` measured a clean-cache agent initialization of 15.674744 seconds, 405.730037 ms median response latency, 442.258690 ms p95, 455.960979 ms maximum across 40 representative two-turn responses, 96,060 KiB agent-process peak RSS, and zero network calls or reported tokens.

The complete official evaluator used 99.11s / 226,644 KiB on the clean-cache first run and 84.74–85.58s / 225,676–225,764 KiB on warm-cache repeats. The evaluator itself separately holds the full catalog, so its RSS is not the agent-only RSS. Per-query work is capped at a 300-item FTS candidate set; it never performs a full in-memory catalog scan.

## Ablations and decisions

| Experiment | Technical score | Decision |
| --- | ---: | --- |
| Weak stateless BM25 baseline | 0.106710 | Reference. |
| Initial stateful sparse core (`reports/experiment_sparse_stateful_v1.json`) | 0.478512 | Demonstrated the value of state, one clarification, and constraint reranking. |
| Final robustness reconciliation (`reports/experiment_robustness_reconciliation_v2.json`) | 0.458587 | Retained despite a 0.019925 public-score reduction: it adds tested decimal-budget handling, common fashion typo normalization, explicit boundary routing, and an explicit sparse-only flag. |
| Dense retrieval | Not run | Rejected as unproven: no local CPU model or artifact has shown enough value to justify an offline submission dependency. |

## Limits and next best experiment

The final [error analysis](error_analysis.md) identifies exact-product boundary sessions as underdetermined after a user supplies no preference. Its largest non-boundary bucket is candidates retrieved below Top-10, not candidate generation. The next best stretch experiment is therefore a held-out, deterministic reranker ablation using only catalog-derived field coverage and hard negatives—not public-message branches or target IDs. A semantic candidate generator is lower priority because only a small candidate-generation bucket remains.

No paid API calls were made; estimated API cost is USD 0.00. No network, API key, model cache, external vector database, or external service is required by the final runtime path.
