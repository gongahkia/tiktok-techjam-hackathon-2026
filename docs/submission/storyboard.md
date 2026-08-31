# Recording storyboard

| Time | Visual | Spoken focus | Capture or evidence |
| --- | --- | --- | --- |
| 0:00–0:20 | Title and one-line problem | Keyword search loses changing preferences | README problem section |
| 0:20–0:45 | Compact Mermaid architecture | Specialised deterministic components, not autonomous agents | `docs/architecture.md` |
| 0:45–1:10 | Terminal: `preference_memory` | State retains black and leather | Live terminal output |
| 1:10–1:35 | Terminal: `correction_override` | Cotton replaces stale preference | Live terminal output |
| 1:35–1:55 | Terminal: `exclusion_safety` | Leather is excluded before ranking | Live terminal output |
| 1:55–2:10 | Terminal: `clarification` | One useful question for a broad browsing request | Live terminal output |
| 2:10–2:35 | Canonical public metric table | Measured improvement and byte-identical runs | `reports/final_submission_evidence.md` |
| 2:35–3:00 | Offline quick-start command | No key, network, or model download | `docs/submission/judge_quickstart.md` |

## Backup terminal capture

Record or save the exact command output before filming:

```bash
FACETFLOW_USE_OPENAI=0 FACETFLOW_SPARSE_ONLY=1 \
  python3 -m facetflow.demo --scenario all --explain --format terminal \
  --catalog data/catalog.jsonl --cache-dir .facetflow_cache \
  --terminal-output reports/submission_demo_terminal.txt
```

The generated text is a backup capture, not a substitute for a real recording. Do not crop out model-free/offline disclosures or replace real IDs with scripted examples.
