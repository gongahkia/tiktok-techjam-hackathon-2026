# M2 locked shadow evaluation design

## Frozen artifact

- Manifest: `data/m2_shadow_manifest.json`
- Generator: `scripts/m2_generate_shadow_suite.py`
- Generator version: `m2-shadow-generator-v2`
- Seed: `facetflow-m2-shadow-seed-v2-2026-08-31`
- Catalog SHA-256: `da979b05a68af864cb0dcf9ee6a81c010c7e66a57978ad286c7a2e005fc69a67`
- Manifest semantic SHA-256: `df94282b5d21743982f9b4b6d7d9837854ce8ebca383605c5d4ae87d1da5e31a`
- Manifest file SHA-256: `2a308a763454c9dd3de5f37b9ba79e569aeb077c40c70066fe9fbbc900409878`

The manifest was generated before M2 reranker tuning. It must not be regenerated in response to development or holdout results. Any future generator version requires a new milestone and a new manifest filename.

## Split discipline

Cases are grouped by `brand|product_type`, then assigned by a SHA-256 hash of the fixed seed and group key: 60% train, 20% development, and 20% holdout. No target `parent_asin` overlaps across the three splits. Template IDs are also split-specific, so development and holdout expression templates are absent from fitting cases.

| Split | Cases | Fingerprint |
| --- | ---: | --- |
| Train | 685 | `a02e9b283e23f5f3ea2fb8dc8a8e39be0513155f778d8f21fe0b6744aaf6519f` |
| Development | 235 | `dc760ac174d226b4cf80e15cae7a97e30b3b19ce1675c33e39f6f1389bbebf6e` |
| Holdout | 182 | `a4f87100f1d5c7ae78b3c0bdf4ca13d2dbb3ba0d579c732d570fb1daf3062ffb` |

## Families and acceptance logic

| Family | Cases | Evaluation objective |
| --- | ---: | --- |
| Product-anchor retrieval | 180 | Exact target rank from product type, verified attribute, and a catalog-wide distinctive title token. |
| Hard-negative ranking | 138 | Exact target must outrank a same-type item that conflicts with a hard attribute and an explicit negative preference. |
| Buying sessions | 143 | Target rank should narrow from category to hard attribute to distinctive evidence. |
| Browsing sessions | 143 | Top-10 should recover a catalog-derived acceptable set and avoid duplicate product types. |
| Intent overrides | 138 | Replacing a color or material moves ranking to the new target and removes the stale value. |
| Boundary | 180 | Out-of-domain/unspecified state remains contract-safe; no target is invented. |
| Metamorphic | 180 | Equivalent state with reordered constraints preserves the Top-10 and target rank. |

Product-anchor exactness is justified by a title token whose document frequency is one across the entire frozen catalog text, combined with product type and a verified material or color where available. Browsing intentionally uses an acceptable catalog-derived set rather than a single arbitrary target.

## Metrics and limitations

The runner reports exact/acceptable HitRate@10, MRR, candidate recall at 10/20/50/100/300, hard and negative violation rates, override/stale-state success, boundary recommendation rate, metamorphic overlap, browsing diversity, unnecessary questions, ranking movement, deterministic replay, and latency. Deterministic bootstrap confidence intervals are computed for major rate metrics.

The suite evaluates ranker behavior through explicit catalog-derived state specifications; it does not reuse public evaluator messages or labels. This isolates ranking quality from public simulator phrasing, but it is not evidence of private-evaluator performance. Boundary behavior is a conservative no-preference proxy because the official contract permits recommendations when user preference is absent; it does not demonstrate successful rejection of a natural-language impossible request. Likewise, the locked metamorphic cases execute canonical constraint reordering; the listed casing, filler, typo, and plurality transformations describe the intended invariant and remain covered by parser unit tests rather than by this ranker-only runner. These limitations were discovered after the manifest was frozen, so the manifest was not regenerated.
