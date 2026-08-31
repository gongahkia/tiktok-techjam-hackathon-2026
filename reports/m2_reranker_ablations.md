# M2 reranker hypothesis and ablation ledger

This ledger was recorded after locking `data/m2_shadow_manifest.json` (v2) and before evaluating an M2 candidate on its development split. It answers all ten retention questions in [the M2 north star](../docs/project_north_star.md), in their numbered order.

## Evaluation discipline

The catalog-derived shadow suite is the development selection signal. Its exact product-anchor family uses catalog-wide unique title terms and has an M1 development MRR ceiling of 1.0; it cannot distinguish rerankers by further MRR improvement. Therefore the predeclared alternative gate in the north star is used: no exact-anchor regression; at least +5.0 percentage points browsing acceptable-set recall; deterministic bootstrap 95% improvement interval entirely above zero; and no regression to constraints, overrides, boundary, metamorphic, diversity, offline, or runtime measures. The selected configuration, if any, is evaluated once on the locked holdout; no holdout result changes a configuration.

Every run uses the immutable catalog, the locked manifest, `FACETFLOW_USE_OPENAI=0`, and `FACETFLOW_SPARSE_ONLY=1`. No public evaluator message, sample ID, target, label, or per-case result is used to choose a weight.

## Required baselines and ablations

| ID | Configuration | Purpose and expected observation | Retention answers (1–9) |
| --- | --- | --- | --- |
| M1 reference (scenario-adaptive weighting disabled) | Built-in `M1_RERANKER_CONFIG` | Establish the default quality/safety/latency reference and the required no-adaptive-weighting ablation. | yes / discovery baseline / catalog-derived / deterministic / ablatable / demoable / measured / contract-safe / replacement-robust / quality-focused |
| candidate-generation-only | `configs/m2/candidate_generation_only.json` | Remove all ranker, diversity, and hard-verifier effects while retaining sparse candidates. A material safety or ranking drop attributes M1 behavior to post-retrieval ranking rather than candidate generation alone. | yes / ranking diagnosis / catalog-derived / deterministic / ablatable / demoable / measured / contract-safe / replacement-robust / quality-focused |
| constraint-verifier-disabled | `configs/m2/constraint_verifier_disabled.json` | Remove hard-match/violation and negative penalties. Any increase in constraint/negative errors rejects removing the verifier. | yes / constraint diagnosis / catalog-derived / deterministic / ablatable / demoable / measured / contract-safe / replacement-robust / quality-focused |
| browsing-diversity-disabled | `configs/m2/browsing_diversity_disabled.json` | Remove the bounded browsing diversity penalty. Lower browsing diversity or acceptable-set recall supports retaining diversity. | yes / browsing discovery diagnosis / catalog-derived / deterministic / ablatable / demoable / measured / contract-safe / replacement-robust / quality-focused |
| learned-reranker absent | not implemented | Establish that a learned model is unnecessary unless a deterministic hypothesis fails. It is excluded because no catalog-only labeled training set exists and it would add runtime/model risk. | no; excluded rather than retained |

## Bounded candidate hypotheses

| ID | Falsifiable hypothesis, change, and expected direction | User/product rationale and failure mode | Complexity, failure condition, and ablation | Retention answers (1–9) |
| --- | --- | --- | --- |
| H1 lexical dampening | Reducing lexical-rank weight from 12 to 6 (`lexical_dampening.json`) may allow catalog field coverage to reorder ambiguous browsing candidates. Expected: browsing acceptable-set recall increases; exact anchors and safety remain unchanged. | A shopper browsing a broad category benefits when explicit catalog fields can outweigh incidental query-token overlap. It addresses lexical dominance among already retrieved candidates. | One constant; fails if browsing recall does not clear the gate or any guardrail regresses. Compared to M1 and candidate-generation-only. | yes / ranking / catalog-derived / deterministic / ablatable / demoable / measured / contract-safe / replacement-robust / quality-focused |
| H2 category emphasis | Raising category coverage from 5 to 8 (`category_emphasis.json`) may prioritize products whose catalog category directly fits broad browse intent. Expected: browsing acceptable-set recall increases without affecting hard constraints. | Category alignment is a catalog-native proxy for product-family relevance when the shopper has not yet supplied many attributes. It addresses broad-intent ranking ambiguity. | One constant; fails under the same alternative gate. Compared to M1 and browsing-diversity-disabled. | yes / discovery ranking / catalog-derived / deterministic / ablatable / demoable / measured / contract-safe / replacement-robust / quality-focused |
| H3 adaptive hard constraints | Apply a predeclared modest hard-match multiplier by generic scenario: buying 1.15, browsing 1.35, override 1.15 (`adaptive_hard_constraints.json`). Expected: explicit requirements exert slightly more influence in multi-turn states while violations remain zero. | A shopper’s stated requirement should remain meaningful after a clarification or correction. It addresses weak ordering among candidates that all survive retrieval. | One small deterministic mapping; fails if it does not clear the gate or harms diversity/overrides/constraints. Compared to M1 and constraint-verifier-disabled. | yes / constraint and override ranking / catalog-derived / deterministic / ablatable / demoable / measured / contract-safe / replacement-robust / quality-focused |

All three candidates are independently reversible configurations, have no new dependencies, require no model or service, and have constant-time scoring overhead. A candidate is not retained solely for public-evaluator movement; it must first satisfy the locked shadow development gate, then the single holdout and public/runtime gates.

## Development results and decision

| Configuration | Exact MRR | Browsing acceptable recall@10 | Negative violation rate | Mean distinct browsing product types | Decision |
| --- | ---: | ---: | ---: | ---: | --- |
| M1 reference | 1.000000 | 0.741935 | 0.000000 | 6.548387 | reference |
| candidate-generation-only | 0.985030 | 0.741935 | 0.064516 | 2.935484 | rejects candidate-only explanation; ranking/verifier matter |
| constraint-verifier-disabled | 0.985030 | 0.677419 | 0.064516 | 6.709677 | rejects verifier removal |
| browsing-diversity-disabled | 1.000000 | 0.774194 | 0.000000 | 3.322581 | rejects: +3.23 points is below +5.0 and diversity regresses |
| H1 lexical dampening | 1.000000 | 0.677419 | 0.000000 | 7.161290 | rejects: browsing recall regresses |
| H2 category emphasis | 1.000000 | 0.741935 | 0.000000 | 6.419355 | rejects: no browsing gain and diversity slightly regresses |
| H3 adaptive hard constraints | 1.000000 | 0.741935 | 0.000000 | 6.548387 | rejects: no browsing gain |

M1 browsing recall's deterministic bootstrap interval is [0.580645, 0.870968]. No candidate achieved the required +0.050000 absolute improvement, so the improvement-interval criterion cannot be met. The only positive movement (diversity-disabled) also violates a non-regression guardrail. No M2 candidate was evaluated on holdout; the unchanged M1 configuration alone proceeded to the locked holdout.

The M1 development family results are anchors 1.000000 MRR, buying 1.000000 MRR, hard-negative 1.000000 MRR, override 1.000000 MRR, metamorphic 1.000000 MRR, and browsing 0.741935 acceptable recall. The corresponding locked-holdout values are anchors/buying/hard-negative/override/metamorphic 1.000000 MRR and browsing 0.695652 acceptable recall. All configurations use the same catalog index and add no artifact or dependency; rejected configurations were development-only, so public metrics and holdout metrics are intentionally absent for them. Shadow-runner latency is reported in each machine-readable result. The final host profile is recorded in the generalization result and is not used to retain a candidate.
