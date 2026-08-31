# Submission checklist

This checklist maps the official [submission rules](submission_rules.md) to repository evidence. Items that depend on Devpost or the organizers are intentionally marked manual rather than inferred.

| Requirement | Repository evidence | Status | Verification or owner |
| --- | --- | --- | --- |
| Python `Agent` entry point | `starter/agent.py` | complete | `python -c 'from starter.agent import Agent'` |
| Local helper modules and setup | `facetflow/`, [reproducibility guide](reproducibility.md) | complete | `make verify` |
| Method, model choice, limitations | README, [Devpost draft](devpost_submission.md) | complete | documentation review |
| Latency, token use, API cost disclosure | README and `reports/final_evaluation.md` | complete with timing caveat | M1 public output reports zero tokens; M2 records host timing anomaly |
| Offline/network disclosure | README and architecture | complete | forbidden-network test |
| Catalog attribution | [DATA_ATTRIBUTION.md](../DATA_ATTRIBUTION.md) | complete | confirm release attribution before publishing |
| Public source repository | repository remote | manual | Gabriel or Keib must make the selected repository public |
| Devpost description and form fields | [Devpost draft](devpost_submission.md) | draft complete | Gabriel or Keib must paste and verify live form requirements |
| Three-minute public video | [script](demo_script.md), [storyboard](demo_storyboard.md), [recording checklist](recording_checklist.md) | manual recording | Gabriel or Keib must record, upload, and add URL |
| One multi-turn live demonstration | `python -m facetflow.demo --scenario main --explain` | complete | real-agent replay, fixture in `reports/demo_sessions.json` |
| Team contributions | Devpost placeholders | manual | Gabriel and Keib must confirm individual contributions |
| License | no license file currently present | manual decision | team must select and add a license before public release |
| Devpost field limits and required attachments | no authoritative form export in repository | manual verification | verify directly in Devpost; do not assume limits |

Do not submit catalog data, private data, caches, credentials, or generated indexes. The catalog itself is intentionally absent from the source bundle and must be obtained from the official release.
