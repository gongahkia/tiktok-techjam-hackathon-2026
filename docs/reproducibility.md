# Reproduce FacetFlow

The canonical clean-machine instructions are in [the judge quick start](submission/judge_quickstart.md). They cover catalogue acquisition, the offline demo, tests, the wheel build, and the official evaluator.

FacetFlow's submitted runtime uses Python 3.10–3.14, SQLite FTS5, and no runtime third-party package, credential, model download, or network request. Generated indexes and the catalogue remain untracked local artefacts.
