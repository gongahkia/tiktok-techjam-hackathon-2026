<p align="center">
<b>FacetFlow</b>
<br>
<em>Offline conversational shopping that keeps changing preferences grounded in a fixed catalogue</em>
<br><br>
<a title="Last Commit" target="_blank" href="https://github.com/gongahkia/tiktok-techjam-hackathon-2026/commits/main"><img src="https://img.shields.io/github/last-commit/gongahkia/tiktok-techjam-hackathon-2026.svg?style=flat-square&color=FF9900"></a>
<a title="GitHub Commits" target="_blank" href="https://github.com/gongahkia/tiktok-techjam-hackathon-2026/commits/main"><img src="https://img.shields.io/github/commit-activity/m/gongahkia/tiktok-techjam-hackathon-2026.svg?style=flat-square"></a>
<a title="Code Size" target="_blank" href="https://github.com/gongahkia/tiktok-techjam-hackathon-2026"><img src="https://img.shields.io/github/languages/code-size/gongahkia/tiktok-techjam-hackathon-2026.svg?style=flat-square&color=yellow"></a>
<a title="Repository Size" target="_blank" href="https://github.com/gongahkia/tiktok-techjam-hackathon-2026"><img src="https://img.shields.io/github/repo-size/gongahkia/tiktok-techjam-hackathon-2026.svg?style=flat-square&color=blueviolet"></a>
<br>
<a title="Python" target="_blank" href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.10%E2%80%933.14-3776AB?style=flat-square"></a>
<a title="SQLite FTS5" target="_blank" href="https://www.sqlite.org/fts5.html"><img src="https://img.shields.io/badge/retrieval-SQLite%20FTS5-003B57?style=flat-square"></a>
<a title="Offline Runtime" target="_blank" href="docs/architecture.md"><img src="https://img.shields.io/badge/runtime-offline-22C55E?style=flat-square"></a>
</p>

<p align="center">
<b>README</b>
| <a href="docs/architecture.md">Architecture</a>
| <a href="docs/competition_specification.md">Competition Specification</a>
| <a href="DATA_ATTRIBUTION.md">Data Attribution</a>
</p>

---

## Table of Contents

* [💡 Introduction](#-introduction)
* [🔮 Features](#-features)
* [👥 Team Members](#-team-members)
* [🏗️ Architecture and Ecosystem](#️-architecture-and-ecosystem)
* [📊 Public Evaluation](#-public-evaluation)
* [🚀 Setup](#-setup)
  * [Install](#install)
  * [Run](#run)
  * [Verification](#verification)
* [🛠️ Development Guide](#️-development-guide)
* [⚠️ Limitations](#️-limitations)

---

## 💡 Introduction

FacetFlow is a fully offline, stateful shopping copilot for the TikTok TechJam 2026 Track 4 catalogue. It preserves the preferences that matter across turns—requirements, corrections, and exclusions—then returns only grounded catalogue recommendations.

The runtime is deterministic Python and SQLite FTS5. It uses no API key, network service, model download, hosted vector database, or generative model.

## 🔮 Features

* Conversational preference memory
  * Retains explicit requirements across turns
  * Replaces stale preferences after corrections
  * Applies exclusions before recommendations are returned
* Grounded product retrieval
  * Searches the fixed catalogue with SQLite FTS5
  * Verifies material, colour, budget, and negative constraints
  * Uses stable `parent_asin` tie-breaking
* Shopping-aware interaction
  * Separates browsing from buying intent
  * Asks at most one focused clarification for genuinely broad requests
  * Keeps explainability outside the official response contract
* Offline reproducibility
  * No runtime third-party dependency
  * No network requests or credentials
  * Local evaluator and deterministic tests

## 👥 Team Members

<table>
  <tbody>
    <tr>
      <td align="center">
        <a href="https://github.com/gongahkia">
          <img src="https://avatars.githubusercontent.com/u/117062305?v=4" width="100" alt="gongahkia"/>
          <br />
          <sub><b>Gabriel Ong</b></sub>
        </a>
      </td>
      <td align="center">
        <a href="https://github.com/kopicplusplus">
          <img src="https://avatars.githubusercontent.com/u/262940233?v=4" width="100" alt="kopicplusplus"/>
          <br />
          <sub><b>Keith Tang</b></sub>
        </a>
      </td>
    </tr>
  </tbody>
</table>

## 🏗️ Architecture and Ecosystem

| Component | Description | Entry point |
| --- | --- | --- |
| Competition adapter | Implements the required `Agent` interface | [`starter/agent.py`](starter/agent.py) |
| Dialogue state | Stores preferences, corrections, exclusions, and context | [`facetflow/state.py`](facetflow/state.py) |
| Retrieval and ranking | Searches and orders catalogue candidates deterministically | [`facetflow/retrieval.py`](facetflow/retrieval.py) |
| Catalogue store | Builds the local fingerprinted SQLite/FTS cache | [`facetflow/catalog.py`](facetflow/catalog.py) |
| Clarification policy | Decides whether one additional question is useful | [`facetflow/policy.py`](facetflow/policy.py) |
| Local evaluator | Replays the supplied public sessions | [`evaluator/local_evaluator.py`](evaluator/local_evaluator.py) |

```mermaid
flowchart LR
    U[User message] --> P[Preference and intent parser]
    P --> S[Structured session state]
    S --> R[SQLite FTS5 retrieval]
    R --> V[Constraint verification]
    V --> K[Deterministic reranking]
    K --> Q[Clarification policy]
    Q --> O[Grounded recommendations]
```

Read the component-level [architecture guide](docs/architecture.md) for the runtime boundary and state semantics.

## 📊 Public Evaluation

| Metric | Starter baseline | FacetFlow |
| --- | ---: | ---: |
| TechnicalScore | 0.106710 | 0.458587 |
| HitRate@10 | 0.125000 | 0.530000 |
| MRR | 0.068034 | 0.325290 |
| Browsing HitRate@10 | 0.025000 | 0.575000 |

These are public evaluator results. Private-evaluator performance is unknown.

## 🚀 Setup

FacetFlow requires Python 3.10–3.14, SQLite FTS5, and the official 50,000-product catalogue. No environment variable or runtime credential is required.

### Install

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

### Run

Download `catalog.jsonl.gz` and `SHA256SUMS` from the challenge release, then verify and unpack the catalogue:

```bash
sha256sum -c SHA256SUMS
gzip -dk catalog.jsonl.gz
mv catalog.jsonl data/catalog.jsonl
make demo
```

For the full four-scenario terminal demo:

```bash
FACETFLOW_SPARSE_ONLY=1 \
  python3 -m facetflow.demo --scenario all --explain --format terminal \
  --catalog data/catalog.jsonl --cache-dir .facetflow_cache
```

The first run builds an ignored SQLite/FTS cache in `.facetflow_cache`. Subsequent runs reuse the cache when its catalogue fingerprint matches.

### Verification

```bash
make test-warnings
make build
make index
make evaluate
```

`make evaluate` writes a local replay to `reports/repro_evaluation.json`; that generated directory is ignored by Git.

## 🛠️ Development Guide

Read the project in this order:

1. [`Makefile`](Makefile)
2. [`starter/agent.py`](starter/agent.py)
3. [`facetflow/agent.py`](facetflow/agent.py)
4. [`facetflow/retrieval.py`](facetflow/retrieval.py)
5. [`docs/architecture.md`](docs/architecture.md)

The public evaluator contract and competition constraints remain in [`docs/`](docs/). Catalogue provenance is documented in [DATA_ATTRIBUTION.md](DATA_ATTRIBUTION.md).

## ⚠️ Limitations

FacetFlow is lexical-first and operates only on the frozen competition catalogue. It does not provide cross-store search, live pricing, checkout, customer service, or private-evaluator claims. Broad boundary requests can remain underdetermined.
