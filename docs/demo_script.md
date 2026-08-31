# Three-minute demo script

Word count: 344 words. At 125–135 words per minute, this is approximately 2:33–2:45.

## 0:00–0:20 — problem

Shopping search is harder than matching keywords. A shopper may start vague, add a must-have, rule something out, then change their mind. The recommendation system has to remember the right details without inventing products.

## 0:20–0:45 — thesis

FacetFlow is an offline-first conversational shopping copilot for a fixed catalog. Our thesis is simple: broaden vague intent, verify hard constraints, remember preference changes, and minimise unnecessary turns. It is not a general chatbot or a swarm of language-model agents.

## 0:45–1:15 — architecture

Each specialised module is deterministic code. Rules extract shopping mode and preferences. Structured memory keeps hard, soft, and excluded attributes. SQLite full-text search finds catalog candidates. A constraint verifier removes invalid options, a deterministic ranker orders the rest, and a question policy asks only when one more requirement is likely to matter. The output is always a valid catalog identifier.

## 1:15–2:10 — live main demo

Here is the real agent. I start: “I’m looking for men’s shoes, but I’m still exploring.” FacetFlow returns diverse catalog options and asks for one requirement. Its explain panel shows browsing intent, 300 initial candidates, and why a question has positive value.

Now I say: “Black; leather.” The state records both as must-haves, the verifier checks catalog evidence, and FacetFlow recommends immediately instead of asking again.

Then I change my mind: “Actually, ignore my earlier preference. I need cotton.” Finally I add: “Without leather.” The panel shows leather removed from memory, cotton added, leather excluded, and the list changes using the real offline agent. No product was scripted into the runtime.

## 2:10–2:40 — evidence

Compared with the supplied weak baseline, TechnicalScore rose from 0.106710 to 0.458587; HitRate@10 rose from 0.125 to 0.530; and browsing HitRate rose from 0.025 to 0.575. Three official evaluator outputs were byte-identical, with zero runtime tokens and no network dependency.

## 2:40–3:00 — restraint and close

M2 tested three reranking ideas on a locked catalog-derived suite. None passed the holdout gate, so we kept M1. That is deliberate: reliable shopping discovery matters more than a benchmark-only tweak. FacetFlow is small, inspectable, and ready to help a shopper narrow a changing request into real catalog options.
