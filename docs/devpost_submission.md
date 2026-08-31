# Devpost submission draft

## Project name

FacetFlow

## One-line description

An offline-first conversational shopping copilot that turns changing preferences into verified, catalog-grounded product recommendations.

## Inspiration and problem

Keyword search struggles when a shopper starts vague, adds requirements over several turns, excludes a material, or changes their mind. The real task is not fluent chat: it is preserving useful shopping memory while returning valid products from a fixed catalog.

## What it does and user journey

FacetFlow broadens an exploratory request into diverse starting options, records explicit requirements as structured preferences, verifies those requirements against catalog fields, and asks one question only when another requirement could change the ranking. When a shopper overrides a preference or adds an exclusion, FacetFlow removes stale state and deterministically recomputes recommendations.

## How it was built

The runtime is deterministic Python and SQLite FTS5. Rule-based language understanding extracts shopping mode, product context, hard/soft/negative preferences, and corrections. A typed dialogue state preserves those preferences. Field-aware sparse retrieval supplies bounded candidates; constraint verification and deterministic reranking order valid catalog `parent_asin` values; a clarification policy weighs ambiguity against turn cost. No runtime LLM, hosted vector database, external product search, credential, or network call is required. Codex assisted repository development but is not a runtime component.

## What is distinctive

FacetFlow separates product truth from conversational wording. It uses specialised deterministic modules, not a swarm of LLM agents: each module has a narrow responsibility that can be inspected, tested, and reproduced offline. Recommendations are always drawn from the frozen catalog, and preference overrides explicitly clear conflicting state.

## Evaluation

Against the supplied weak BM25 baseline, FacetFlow improves TechnicalScore from 0.106710 to 0.458587, HitRate@10 from 0.125000 to 0.530000, MRR from 0.068034 to 0.325290, and browsing HitRate@10 from 0.025000 to 0.575000. Three official output files are byte-identical. M2 then locked a 1,102-case catalog-derived shadow suite, corrected an earlier error diagnosis to 61 ranking-stage misses out of 94, tested three small reranking hypotheses, and retained M1 because none cleared the held-out gate. The exact-target shadow family is deliberately saturated and does not prove perfect real-world generalization; browsing holdout recall is 0.695652 and private performance remains unknown.

## Runtime, cost, and limitations

The measured M1 profile reported 15.67 s clean initialization, 405.73 ms median response latency, 442.26 ms p95, a 205.6 MiB derived index, and zero reported tokens. A later M2 clean-host timing run was slower; its range and host-condition caveat are documented in the M2 report rather than hidden. Runtime API cost is zero. FacetFlow remains lexical-first, boundary requests can be underdetermined, and it does not provide external price comparison or purchasing.

## Challenges and lessons

The difficult part was resisting public-set overfitting. M2 showed that an attractive reranker change is not enough: it must generalize to a locked catalog-derived suite without sacrificing constraints, overrides, diversity, determinism, or operational simplicity.

## Future work

Use a newly locked suite to evaluate broader candidate generation and more natural-language boundary tests. Any future language model should assist interpretation only; it must not invent catalog truth or make runtime offline operation optional.

## Repository and demo

Setup, evaluator, and demo commands are in [reproducibility.md](reproducibility.md). Demo video URL: **[Gabriel/Keib: add public video link]**.

## Team contributions

- Gabriel: **[confirm contribution]**
- Keib: **[confirm contribution]**

Both contributors must replace these placeholders with accurate individual contributions before submission.
