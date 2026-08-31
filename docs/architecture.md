# FacetFlow architecture

FacetFlow is an offline conversational shopping system. It translates each turn into structured preference state, retrieves only from the fixed competition catalogue, and deterministically ranks valid product identifiers.

```mermaid
flowchart LR
    U[User message] --> P[Preference and intent parser]
    P --> S[Structured session state]
    S --> R[SQLite FTS5 retrieval]
    R --> V[Constraint verification]
    V --> K[Deterministic reranking]
    K --> Q[Clarification policy]
    Q --> O[Grounded recommendations]
```

## Components

| Component | Responsibility |
| --- | --- |
| `starter/agent.py` | Competition-compatible `Agent` entry point. |
| `facetflow/text.py` | Rule-based preference and intent extraction. |
| `facetflow/state.py` | Session memory for preferences, corrections, and exclusions. |
| `facetflow/catalog.py` | Catalogue fingerprinting and local SQLite/FTS cache creation. |
| `facetflow/retrieval.py` | Bounded candidate retrieval, constraint checks, and stable ranking. |
| `facetflow/policy.py` | At-most-one clarification decision for broad requests. |
| `evaluator/local_evaluator.py` | Local replay of the supplied public sessions. |

## Runtime properties

The submitted runtime uses Python and SQLite FTS5 only. It makes no network calls, requires no credential or model download, and returns recommendations drawn from the frozen catalogue. `FACETFLOW_SPARSE_ONLY=1` is the default production setting; generated SQLite caches are local and ignored by Git.

## State semantics

New explicit values replace conflicting values for the same preference. “No preference” and correction phrasing remove stale beliefs rather than creating positive constraints. Exclusions remain negative constraints and are checked before a recommendation list is returned.
