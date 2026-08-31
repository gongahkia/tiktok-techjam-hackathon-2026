# M2 generalization results

## Decision

M1 remains FacetFlow's default reranker. The three bounded M2 hypotheses failed the locked catalog-only development gate, so retaining a new production ranking policy would not be evidence-backed. The selected configuration was therefore the unchanged `M1_RERANKER_CONFIG`; it was evaluated once on the holdout. Candidate configurations were not evaluated on holdout and no weight was changed after reading it.

## Leakage and error audit

`scripts/m2_overfitting_audit.py` reports zero production references to public evaluator paths/messages/sample IDs, catalog-ASIN literals, evaluator dependencies, or runtime-network operations. The rank diagnostic corrects the earlier coarse claim that “80 of 94 errors are reranking.” Of 94 public misses, 61 are ranking-stage, 10 filtering-stage, 9 evaluation-timing, 10 boundary, and 4 retrieval-stage; 86 rankable misses have a target-versus-rank-10 mean score margin of -2.684369 (median -1.544733). Candidate recall among all target cases is 0.540000 at 10 and 0.960000 at 300. This is diagnosis, not a fitting target.

## Locked suite

The committed v2 manifest is catalog-only and deterministic: 1,102 cases split 685 train / 235 development / 182 holdout by `brand|product_type`; split target sets do not overlap. It exercises product anchors, progressive buying, browsing acceptable sets, explicit hard negatives, intent overrides, preference-free boundaries, and metamorphic constraint order. Its catalog and semantic manifest fingerprints are recorded in [m2_shadow_eval_design.md](m2_shadow_eval_design.md). The suite evaluates constructed ranking state rather than public simulator messages, so it is a reproducible generalization check, not a private-evaluator performance estimate.

## Development selection

The exact-anchor family deliberately uses a catalog-wide unique title token. Its M1 MRR is 1.0, so relative MRR improvement is impossible. The predeclared alternative gate instead requires no exact regression, at least +0.050000 absolute browsing acceptable-set recall with a positive bootstrap improvement interval, and no regression to safety, override, boundary, metamorphic, diversity, offline, or runtime measures.

| Configuration | Exact MRR | Browsing acceptable recall@10 | Decision |
| --- | ---: | ---: | --- |
| M1 | 1.000000 | 0.741935 | selected reference |
| lexical dampening | 1.000000 | 0.677419 | reject |
| category emphasis | 1.000000 | 0.741935 | reject |
| adaptive hard constraints | 1.000000 | 0.741935 | reject |

The diversity-removal ablation reached 0.774194 browsing recall (+0.032259) but reduced mean distinct browsing types from 6.548387 to 3.322581. It neither meets the threshold nor preserves diversity. Full ablation results are in [m2_reranker_ablations.md](m2_reranker_ablations.md).

## One-time holdout confirmation of selected M1

| Measure | Holdout result |
| --- | ---: |
| Cases / target / exact / browsing | 182 / 152 / 129 / 23 |
| Exact HitRate@10 / MRR | 1.000000 / 1.000000 |
| Browsing acceptable recall@10 (bootstrap 95%) | 0.695652 [0.478261, 0.869565] |
| Candidate recall @10 / @300 | 0.960526 / 0.993421 |
| Hard / negative violation rate | 0.000000 / 0.000000 |
| Override success / stale reappearance | 1.000000 / 0.000000 |
| Metamorphic overlap / target consistency | 1.000000 / 1.000000 |
| Mean browsing diversity / distinct types | 0.608696 / 6.086957 |
| Median / p95 runner latency | 229.075412 ms / 636.956435 ms |

The no-preference boundary proxy still returns products (false-positive recommendation rate 1.0). This is an existing limitation of a contract that permits recommendations absent a preference; it is unchanged by M2 and is not claimed as an improvement.

## Remaining gates

The public-evaluator and clean-profile regression gates are recorded after the final M2 verification run. They do not select a candidate: M1 has already been retained on development.
