from __future__ import annotations

from dataclasses import dataclass, field
import re

from .text import normalize, tokens, unique


MATERIALS = {
    "cotton", "polyester", "nylon", "leather", "wool", "spandex", "silk", "rayon",
    "linen", "denim", "suede", "rubber", "canvas", "cashmere", "viscose", "acrylic",
}
COLORS = {
    "black", "white", "blue", "red", "pink", "green", "brown", "gray", "purple",
    "yellow", "orange", "beige", "tan", "gold", "silver", "navy", "ivory", "khaki",
}
SIZE_WORDS = {"size", "sizing", "wide", "narrow", "small", "medium", "large", "xl", "xxl"}
STYLE_WORDS = {"style", "fit", "sleeve", "neck", "casual", "formal", "vintage", "slim", "regular"}
USE_CASE_WORDS = {"hiking", "running", "gym", "winter", "outdoor", "work", "wedding", "travel", "beach"}
NO_PREFERENCE_RE = re.compile(
    r"(?:no|don t|don\'t)\s+(?:have\s+)?(?:an?\s+)?(?:additional\s+)?preference\s+(?:for|about)\s+([a-z_ ]+)",
    re.I,
)
CLEAR_RE = re.compile(r"(?:don t|don\'t|do not)\s+care\s+(?:about\s+)?([a-z_ ]+?)(?:\s+anymore|\s+now|[.!?,]|$)", re.I)
NEGATIVE_RE = re.compile(r"(?:without|not|no)\s+(?:a\s+|an\s+|any\s+)?([a-z][a-z0-9 -]{1,70})", re.I)


@dataclass(frozen=True)
class Belief:
    attribute: str
    value: str
    confidence: float
    turn: int
    provenance: str
    numeric_value: float | None = None


@dataclass
class DialogueState:
    session_id: str
    profile_tags: tuple[str, ...]
    scenario: str = "unknown"
    category_text: str = ""
    hard: list[Belief] = field(default_factory=list)
    soft: list[Belief] = field(default_factory=list)
    negative: list[Belief] = field(default_factory=list)
    cleared: list[Belief] = field(default_factory=list)
    asked_attributes: set[str] = field(default_factory=set)
    no_preference_attributes: set[str] = field(default_factory=set)
    shown_products: set[str] = field(default_factory=set)
    previous_candidates: tuple[str, ...] = ()
    last_turn: int = 0
    last_trace: dict = field(default_factory=dict)

    @classmethod
    def create(cls, session_id: str, user_profile: dict) -> "DialogueState":
        tags = tuple(normalize(tag) for tag in user_profile.get("preference_tags", []) if normalize(tag))
        return cls(session_id=session_id, profile_tags=tags)

    def ingest(self, message: str, turn: int) -> None:
        """Parse deterministic dialogue evidence and resolve explicit corrections."""
        raw = message.strip()
        lowered = normalize(raw)
        self.last_turn = turn
        if not lowered:
            return

        if "still exploring" in lowered or "just exploring" in lowered or "browse" in lowered:
            self.scenario = "browsing"
        if "key requirement" in lowered or "what matters is" in lowered:
            if self.scenario == "unknown":
                self.scenario = "buying"
        if "actually" in lowered and ("ignore" in lowered or "instead" in lowered or "rather" in lowered):
            self.scenario = "intent_override"
            self._clear_soft_for_override(turn)
        if "outside" in lowered or "not shopping" in lowered:
            self.scenario = "boundary"

        self._learn_category(raw, turn)
        self._apply_no_preference(raw, turn)
        self._apply_explicit_clear(raw, turn)
        self._apply_negative(raw, turn)

        fragments, provenance = self._constraint_fragments(raw)
        for fragment in fragments:
            value = normalize(fragment)
            if value:
                attribute = self.classify_attribute(value)
                numeric_value = self._budget_value(fragment) if attribute == "budget" else None
                self._add(Belief(attribute, value, 0.96, turn, provenance, numeric_value), hard=provenance != "initial_soft")

    def _learn_category(self, message: str, turn: int) -> None:
        if self.category_text:
            return
        match = re.search(r"(?:i['’]?m|i am)\s+looking\s+for\s+(.+?)(?:\s+but\s+|\.\s*|$)", message, re.I)
        if not match:
            return
        candidate = normalize(match.group(1))
        candidate = re.sub(r"\b(?:a key requirement is|key requirement)\b.*", "", candidate).strip()
        if candidate:
            self.category_text = candidate

    def _apply_no_preference(self, message: str, turn: int) -> None:
        for match in NO_PREFERENCE_RE.finditer(message):
            attribute = self._normal_attribute(match.group(1))
            self.no_preference_attributes.add(attribute)
            self._clear_attribute(attribute, turn, "no_preference")
            if attribute == "other" and self.scenario == "browsing" and not self.hard:
                self.scenario = "boundary"

    def _apply_explicit_clear(self, message: str, turn: int) -> None:
        for match in CLEAR_RE.finditer(message):
            attribute = self._normal_attribute(match.group(1))
            self._clear_attribute(attribute, turn, "explicit_clear")

    def _apply_negative(self, message: str, turn: int) -> None:
        lowered = normalize(message)
        if "not quite right" in lowered or "no preference" in lowered or "no additional preference" in lowered:
            return
        for match in NEGATIVE_RE.finditer(message):
            value = normalize(match.group(1))
            if len(tokens(value)) < 1 or value in {"right", "preference", "additional preference"}:
                continue
            belief = Belief(self.classify_attribute(value), value, 0.9, turn, "negative")
            if not any(item.value == belief.value for item in self.negative):
                self.negative.append(belief)

    def _constraint_fragments(self, message: str) -> tuple[list[str], str]:
        explicit = re.search(
            r"(?:key\s+requirement\s+is|what\s+matters\s+is|what\s+i\s+need\s+is|requirement\s+is)\s*:\s*(.+)$",
            message,
            re.I,
        )
        if explicit:
            return self._split_fragments(explicit.group(1)), "explicit"

        looking = re.search(r"(?:i['’]?m|i am)\s+looking\s+for\s+.+?\.\s*(.+)$", message, re.I)
        if looking and "still exploring" not in looking.group(1).lower() and "key requirement" not in looking.group(1).lower():
            remainder = looking.group(1).strip()
            if remainder:
                return self._split_fragments(remainder), "initial_soft"
        return [], "none"

    @staticmethod
    def _split_fragments(value: str) -> list[str]:
        return [fragment.strip(" .") for fragment in re.split(r"\s*;\s*", value) if normalize(fragment)]

    @staticmethod
    def _budget_value(value: str) -> float | None:
        match = re.search(r"(?:\$\s*)?(\d+(?:\.\d{1,2})?)", value)
        return float(match.group(1)) if match else None

    def _add(self, belief: Belief, *, hard: bool) -> None:
        target = self.hard if hard else self.soft
        if belief.attribute not in {"feature", "other"}:
            for item in list(self.hard) + list(self.soft):
                if item.attribute == belief.attribute and item.value != belief.value:
                    self._remove(item, belief.turn, "conflicting_preference")
        if any(item.value == belief.value and item.attribute == belief.attribute for item in target):
            return
        target.append(belief)

    def _remove(self, belief: Belief, turn: int, reason: str) -> None:
        for collection in (self.hard, self.soft, self.negative):
            if belief in collection:
                collection.remove(belief)
            self.cleared.append(Belief(belief.attribute, belief.value, belief.confidence, turn, reason, belief.numeric_value))

    def _clear_attribute(self, attribute: str, turn: int, reason: str) -> None:
        for collection in (self.hard, self.soft, self.negative):
            for belief in list(collection):
                if belief.attribute == attribute:
                    self._remove(belief, turn, reason)

    def _clear_soft_for_override(self, turn: int) -> None:
        for belief in list(self.soft):
            self._remove(belief, turn, "override")

    @staticmethod
    def _normal_attribute(value: str) -> str:
        lowered = normalize(value)
        return lowered if lowered in {"category", "material", "color", "size", "style", "brand", "budget", "feature", "use case", "other"} else "other"

    @staticmethod
    def classify_attribute(value: str) -> str:
        values = set(tokens(value))
        if values & MATERIALS:
            return "material"
        if values & COLORS or "color" in values:
            return "color"
        if "budget" in values or "$" in value or any(token.isdigit() for token in values):
            return "budget"
        if values & SIZE_WORDS:
            return "size"
        if values & USE_CASE_WORDS:
            return "use_case"
        if values & STYLE_WORDS or "department" in values:
            return "style"
        if "brand" in values or "manufacturer" in values or "store" in values:
            return "brand"
        return "feature"

    def query_terms(self) -> list[str]:
        return unique([
            *tokens(self.category_text),
            *(token for belief in self.hard for token in tokens(belief.value)),
            *(token for belief in self.soft for token in tokens(belief.value)),
        ])

    def mark_shown(self, product_ids: list[str]) -> None:
        self.shown_products.update(product_ids)
        self.previous_candidates = tuple(product_ids)

    def retrieval_signature(self) -> tuple:
        """State elements that can change retrieval or a clarification decision."""
        return (
            self.scenario,
            self.category_text,
            tuple((item.attribute, item.value, item.numeric_value) for item in self.hard),
            tuple((item.attribute, item.value, item.numeric_value) for item in self.soft),
            tuple((item.attribute, item.value, item.numeric_value) for item in self.negative),
            tuple(sorted(self.asked_attributes)),
            tuple(sorted(self.no_preference_attributes)),
            self.profile_tags,
        )
