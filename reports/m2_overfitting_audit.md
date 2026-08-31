# M2 overfitting and leakage audit

Scope: production runtime files only (`facetflow/` and `starter/agent.py`). Tests, reports, the official evaluator, and analysis scripts are intentionally excluded because they may legitimately reference public data.

## Static findings

| Check | Matches | Severity | Assessment |
| --- | ---: | --- | --- |
| public_message_or_path | 0 | none | No public message, path, sample ID, label, or intent-card reference in runtime code. |
| catalog_identifier_literal | 0 | none | No hard-coded Amazon parent ASIN literal in runtime code. |
| evaluator_dependency | 0 | none | Production code does not import or call the evaluator. |
| runtime_network | 0 | none | No network-client module reference in runtime code. |
| scenario_id_branch | 0 | none | Production routing derives from user language, not public scenario or difficulty fields. |

## Manual review

- `facetflow/text.py` contains eight small spelling/variant normalizations (`grey`, common color/material/shoe typos, and `tee`/`tshirt`). They are generalized fashion-language normalization applied uniformly to catalog and dialogue text, not public-message branches.
- `facetflow/state.py` contains compact material, color, size, style, and use-case vocabularies. They classify arbitrary user constraints and catalog evidence; they do not name public targets or sample IDs.
- `facetflow/catalog.py` derives facets, product types, and brands solely from the frozen catalog. Retrieval ties by `parent_asin`; FTS fallback also orders by `parent_asin`, so catalog insertion order is not a ranking signal.
- `facetflow/agent.py` reads only `FACETFLOW_CACHE_DIR` and `FACETFLOW_SPARSE_ONLY`; neither selects data, labels, targets, or evaluator-specific behavior.
- `set` values are used for membership/counting only. Ranking order is explicitly sorted by score then `parent_asin`; no random generator is imported by production code.

## Behavioral checks

The M2 guardrail tests add reversed-catalog ordering, forbidden-network, default-configuration, ranking-decomposition, and locked-manifest checks. Existing contract and deterministic-replay tests remain in the base suite. Their results belong in the final M2 verification report.

No prohibited shortcut was found in this source audit. If a later M2 change adds a static match, rerun this script and document the review before retaining it.
