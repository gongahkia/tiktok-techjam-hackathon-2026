# Final submission checklist

The repository documentation does not specify a video duration or final Devpost field requirements. Those items remain human confirmation rather than inferred rules.

## Automatable

- [ ] `make test-warnings`
- [ ] `make build`
- [ ] Install the package in a clean virtual environment
- [ ] Run `make demo` with the real downloaded catalogue
- [ ] Run all four demo scenarios with `--scenario all --explain --format terminal`
- [ ] Run the official evaluator three times from clean processes
- [ ] Confirm byte-identical output fingerprint `92036d…91ff9`
- [ ] Confirm protected public metrics in `reports/final_submission_evidence.md`
- [ ] Run `python3 scripts/release_audit.py --output reports/release_hygiene_audit.json`
- [ ] Scan tracked files for credentials and generated catalogue/cache artefacts
- [ ] Check relative documentation links and `git diff --check`
- [ ] Confirm the release branch has no M4/M5 implementation, online dependency, or API-key requirement

## Human/manual

- [ ] Confirm the licence choice with the team or qualified counsel; no M3 or upstream licence file was found
- [ ] Confirm Gabriel / Gong and Keib contribution descriptions
- [ ] Make the selected repository public
- [ ] Push the final release branch
- [ ] Record the real terminal demo
- [ ] Upload the video and insert the final URL
- [ ] Insert the final repository URL
- [ ] Add screenshots or a project image
- [ ] Complete Devpost fields and verify current field limits
- [ ] Confirm video duration and format rules in the live submission form
- [ ] Perform final claim review and submit before the deadline

## Do not include

Do not submit the downloaded catalogue, private data, generated cache, credentials, API keys, raw experimental provider output, or rejected M4/M5 code. Data attribution is in [DATA_ATTRIBUTION.md](../../DATA_ATTRIBUTION.md).
