# Devpost submission draft

## Project name

FacetFlow

## One-line tagline

An offline, stateful shopping copilot that remembers changing preferences and returns grounded catalogue recommendations.

## Inspiration and problem

Keyword search is brittle when a shopper starts broad, adds a requirement, excludes a material, or changes their mind. The challenge is not generating fluent chat; it is retaining the right shopping state while keeping every recommendation tied to a fixed catalogue.

## What it does

FacetFlow turns a multi-turn request into typed preference state. It retains explicit requirements, clears stale ones after a correction, preserves exclusions, separates browsing from buying intent, and asks one focused clarification only when another answer could change the result. Recommendations are ordered catalogue `parent_asin` values, not generated product claims.

## How it works

FacetFlow separates conversational understanding, preference state, shopping intent, retrieval, ranking and clarification into specialised deterministic components. This gives the benefits of task separation without the latency, instability and orchestration overhead of multiple generative agents. Catalogue-aware parsing feeds structured state; SQLite FTS5 retrieves bounded candidates; field weighting and constraint verification rerank them deterministically; a turn-aware policy decides whether to ask one question or recommend now.

## How it was built

The submitted runtime is Python and SQLite FTS5 with no runtime third-party package, API key, network service, model download, hosted vector database, external browsing, or agent framework. `starter.Agent` remains the competition entry point; the implementation is in `facetflow/`. Codex assisted repository development but is not a runtime component.

## Technical challenges, accomplishments, and learning

The hard part was preventing conversational state from becoming stale or ungrounded. FacetFlow keeps corrections and exclusions explicit, verifies constraints against the frozen catalogue, and retains deterministic retrieval even when language is ambiguous.

Against the supplied weak starter baseline, public TechnicalScore improved from 0.106710 to 0.458587, HitRate@10 from 0.125000 to 0.530000, MRR from 0.068034 to 0.325290, and Browsing HitRate@10 from 0.025000 to 0.575000. Three public evaluator outputs were byte-identical. Hidden-test performance is unknown.

We rejected attractive changes when they did not clear locked evidence: M2 did not replace the production reranker. We also evaluated a model-primary language interpreter through 120 live provider invocations. It improved selected development categories but had 10% all-three-run and 23.33% pairwise state-delta stability, so it was not promoted; the holdout stayed untouched. This is development evidence, not an official or held-out metric.

## Technologies used

- Python 3.10–3.14
- SQLite FTS5
- Standard library data processing and deterministic tests

## What is next

Future work needs a newly locked suite before testing broader candidate generation or language interpretation. It must keep catalogue truth, recommendation ranking, and offline operation deterministic.

## Runtime and limitations

Submitted-runtime API cost is zero. FacetFlow is lexical-first, operates only on the frozen catalogue, and may be underdetermined for preference-free boundary requests. It does not provide cross-store search, live pricing, checkout, customer service, or private-performance claims.

## Repository, video, and team

- Repository URL: **[team: insert final public repository URL]**
- Demo video URL: **[team: insert final public video URL]**
- Project image or screenshots: **[team: add after recording]**

| Contributor | Confirmed scope |
| --- | --- |
| Gabriel / Gong | **[confirm exact implementation and evaluation contribution; repository history uses the `gongahkia` author identity]** |
| Keib | **[confirm product, research, demo, or presentation contribution]** |

These placeholders intentionally require team confirmation before submission.
