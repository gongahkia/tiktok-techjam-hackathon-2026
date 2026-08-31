# ADR 0002: retain the M1 reranker after the M2 generalization audit

- Status: accepted
- Date: 2026-08-31

## Context

M1 uses deterministic sparse candidate generation followed by catalog-field-aware scoring, hard/negative constraint verification, and a bounded browsing-diversity pass. Its public results could not establish whether its explicit reranker generalized or whether changes would merely fit the public development set.

M2 added inspectable score components and configuration injection while keeping the M1 constants as the default. It then locked a catalog-only shadow suite before candidate evaluation and recorded three small, independently ablatable hypotheses: lexical dampening, category emphasis, and scenario-adaptive hard-match weight.

## Decision

Keep `M1_RERANKER_CONFIG` as the production default. Do not add a new default M2 reranker.

None of the three candidates improved development browsing acceptable-set recall by the predeclared five percentage points while preserving all guardrails. The browsing-diversity removal ablation improved recall by only 3.23 points and materially reduced type diversity, demonstrating the required product-quality tradeoff. The unchanged M1 configuration was the only policy evaluated on the locked holdout.

## Consequences

- Production recommendation ordering and the public API retain M1 behavior.
- The extracted configuration and ranking analysis remain as testable offline instrumentation for future, separately locked experiments.
- Future reranker work must use a new immutable manifest and cannot tune against this holdout.
