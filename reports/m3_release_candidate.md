# FacetFlow M3 release-candidate evidence

## Identity and artifacts

- Branch: `feat/facetflow-m3-submission`
- Candidate revision: local annotated tag `facetflow-submission-candidate`, applied after release verification.
- Immutable M1 reference: `9f3d5d6` (`facetflow-m1`)
- Catalog SHA-256: `da979b05a68af864cb0dcf9ee6a81c010c7e66a57978ad286c7a2e005fc69a67`
- Locked shadow manifest SHA-256: `df94282b5d21743982f9b4b6d7d9837854ce8ebca383605c5d4ae87d1da5e31a`
- Official public output SHA-256: `92036d26b0e13e7a7d51b1423fdc85022c516965bcf7f0e79308d09d88891ff9`
- M3 replay evidence: `reports/m3_public_evaluation_run1.json`, `reports/m3_public_evaluation_run2.json`, and `reports/m3_public_evaluation_run3.json`; their hashes are recorded in `reports/m3_public_fingerprints.txt`.
- Runtime dependencies: Python standard library and SQLite FTS5; build verification uses `build`.

## Reproduction

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip build
python -m pip install -e .
make verify
python -m facetflow.demo --scenario all --explain --output reports/demo_sessions.json
```

The catalog must first be obtained from the official release and placed at `data/catalog.jsonl`; see `docs/reproducibility.md`. Evaluation and demonstration run with `FACETFLOW_USE_OPENAI=0` and `FACETFLOW_SPARSE_ONLY=1` and have no credential or network requirement.

## Quality and determinism

| Check | Result |
| --- | --- |
| Tests | 18 pass, including `-W error::ResourceWarning` |
| Wheel | `python3 -m build --wheel --no-isolation` passes |
| Public metrics | TechnicalScore 0.458587; HitRate@10 0.530000; MRR 0.325290; browsing HitRate@10 0.575000 |
| Public determinism | three outputs byte-identical to the M1 fingerprint above |
| Demo | four deterministic real-agent scenarios in `reports/demo_sessions.json`; main has four turns and shows override plus exclusion |
| Explain mode | opt-in `Agent.explain`; tested not to alter the official response schema or values |
| Hygiene | `scripts/release_audit.py` reports no secret, forbidden artifact, oversized tracked file, or broken relative Markdown link |

## Timing observations

The original M1 profile recorded 15.674744 s cold initialization, 405.730037 ms median response latency, 442.258690 ms p95, and a 215,601,152-byte index. Two M3 clean-cache rechecks on the same Fedora host reported the same index size but a wider range:

| Run | Init | Median | p95 | RSS |
| --- | ---: | ---: | ---: | ---: |
| M3 1 | 21.381028 s | 624.400522 ms | 758.161260 ms | 29,480 KiB |
| M3 2 | 29.241728 s | 884.151495 ms | 1,713.608819 ms | 29,480 KiB |

The host exposed a 13th Gen Intel Core i7-1355U, 15 GiB RAM with only about 3.8 GiB available, and full swap at collection time. Production `SparseRetriever` methods are AST-identical to tagged M1 and final public outputs remain byte-identical, so these results are recorded as host-condition variability, not a selected M3 behavior change. Do not cite only the faster M1 timing without this caveat.

## Limitations and manual submission tasks

- The exact-target shadow family is intentionally saturated; its 1.0/1.0 result is not a real-world generalization claim.
- Browsing shadow holdout recall is 0.695652; private evaluator performance is unknown.
- Boundary requests remain underdetermined and FacetFlow has no external price search, checkout, or purchasing workflow.
- Gabriel and Keib must: make the selected repository public, choose/add a license, confirm individual contributions, record/upload the public video, paste the Devpost draft, and verify live Devpost form requirements and word limits.
