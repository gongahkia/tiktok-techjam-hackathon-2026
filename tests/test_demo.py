from __future__ import annotations

import unittest

from facetflow.demo import SHOWCASE_SCENARIOS, render_terminal


class DemoPresentationTest(unittest.TestCase):
    def test_showcase_has_the_four_judge_facing_scenarios(self) -> None:
        self.assertEqual(
            SHOWCASE_SCENARIOS,
            ("preference_memory", "correction_override", "exclusion_safety", "clarification"),
        )

    def test_terminal_renderer_keeps_real_catalog_ids_visible(self) -> None:
        payload = {
            "scenarios": [{
                "scenario": "clarification",
                "description": "A broad request.",
                "turns": [{
                    "turn": 1,
                    "user": "I am exploring shoes.",
                    "assistant": "Which requirement matters most?",
                    "products": [{"parent_asin": "B000000000", "title": "A catalog shoe", "materials": [], "colors": [], "product_type": "shoes"}],
                    "explain": {
                        "intent": "browsing", "product_type": "shoes", "must_have": [], "excluded": [],
                        "clarification": {"asked": "other", "reason": "one useful question", "expected_gain": 1.0},
                    },
                }],
            }],
        }
        rendered = render_terminal(payload)
        self.assertIn("B000000000", rendered)
        self.assertIn("Intent: browsing", rendered)
        self.assertIn("Clarification: other", rendered)


if __name__ == "__main__":
    unittest.main()
