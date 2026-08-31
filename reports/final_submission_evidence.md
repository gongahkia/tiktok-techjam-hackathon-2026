# Final submission evidence

## Candidate identity

The release branch starts at the immutable `facetflow-submission-candidate` tag, commit `6b3879045b6576834db9cd906892710c5397ded4`. It retains the original M3 production code and treats M2, M4, and M5 as rejected engineering evidence rather than shipped functionality.

The concurrent commit `dd3357d` was audited read-only before release preparation. It is a descendant of M3 but postdates the protected tag, deletes `AGENTS.md`, and adds M5 experimental evidence. It is not in this release branch and was not restored, reverted, amended, cherry-picked, or merged.

## Public evaluator evidence

| Metric | Starter baseline | FacetFlow | Absolute change | Multiplicative change |
| --- | ---: | ---: | ---: | ---: |
| TechnicalScore | 0.106710 | 0.458587 | +0.351877 | 4.297507× |
| HitRate@10 | 0.125000 | 0.530000 | +0.405000 | 4.240000× |
| MRR | 0.068034 | 0.325290 | +0.257256 | 4.781286× |
| Browsing HitRate@10 | 0.025000 | 0.575000 | +0.550000 | 23.000000× |

These are public evaluator results. Three separate final-release replays are byte-identical with SHA-256 `92036d26b0e13e7a7d51b1423fdc85022c516965bcf7f0e79308d09d88891ff9`: [run 1](release_public_evaluation_run1.json), [run 2](release_public_evaluation_run2.json), and [run 3](release_public_evaluation_run3.json). Private performance is unknown, and public optimisation does not establish generalisation. See [the detailed M3 evaluation](final_evaluation.md).

## Release boundary

The production package uses no API key, network call, model download, online dependency, or generative model. `starter.Agent` is offline by default and the public evaluator reports zero prompt and completion tokens.

M2 shadow reranker candidates did not clear their locked gate, so the production reranker is unchanged. M4/M5 language-interpreter experiments are not present in this branch. A later live experiment elsewhere made 120 provider invocations for USD 0.1491122; it improved selected development categories but had 10% all-three-run and 23.33% pairwise state-delta stability, so the model-primary path was rejected and its holdout was intentionally untouched. These are development experiment facts, not official evaluator metrics.

## Reproduction and unresolved review

Run [the judge quick start](../docs/submission/judge_quickstart.md) after obtaining the official catalogue. The final checklist lists automated verification and external human actions separately.

No licence file exists in M3 or the inspected upstream tree; the upstream public API reported no detected licence. The correct licence choice requires team or legal confirmation, so no licence text has been added.
