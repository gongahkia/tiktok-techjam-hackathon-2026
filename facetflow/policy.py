from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import math

from .retrieval import RankedProduct
from .state import DialogueState


@dataclass(frozen=True)
class ClarificationDecision:
    ask_attribute: str | None
    expected_gain: float
    reason: str


class ClarificationPolicy:
    """Deterministic, one-question policy with an explicit turn-cost penalty."""

    def decide(self, state: DialogueState, candidates: tuple[RankedProduct, ...]) -> ClarificationDecision:
        if not candidates:
            return ClarificationDecision("other", 1.0, "no viable lexical candidates")
        if len(state.hard) >= 2:
            return ClarificationDecision(None, 0.0, "two explicit constraints already resolve the main ambiguity")
        if "other" in state.asked_attributes or "other" in state.no_preference_attributes:
            return ClarificationDecision(None, 0.0, "a broad requirement question was already exhausted")

        entropy = self._attribute_entropy(candidates)
        top = candidates[0]
        second_score = candidates[1].score if len(candidates) > 1 else 0.0
        score_gap = max(0.0, top.score - second_score)
        gain = entropy + (0.9 if not state.hard else 0.45) - 0.12 * score_gap
        if gain <= 0.30:
            return ClarificationDecision(None, gain, "top results are sufficiently concentrated")
        # `other` is the API-approved catch-all for a single high-value requirement
        # when no known facet is justified over all remaining product types.
        return ClarificationDecision("other", gain, "one remaining requirement has positive expected ranking value")

    @staticmethod
    def _attribute_entropy(candidates: tuple[RankedProduct, ...]) -> float:
        values = [candidate.product.product_type for candidate in candidates[:10]]
        counts = Counter(values)
        total = len(values)
        if total < 2:
            return 0.0
        return -sum((count / total) * math.log2(count / total) for count in counts.values())


def response_message(state: DialogueState, decision: ClarificationDecision, recommendation_count: int) -> str:
    if state.scenario == "boundary":
        return "I can recommend catalog matches, but I need a shopping category or requirement to narrow them safely."
    if decision.ask_attribute == "other":
        if recommendation_count:
            return "I found useful starting options. Which single requirement matters most for this choice?"
        return "Which single requirement matters most for this choice?"
    if state.scenario == "intent_override":
        return "I updated the recommendations to reflect your latest preference."
    return "Here are the closest catalog matches for the preferences you shared."
