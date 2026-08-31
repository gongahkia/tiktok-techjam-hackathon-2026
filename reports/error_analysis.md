# Public evaluator error analysis

Source result: `reports/final_evaluation_run1.json`. This report classifies only the 94 missed public sessions; it does not alter the evaluator or agent.

## Primary buckets

| Bucket | Misses |
| --- | ---: |
| reranking: target retrieved below Top-10 | 80 |
| boundary: no preference supplied | 10 |
| candidate generation: target outside bounded lexical pool | 4 |

## Misses by scenario and public difficulty label

| Dimension | Count |
| --- | ---: |
| scenario: boundary | 10 |
| scenario: browsing | 34 |
| scenario: buying | 30 |
| scenario: intent_override | 20 |
| difficulty: easy | 30 |
| difficulty: hard | 20 |
| difficulty: medium | 44 |

## Interpretation

Boundary sessions provide no preference after the agent asks, so exact-product recovery from a broad category is intrinsically underdetermined. Reranking misses are candidates that lexical retrieval found but whose deterministic score placed them below the first ten; this is the largest non-boundary bucket and the next ranking-analysis target. Candidate-generation misses are smaller, so a semantic expansion ablation is lower priority. This public breakdown is diagnostic only and must not become per-sample agent logic.

## Reproducible missed-session classifications

| Sample | Scenario | Bucket |
| --- | --- | --- |
| public_0002 | intent_override | reranking: target retrieved below Top-10 |
| public_0004 | intent_override | candidate generation: target outside bounded lexical pool |
| public_0005 | buying | reranking: target retrieved below Top-10 |
| public_0006 | browsing | reranking: target retrieved below Top-10 |
| public_0008 | buying | reranking: target retrieved below Top-10 |
| public_0011 | browsing | reranking: target retrieved below Top-10 |
| public_0012 | browsing | reranking: target retrieved below Top-10 |
| public_0013 | intent_override | reranking: target retrieved below Top-10 |
| public_0016 | browsing | reranking: target retrieved below Top-10 |
| public_0017 | buying | reranking: target retrieved below Top-10 |
| public_0020 | buying | reranking: target retrieved below Top-10 |
| public_0024 | buying | reranking: target retrieved below Top-10 |
| public_0028 | buying | reranking: target retrieved below Top-10 |
| public_0029 | buying | reranking: target retrieved below Top-10 |
| public_0032 | buying | reranking: target retrieved below Top-10 |
| public_0033 | browsing | reranking: target retrieved below Top-10 |
| public_0034 | intent_override | reranking: target retrieved below Top-10 |
| public_0035 | boundary | boundary: no preference supplied |
| public_0040 | browsing | reranking: target retrieved below Top-10 |
| public_0041 | boundary | boundary: no preference supplied |
| public_0042 | buying | reranking: target retrieved below Top-10 |
| public_0045 | buying | reranking: target retrieved below Top-10 |
| public_0046 | intent_override | reranking: target retrieved below Top-10 |
| public_0048 | browsing | reranking: target retrieved below Top-10 |
| public_0050 | boundary | boundary: no preference supplied |
| public_0052 | intent_override | reranking: target retrieved below Top-10 |
| public_0054 | buying | reranking: target retrieved below Top-10 |
| public_0055 | browsing | reranking: target retrieved below Top-10 |
| public_0057 | browsing | reranking: target retrieved below Top-10 |
| public_0058 | buying | reranking: target retrieved below Top-10 |
| public_0064 | intent_override | reranking: target retrieved below Top-10 |
| public_0068 | intent_override | reranking: target retrieved below Top-10 |
| public_0071 | intent_override | reranking: target retrieved below Top-10 |
| public_0075 | browsing | reranking: target retrieved below Top-10 |
| public_0076 | browsing | reranking: target retrieved below Top-10 |
| public_0078 | intent_override | reranking: target retrieved below Top-10 |
| public_0079 | browsing | reranking: target retrieved below Top-10 |
| public_0080 | intent_override | reranking: target retrieved below Top-10 |
| public_0083 | buying | reranking: target retrieved below Top-10 |
| public_0084 | intent_override | reranking: target retrieved below Top-10 |
| public_0085 | browsing | reranking: target retrieved below Top-10 |
| public_0087 | browsing | reranking: target retrieved below Top-10 |
| public_0091 | browsing | reranking: target retrieved below Top-10 |
| public_0092 | browsing | reranking: target retrieved below Top-10 |
| public_0094 | buying | reranking: target retrieved below Top-10 |
| public_0096 | intent_override | reranking: target retrieved below Top-10 |
| public_0098 | browsing | reranking: target retrieved below Top-10 |
| public_0099 | browsing | reranking: target retrieved below Top-10 |
| public_0100 | browsing | reranking: target retrieved below Top-10 |
| public_0101 | buying | reranking: target retrieved below Top-10 |
| public_0104 | boundary | boundary: no preference supplied |
| public_0105 | browsing | reranking: target retrieved below Top-10 |
| public_0106 | buying | reranking: target retrieved below Top-10 |
| public_0109 | buying | reranking: target retrieved below Top-10 |
| public_0112 | boundary | boundary: no preference supplied |
| public_0115 | browsing | reranking: target retrieved below Top-10 |
| public_0120 | browsing | reranking: target retrieved below Top-10 |
| public_0124 | buying | candidate generation: target outside bounded lexical pool |
| public_0126 | browsing | reranking: target retrieved below Top-10 |
| public_0127 | browsing | reranking: target retrieved below Top-10 |
| public_0128 | browsing | reranking: target retrieved below Top-10 |
| public_0130 | intent_override | reranking: target retrieved below Top-10 |
| public_0131 | boundary | boundary: no preference supplied |
| public_0133 | buying | candidate generation: target outside bounded lexical pool |
| public_0136 | buying | reranking: target retrieved below Top-10 |
| public_0137 | browsing | reranking: target retrieved below Top-10 |
| public_0138 | browsing | reranking: target retrieved below Top-10 |
| public_0140 | browsing | reranking: target retrieved below Top-10 |
| public_0142 | intent_override | reranking: target retrieved below Top-10 |
| public_0144 | intent_override | reranking: target retrieved below Top-10 |
| public_0145 | buying | reranking: target retrieved below Top-10 |
| public_0149 | buying | reranking: target retrieved below Top-10 |
| public_0151 | browsing | reranking: target retrieved below Top-10 |
| public_0154 | buying | reranking: target retrieved below Top-10 |
| public_0157 | buying | reranking: target retrieved below Top-10 |
| public_0158 | browsing | reranking: target retrieved below Top-10 |
| public_0165 | buying | reranking: target retrieved below Top-10 |
| public_0169 | boundary | boundary: no preference supplied |
| public_0170 | browsing | reranking: target retrieved below Top-10 |
| public_0172 | browsing | reranking: target retrieved below Top-10 |
| public_0173 | browsing | reranking: target retrieved below Top-10 |
| public_0174 | buying | reranking: target retrieved below Top-10 |
| public_0175 | browsing | reranking: target retrieved below Top-10 |
| public_0177 | intent_override | candidate generation: target outside bounded lexical pool |
| public_0178 | buying | reranking: target retrieved below Top-10 |
| public_0179 | buying | reranking: target retrieved below Top-10 |
| public_0180 | boundary | boundary: no preference supplied |
| public_0183 | intent_override | reranking: target retrieved below Top-10 |
| public_0186 | intent_override | reranking: target retrieved below Top-10 |
| public_0187 | boundary | boundary: no preference supplied |
| public_0190 | buying | reranking: target retrieved below Top-10 |
| public_0192 | boundary | boundary: no preference supplied |
| public_0194 | buying | reranking: target retrieved below Top-10 |
| public_0198 | intent_override | reranking: target retrieved below Top-10 |
