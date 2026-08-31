from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from facetflow.agent import Agent
from facetflow.catalog import CatalogIndex
from facetflow.policy import ClarificationPolicy
from facetflow.retrieval import SparseRetriever
from facetflow.state import DialogueState


PROFILE = {
    "purchase_frequency": "1 prior purchase",
    "average_prior_rating": 4.0,
    "rating_style": "positive",
    "preference_tags": ["comfort"],
    "summary": "Comfort matters.",
}


def catalog_rows() -> list[dict]:
    return [
        {
            "parent_asin": "A",
            "title": "Men black cotton running shoe",
            "features": ["100% cotton upper", "running comfort"],
            "description": ["A lightweight black shoe for running."],
            "price": 40.0,
            "categories": ["Clothing, Shoes & Jewelry", "Men", "Shoes", "Running"],
            "details": {"Color": "Black", "Material": "Cotton", "Brand": "North"},
            "store": "North",
        },
        {
            "parent_asin": "B",
            "title": "Men black leather winter boot",
            "features": ["Leather upper", "winter boot"],
            "description": ["Warm black boot."],
            "price": 90.0,
            "categories": ["Clothing, Shoes & Jewelry", "Men", "Shoes", "Boots"],
            "details": {"Color": "Black", "Material": "Leather", "Brand": "South"},
            "store": "South",
        },
        {
            "parent_asin": "C",
            "title": "Women blue cotton tshirt",
            "features": ["Cotton short sleeve shirt"],
            "description": ["Blue casual tshirt."],
            "price": 20.0,
            "categories": ["Clothing, Shoes & Jewelry", "Women", "Clothing", "T-Shirts"],
            "details": {"Color": "Blue", "Material": "Cotton", "Brand": "East"},
            "store": "East",
        },
    ]


class DialogueStateTest(unittest.TestCase):
    def test_paraphrased_reordered_and_common_typo_terms_are_normalized(self) -> None:
        state = DialogueState.create("session", PROFILE)
        state.ingest("I'm looking for cottn blak shooes, but I'm still exploring.", 1)
        self.assertEqual(state.category_text, "cotton black shoes")
        self.assertEqual(state.scenario, "browsing")

    def test_correction_negation_and_no_preference_remove_stale_beliefs(self) -> None:
        state = DialogueState.create("session", PROFILE)
        state.ingest("I'm looking for shoes. A key requirement is: black.", 1)
        state.ingest("Actually, what I need is: red.", 2)
        self.assertEqual([belief.value for belief in state.hard if belief.attribute == "color"], ["red"])
        state.ingest("I don't care about color anymore.", 3)
        self.assertFalse([belief for belief in state.hard if belief.attribute == "color"])
        state.ingest("I need something without leather.", 4)
        self.assertEqual([belief.value for belief in state.negative], ["leather"])

    def test_override_clears_initial_soft_belief_but_retains_category(self) -> None:
        state = DialogueState.create("session", PROFILE)
        state.ingest("I'm looking for Men Shoes. leather.", 1)
        self.assertEqual([belief.value for belief in state.soft], ["leather"])
        state.ingest("Actually, ignore my earlier preference. What I need is: cotton.", 3)
        self.assertEqual(state.category_text, "men shoes")
        self.assertEqual(state.scenario, "intent_override")
        self.assertFalse(state.soft)
        self.assertEqual([belief.value for belief in state.hard], ["cotton"])

    def test_no_preference_does_not_turn_into_positive_constraint(self) -> None:
        state = DialogueState.create("session", PROFILE)
        state.ingest("I'm looking for shoes. A key requirement is: black.", 1)
        state.ingest("I don't have a preference for color; please use your judgment.", 2)
        self.assertIn("color", state.no_preference_attributes)
        self.assertFalse([belief for belief in state.hard if belief.attribute == "color"])

    def test_broad_no_preference_routes_to_boundary_without_inventing_a_belief(self) -> None:
        state = DialogueState.create("session", PROFILE)
        state.ingest("I'm looking for shoes, but I'm still exploring.", 1)
        state.ingest("I don't have a preference for other; please use your judgment.", 2)
        self.assertEqual(state.scenario, "boundary")
        self.assertFalse(state.hard)

    def test_budget_keeps_decimal_value_for_verification(self) -> None:
        state = DialogueState.create("session", PROFILE)
        state.ingest("I'm looking for shoes. A key requirement is: budget around $27.99.", 1)
        self.assertEqual(state.hard[0].attribute, "budget")
        self.assertEqual(state.hard[0].numeric_value, 27.99)


class FacetFlowIntegrationTest(unittest.TestCase):
    def test_constraint_reranking_and_negative_filter(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            catalog_path = root / "catalog.jsonl"
            catalog_path.write_text("".join(json.dumps(row) + "\n" for row in catalog_rows()), encoding="utf-8")
            index = CatalogIndex(catalog_path, root / "cache")
            state = DialogueState.create("session", PROFILE)
            state.ingest("I'm looking for Men Shoes. A key requirement is: cotton.", 1)
            result = SparseRetriever(index).retrieve(state, 10)
            self.assertEqual(result.ranked[0].product.parent_asin, "A")
            state.ingest("I need something without leather.", 2)
            result = SparseRetriever(index).retrieve(state, 10)
            self.assertNotIn("B", [item.product.parent_asin for item in result.ranked])

    def test_contract_and_identical_fresh_sessions_are_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            catalog_path = root / "catalog.jsonl"
            catalog_path.write_text("".join(json.dumps(row) + "\n" for row in catalog_rows()), encoding="utf-8")
            agent = Agent(catalog_path)
            responses = []
            for session_id in ("one", "two"):
                agent.reset(session_id, PROFILE)
                responses.append(agent.respond(session_id, "I'm looking for Men Shoes. A key requirement is: cotton.", 1, 10))
            self.assertEqual(responses[0], responses[1])
            self.assertEqual(set(responses[0]), {"message", "ask_attribute", "recommendations", "usage"})
            self.assertTrue(all(item["parent_asin"] in {"A", "B", "C"} for item in responses[0]["recommendations"]))

    def test_question_policy_asks_only_when_unresolved(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            catalog_path = root / "catalog.jsonl"
            catalog_path.write_text("".join(json.dumps(row) + "\n" for row in catalog_rows()), encoding="utf-8")
            index = CatalogIndex(catalog_path, root / "cache")
            state = DialogueState.create("session", PROFILE)
            state.ingest("I'm looking for shoes, but I'm still exploring.", 1)
            result = SparseRetriever(index).retrieve(state, 10)
            policy = ClarificationPolicy()
            self.assertEqual(policy.decide(state, result.ranked).ask_attribute, "other")
            state.asked_attributes.add("other")
            self.assertIsNone(policy.decide(state, result.ranked).ask_attribute)


if __name__ == "__main__":
    unittest.main()
