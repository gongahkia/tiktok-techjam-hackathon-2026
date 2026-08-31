# FacetFlow M2 project north star

## User outcome

FacetFlow helps a shopper narrow a frozen catalog to suitable products through efficient, multi-turn conversation. Its value is better product discovery: broad intent becomes catalog-grounded options, explicit requirements are verified, corrections remove stale preferences, and questions earn their turn cost.

M2 is limited to evidence-backed ranking generalization. It is not a public-evaluator optimization exercise and does not add a model, service, interface, or conversational flourish without improving that user outcome.

## Non-negotiable constraints

- Recommendations remain valid `parent_asin` values from the immutable catalog.
- The default stays deterministic, CPU-only, offline, and free of API keys, network calls, hosted services, and runtime generative models.
- The official response contract and evaluator remain unmodified.
- No production behavior may inspect public sample IDs, targets, labels, evaluator paths, or public-message literals.
- M1 remains an available reference configuration until an M2 candidate passes the locked shadow and public regression gates.

## Retention gate

Before a M2 experiment is retained, record answers in the ledger:

1. Does it help a shopper find a suitable catalog product?
2. Which concrete discovery, constraint, override, boundary, ranking, or turn-efficiency failure does it address?
3. Is it catalog-derived and generalized rather than tied to public messages or targets?
4. Is it deterministic, offline, and API-free?
5. Can its contribution be isolated in an ablation?
6. Can a three-minute demo explain both its product rationale and its technical behavior?
7. Do measured quality, latency, memory, artifact, and maintenance costs justify it?
8. Does it preserve identifier validity, catalog immutability, and the official API contract?
9. Would it still make sense if the public 200 sessions were replaced tomorrow?
10. Does it improve recommendation quality rather than only conversational polish?

Any “no” requires rejection, removal, or an explicitly documented exception approved by stronger evidence.

## M2 acceptance rule

An M2 reranker becomes the default only when it beats M1 by at least 5% relative MRR (or a predeclared, justified alternative) on the locked catalog-derived holdout without regressing HitRate@10 by more than one point, hard/negative constraints, overrides, boundaries, metamorphic consistency, offline behavior, or runtime gates. Otherwise M1 remains the default.

## Shadow-suite structural alternative

The locked v2 shadow development baseline has exact-anchor MRR of 1.0 because its product anchors intentionally include a catalog-wide unique title token; relative MRR improvement is therefore mathematically impossible for that exact family. Before evaluating any M2 candidate, the alternative acceptance gate is:

- exact-anchor HitRate@10 and MRR do not regress;
- browsing acceptable-set recall improves by at least five absolute percentage points, with the deterministic bootstrap 95% interval lower bound above zero;
- hard/negative violation, override/stale-state, boundary, metamorphic, and browsing-diversity metrics do not regress;
- public and runtime gates remain satisfied.

This alternative evaluates the nontrivial ambiguous browsing portion of the frozen suite without weakening the original safety constraints.
