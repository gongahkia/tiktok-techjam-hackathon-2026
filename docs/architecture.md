# FacetFlow architecture

FacetFlow is an offline decision-theoretic conversational shopping copilot. It does not use an agent swarm or a generative model at runtime. Ranking and wording are intentionally separate: deterministic retrieval selects valid catalog identifiers, then a short template explains the next action.

```text
catalog JSONL -> normalized versioned SQLite/FTS cache -> sparse candidate generation
user turn -> typed belief state -> constraint verifier + deterministic reranker -> Top-K IDs
                                      |                         |
                                      +-> clarification value --+-> response template
```

`starter/agent.py` is the thin competition adapter. The substantive package is `facetflow/`:

- `catalog.py` fingerprints the immutable source and builds a local fielded FTS cache. The source JSONL remains the raw-value audit record; generated caches are ignored.
- `state.py` records category context, hard/soft/negative beliefs, provenance, confidence, clears, overrides, questions, and seen candidates.
- `retrieval.py` performs title/category-weighted FTS candidate generation, field-aware coverage scoring, explicit material/color/budget checks, deterministic ties, and bounded browsing diversification.
- `policy.py` estimates candidate product-type entropy and applies a turn-cost penalty before asking at most one `other` question. It returns recommendations in the same turn.
- `agent.py` enforces the official response shape and caches unchanged state responses rather than recomputing them.

The default is sparse-only (`FACETFLOW_SPARSE_ONLY=1`). Setting the flag to `0` is an explicit ablation request but currently reports a sparse fallback because no CPU model or vector artifact has yet demonstrated incremental value over this catalog-specific lexical and constraint path, and a model download cannot be a private-evaluation dependency. The cache makes query work bounded to FTS candidates rather than a catalog scan.

## State and correction semantics

Explicit values replace conflicting values for a structured attribute. “I don’t care about X anymore” and “no preference for X” remove matching beliefs rather than adding a positive term. An override clears initial soft preferences while retaining the shopping category and later explicit requirements. Negative constraints stay negative and are checked before a list is filled.

## Determinism and safety

No random seed, network call, API key, external database, or generated language model is used. SQLite returns a bounded candidate set and FacetFlow ties by `parent_asin`. Recommendations originate only from the frozen index, so every returned identifier is catalog-valid. Debug traces are available via `Agent.debug_trace` but are never added to the contract response.
