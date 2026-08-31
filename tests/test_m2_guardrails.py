from __future__ import annotations

import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from facetflow.agent import Agent
from facetflow.catalog import CatalogIndex
from facetflow.retrieval import M1_RERANKER_CONFIG, RerankerConfig, ShadowReranker, SparseRetriever
from facetflow.state import DialogueState
from scripts.m2_run_shadow_eval import validate_manifest

from tests.test_facetflow import PROFILE, catalog_rows


class M2GeneralizationGuardrailTest(unittest.TestCase):
    def _write_catalog(self, root: Path, name: str, rows: list[dict]) -> Path:
        path = root / name
        path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        return path

    def test_catalog_row_order_does_not_change_ranked_ids(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            forward = self._write_catalog(root, "forward.jsonl", catalog_rows())
            reverse = self._write_catalog(root, "reverse.jsonl", list(reversed(catalog_rows())))
            outputs = []
            for catalog_path, cache_name in ((forward, "forward-cache"), (reverse, "reverse-cache")):
                state = DialogueState.create("session", PROFILE)
                state.ingest("I'm looking for Men Shoes. A key requirement is: cotton.", 1)
                index = CatalogIndex(catalog_path, root / cache_name)
                try:
                    result = SparseRetriever(index).retrieve(state, 10)
                finally:
                    index.close()
                outputs.append([item.product.parent_asin for item in result.ranked])
            self.assertEqual(outputs[0], outputs[1])

    def test_agent_path_never_opens_a_network_connection(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            catalog_path = self._write_catalog(root, "catalog.jsonl", catalog_rows())
            with patch.object(socket.socket, "connect", side_effect=AssertionError("network access is prohibited")):
                agent = Agent(catalog_path)
                try:
                    agent.reset("session", PROFILE)
                    response = agent.respond("session", "I'm looking for Men Shoes, but I'm still exploring.", 1, 10)
                finally:
                    agent.close()
            self.assertEqual(response["usage"], {"prompt_tokens": 0, "completion_tokens": 0})
            self.assertTrue(response["recommendations"])

    def test_rank_analysis_decomposition_sums_to_ranked_score(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            catalog_path = self._write_catalog(root, "catalog.jsonl", catalog_rows())
            index = CatalogIndex(catalog_path, root / "cache")
            try:
                state = DialogueState.create("session", PROFILE)
                state.ingest("I'm looking for Men Shoes. A key requirement is: cotton.", 1)
                analysis = ShadowReranker(index).rank_candidates(state, 10)
                self.assertEqual(
                    [item.product.parent_asin for item in analysis.displayed],
                    [item.product.parent_asin for item in SparseRetriever(index).retrieve(state, 10).ranked],
                )
                for item in analysis.scored:
                    self.assertAlmostEqual(item.components["total_score"], item.score)
            finally:
                index.close()

    def test_default_reranker_configuration_is_the_frozen_m1_configuration(self) -> None:
        self.assertEqual(RerankerConfig(), M1_RERANKER_CONFIG)

    def test_locked_shadow_manifest_matches_the_immutable_catalog(self) -> None:
        root = Path(__file__).resolve().parents[1]
        manifest = json.loads((root / "data/m2_shadow_manifest.json").read_text(encoding="utf-8"))
        validate_manifest(manifest, str(root / "data/catalog.jsonl"))


if __name__ == "__main__":
    unittest.main()
