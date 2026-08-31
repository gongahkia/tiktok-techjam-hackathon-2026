# Video narration script

The repository rules do not state a video duration or format. **Human confirmation required:** check the live Devpost form before recording. The primary script is designed for about three minutes; the fallback is under ninety seconds.

## Primary script

### 0:00–0:20 — the problem

Shopping search breaks when a shopper says, “I’m still exploring,” then adds a must-have, excludes a material, or changes their mind. Matching the latest keywords alone loses useful context.

### 0:20–0:45 — the value

FacetFlow is an offline, stateful shopping copilot for a fixed catalogue. It remembers explicit preferences, distinguishes browsing from buying, verifies constraints, and only asks one focused question when it has real value.

### 0:45–1:10 — the architecture

The architecture is deliberately deterministic. Preference and intent interpretation update structured session state. SQLite full-text search retrieves catalogue candidates. Constraint verification and deterministic reranking keep product IDs grounded, and a clarification policy decides whether to ask or recommend.

### 1:10–2:10 — the real demo

Run the four-scenario terminal demo. First, show preference memory: a broad shoe request gains black and leather requirements. Next, show the correction: the shopper replaces the earlier material with cotton. Then show exclusion safety: “without leather” becomes an active exclusion. Finally, replay the broad browsing request and show one useful clarification instead of false certainty. The terminal view exposes state, intent, exclusions, clarification reason, and actual catalogue IDs from the real agent.

### 2:10–2:35 — the evidence

On the public evaluator, FacetFlow raised TechnicalScore from 0.106710 to 0.458587, HitRate@10 from 0.125000 to 0.530000, MRR from 0.068034 to 0.325290, and browsing HitRate@10 from 0.025000 to 0.575000. Three final outputs were byte-identical.

### 2:35–3:00 — close

FacetFlow keeps product truth deterministic and offline. We rejected reranking and model-primary experiments that did not clear their evidence gates. The result is a small, inspectable system that turns a changing shopping conversation into reproducible catalogue recommendations.

## Short fallback script

FacetFlow solves the multi-turn shopping problem that keyword search misses: it remembers requirements, applies corrections and exclusions, distinguishes browsing from buying, and returns only grounded catalogue IDs. Its deterministic Python and SQLite architecture needs no API key or network. On the public evaluator, TechnicalScore rose from 0.106710 to 0.458587 and browsing HitRate@10 from 0.025000 to 0.575000; three final outputs were identical. The terminal demo shows real preference memory, correction, exclusion safety, and clarification behaviour.

## Exact recording command

```bash
FACETFLOW_USE_OPENAI=0 FACETFLOW_SPARSE_ONLY=1 \
  python3 -m facetflow.demo --scenario all --explain --format terminal \
  --catalog data/catalog.jsonl --cache-dir .facetflow_cache
```
