# ADR 0001: use a versioned SQLite FTS sparse core

## Status

Accepted.

## Context

The catalog has 50,000 text-heavy products, private evaluation may have no network, and the score penalizes delayed conversion. A retrieved product must be an exact catalog identifier.

## Decision

Use a local, versioned SQLite FTS5 index with field weights, then apply Python constraint verification and deterministic reranking over a bounded candidate pool. Fingerprint the catalog and schema version in the cache filename. Keep the index out of Git.

## Consequences

The default path is reproducible, inspectable, and has no model or network dependency. It has a build cost and a cache artifact, both measured and documented. A dense retriever remains an optional ablation rather than a mandatory component.
