PYTHON ?= python3
CATALOG ?= data/catalog.jsonl
CACHE_DIR ?= .facetflow_cache

.PHONY: test test-warnings build index evaluate demo verify

test:
	@$(PYTHON) -m unittest discover -v

test-warnings:
	@$(PYTHON) -W error::ResourceWarning -m unittest discover -v

build:
	@$(PYTHON) -m build --wheel --no-isolation

index:
	@$(PYTHON) scripts/build_index.py --catalog $(CATALOG) --cache-dir $(CACHE_DIR)

evaluate:
	@FACETFLOW_SPARSE_ONLY=1 FACETFLOW_CACHE_DIR=$(CACHE_DIR) $(PYTHON) -m evaluator.local_evaluator --catalog $(CATALOG) --dataset data/public_set.jsonl --output reports/repro_evaluation.json

demo:
	@FACETFLOW_SPARSE_ONLY=1 FACETFLOW_CACHE_DIR=$(CACHE_DIR) $(PYTHON) -m facetflow.demo --scenario main --explain --catalog $(CATALOG)

verify: test-warnings build index demo evaluate
