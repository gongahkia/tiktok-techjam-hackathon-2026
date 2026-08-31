# Research notes

No web source was needed for the initial offline sparse implementation. The authoritative design inputs were the released competition documents:

- `docs/competition_specification.md` establishes the multi-turn protocol, exact-ID metric, offline allowance, and scenario mix.
- `docs/agent_api_contract.json` defines the allowed question attributes and response schema.
- `docs/evaluation_config.json` defines the metric weights and ten-turn limit.

Implementation decisions influenced by those sources:

| Evidence | Decision |
| --- | --- |
| Exact `parent_asin` scoring with a frozen catalog | Build a local catalog-backed index and never synthesize product identifiers. |
| Turn penalty in MTTC | Ask only one broad, explicit requirement question when candidate ambiguity outweighs its turn cost; still return products on that turn. |
| Browsing, buying, override, boundary scenarios | Represent routing and correction in deterministic typed state instead of replaying raw chat text. |
| Possible offline private scorer | Use Python standard library and SQLite FTS only; no runtime network or model download. |

If a dense retriever is evaluated later, this document must record the primary model documentation, measured quality, cache size, initialization time, memory, latency, and the decision to retain or reject it.
