# M2 rank-placement diagnostics

Version: `m2-rank-diagnostics-v1`. Catalog fingerprint: `da979b05a68af864cb0dcf9ee6a81c010c7e66a57978ad286c7a2e005fc69a67`. The script replays the public simulator only for post-hoc analysis; production runtime does not read these records.

## Corrected candidate recall

| Population | R@10 | R@20 | R@50 | R@100 | R@300 |
| --- | ---: | ---: | ---: | ---: | ---: |
| all terminal sessions | 0.540000 | 0.670000 | 0.790000 | 0.865000 | 0.960000 |
| official misses | 0.106383 | 0.308511 | 0.553191 | 0.712766 | 0.914894 |

## Failure and score-margin summary

- official misses: 94; failure types: `{"boundary": 10, "evaluation_timing": 9, "filtering": 10, "ranking": 61, "retrieval": 4}`.
- target-versus-displayed-rank-10 score margin: mean `-2.684369`, median `-1.544733` across 86 rankable misses.
- candidate-rank histogram: `{"101_300": 19, "11_20": 26, "1_10": 108, "21_50": 24, "51_100": 15, "not_retained": 8}`.
- target component lower than displayed rank-10 competitor: `{"hard_match": 1, "hard_violation": 8, "lexical_rank": 61, "negative_penalty": 2, "profile": 25}`. This is descriptive score evidence, not causal attribution.
- clarification outcomes: `{"asked_and_candidate_rank_improved": 92, "asked_without_candidate_rank_improvement": 71, "asked_without_resolved_constraint": 11, "not_asked": 26}`.

The machine-readable companion records every official miss with terminal-turn constraints, candidate/pre-filter/post-filter/final ranks, target and competitor facets, feature contributions, filtering status, clarification path, and failure classification. Aggregate values retain all 200 sessions.
