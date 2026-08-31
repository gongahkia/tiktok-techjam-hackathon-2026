from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
import math
import re

from .catalog import CatalogIndex, Product
from .state import Belief, COLORS, MATERIALS, DialogueState
from .text import normalize, tokens


PRICE_RE = re.compile(r"(?:\$|budget\s+(?:around|under|below)?\s*)(\d+(?:\.\d{1,2})?)", re.I)


@dataclass(frozen=True)
class RankedProduct:
    product: Product
    score: float
    hard_violations: int
    hard_coverage: float
    lexical_rank: int


@dataclass(frozen=True)
class RankedProductDiagnostic(RankedProduct):
    """Offline score decomposition; never created by the API request path."""

    components: dict[str, object]


@dataclass(frozen=True)
class RetrievalResult:
    ranked: tuple[RankedProduct, ...]
    trace: dict


@dataclass(frozen=True)
class RankingAnalysis:
    """Inspectable ranking stages; used by offline diagnostics, never the API."""

    candidates: tuple[Product, ...]
    scored: tuple[RankedProduct, ...]
    pool: tuple[RankedProduct, ...]
    displayed: tuple[RankedProduct, ...]
    qualified_count: int


@dataclass(frozen=True)
class RerankerConfig:
    """Inspectable deterministic weights; defaults exactly match frozen M1."""

    name: str = "m1"
    lexical_weight: float = 12.0
    category_weight: float = 5.0
    hard_match_weight: float = 18.0
    hard_violation_penalty: float = -24.0
    soft_match_weight: float = 4.0
    negative_violation_penalty: float = -28.0
    profile_token_weight: float = 0.25
    profile_cap: float = 1.5
    diversity_product_type_penalty: float = 1.6
    diversity_brand_penalty: float = 0.35
    enforce_hard_constraints: bool = True
    scenario_hard_match_multiplier: dict[str, float] = field(default_factory=dict)

    def hard_weight_for(self, scenario: str) -> float:
        return self.hard_match_weight * self.scenario_hard_match_multiplier.get(scenario, 1.0)


M1_RERANKER_CONFIG = RerankerConfig()


class ShadowReranker:
    """Configurable, score-inspectable ranker used only by M2 offline evaluation."""

    def __init__(self, catalog: CatalogIndex, config: RerankerConfig | None = None) -> None:
        self.catalog = catalog
        self.config = config or M1_RERANKER_CONFIG

    def retrieve(self, state: DialogueState, top_k: int) -> RetrievalResult:
        if self.config == M1_RERANKER_CONFIG:
            return self._retrieve_frozen_m1(state, top_k)
        terms = state.query_terms()
        candidates, _, displayed, qualified_count = self._rank(state, top_k, detailed=False)
        trace = {
            "retriever": "sparse",
            "query_terms": terms,
            "candidate_count": len(candidates),
            "qualified_count": qualified_count,
            "hard_constraint_count": len(state.hard),
            "negative_constraint_count": len(state.negative),
            "scenario": state.scenario,
            "selected": [
                {
                    "parent_asin": item.product.parent_asin,
                    "score": round(item.score, 6),
                    "hard_violations": item.hard_violations,
                    "hard_coverage": round(item.hard_coverage, 4),
                }
                for item in displayed
            ],
        }
        return RetrievalResult(tuple(displayed), trace)

    def _retrieve_frozen_m1(self, state: DialogueState, top_k: int) -> RetrievalResult:
        """Preserve the measured M1 request path without offline diagnostics."""
        terms = state.query_terms()
        candidates = self.catalog.search(terms, limit=max(300, top_k * 30))
        ranked = [self._score_frozen_m1(candidate, rank, state) for rank, candidate in enumerate(candidates, start=1)]
        qualifying = [candidate for candidate in ranked if candidate.hard_violations == 0]
        pool = qualifying if qualifying else ranked
        pool.sort(key=lambda candidate: (-candidate.score, candidate.product.parent_asin))
        if state.scenario == "browsing" and len(state.hard) < 2:
            displayed = self._diversify_frozen_m1(pool, top_k)
        else:
            displayed = pool[:top_k]
        trace = {
            "retriever": "sparse",
            "query_terms": terms,
            "candidate_count": len(candidates),
            "qualified_count": len(qualifying),
            "hard_constraint_count": len(state.hard),
            "negative_constraint_count": len(state.negative),
            "scenario": state.scenario,
            "selected": [
                {
                    "parent_asin": item.product.parent_asin,
                    "score": round(item.score, 6),
                    "hard_violations": item.hard_violations,
                    "hard_coverage": round(item.hard_coverage, 4),
                }
                for item in displayed
            ],
        }
        return RetrievalResult(tuple(displayed), trace)

    def rank_candidates(self, state: DialogueState, top_k: int, candidate_limit: int | None = None) -> RankingAnalysis:
        """Expose every sparse candidate and score for reproducible offline analysis."""
        candidates, scored, displayed, qualified_count = self._rank(state, top_k, candidate_limit, detailed=True)
        pool = [candidate for candidate in scored if candidate.hard_violations == 0]
        if not pool:
            pool = list(scored)
        pool.sort(key=lambda candidate: (-candidate.score, candidate.product.parent_asin))
        return RankingAnalysis(tuple(candidates), tuple(scored), tuple(pool), tuple(displayed), qualified_count)

    def _rank(
        self,
        state: DialogueState,
        top_k: int,
        candidate_limit: int | None = None,
        *,
        detailed: bool,
    ) -> tuple[list[Product], list[RankedProduct], list[RankedProduct], int]:
        """Share ranking semantics while keeping per-candidate diagnostics offline."""
        limit = candidate_limit if candidate_limit is not None else max(300, top_k * 30)
        candidates = self.catalog.search(state.query_terms(), limit=limit)
        scored = [self._score(candidate, rank, state, detailed=detailed) for rank, candidate in enumerate(candidates, start=1)]
        qualifying = [candidate for candidate in scored if candidate.hard_violations == 0]
        # Do not fill a short list with explicit hard-constraint violations. Soft
        # preferences influence scores only, so this never relaxes a hard rule.
        pool = qualifying if qualifying else scored
        pool.sort(key=lambda candidate: (-candidate.score, candidate.product.parent_asin))
        if state.scenario == "browsing" and len(state.hard) < 2:
            displayed = self._diversify(pool, top_k)
        else:
            displayed = pool[:top_k]
        return candidates, scored, displayed, len(qualifying)

    def _score(self, product: Product, lexical_rank: int, state: DialogueState, *, detailed: bool) -> RankedProduct:
        document_tokens = set(tokens(product.all_text, include_stopwords=True))
        lexical_score = self.config.lexical_weight / math.sqrt(lexical_rank)
        score = lexical_score
        components: dict[str, object] | None = {"lexical_rank_score": lexical_score} if detailed else None
        category_terms = tokens(state.category_text)
        if category_terms:
            category_coverage = sum(term in product.categories or term in product.title for term in category_terms) / len(category_terms)
            category_score = self.config.category_weight * category_coverage
            score += category_score
            if components is not None:
                components["category"] = {"coverage": category_coverage, "score": category_score}
        elif components is not None:
            components["category"] = {"coverage": 0.0, "score": 0.0}

        hard_violations = 0
        coverage_values: list[float] = []
        hard_components: list[dict] = []
        for belief in state.hard:
            coverage, violation = self._constraint_match(product, document_tokens, belief)
            coverage_values.append(coverage)
            match_score = self.config.hard_weight_for(state.scenario) * coverage
            score += match_score
            violation_score = 0.0
            if violation:
                if self.config.enforce_hard_constraints:
                    hard_violations += 1
                violation_score = self.config.hard_violation_penalty
                score += violation_score
            if components is not None:
                hard_components.append({
                    "attribute": belief.attribute,
                    "value": belief.value,
                    "coverage": coverage,
                    "match_score": match_score,
                    "violation": violation,
                    "violation_score": violation_score,
                })
        if components is not None:
            components["hard"] = hard_components
        soft_components: list[dict] = []
        for belief in state.soft:
            coverage, _ = self._constraint_match(product, document_tokens, belief)
            match_score = self.config.soft_match_weight * coverage
            score += match_score
            if components is not None:
                soft_components.append({"attribute": belief.attribute, "value": belief.value, "coverage": coverage, "score": match_score})
        if components is not None:
            components["soft"] = soft_components
        negative_components: list[dict] = []
        for belief in state.negative:
            coverage, _ = self._constraint_match(product, document_tokens, belief)
            penalty = 0.0
            if coverage >= 0.7:
                penalty = self.config.negative_violation_penalty
                score += penalty
                if self.config.enforce_hard_constraints:
                    hard_violations += 1
            if components is not None:
                negative_components.append({"attribute": belief.attribute, "value": belief.value, "coverage": coverage, "penalty": penalty})
        if components is not None:
            components["negative"] = negative_components
        profile_terms = {term for tag in state.profile_tags for term in tokens(tag)}
        profile_score = 0.0
        if profile_terms:
            profile_score = min(self.config.profile_cap, self.config.profile_token_weight * sum(term in document_tokens for term in profile_terms))
            score += profile_score
        if components is not None:
            components["profile_score"] = profile_score
        hard_coverage = sum(coverage_values) / len(coverage_values) if coverage_values else 0.0
        if components is not None:
            components["total_score"] = score
        if components is not None:
            return RankedProductDiagnostic(product, score, hard_violations, hard_coverage, lexical_rank, components)
        return RankedProduct(product, score, hard_violations, hard_coverage, lexical_rank)

    def _score_frozen_m1(self, product: Product, lexical_rank: int, state: DialogueState) -> RankedProduct:
        """The original M1 scoring arithmetic, retained as the default reference."""
        document_tokens = set(tokens(product.all_text, include_stopwords=True))
        score = 12.0 / math.sqrt(lexical_rank)
        category_terms = tokens(state.category_text)
        if category_terms:
            category_coverage = sum(term in product.categories or term in product.title for term in category_terms) / len(category_terms)
            score += 5.0 * category_coverage
        hard_violations = 0
        coverage_values: list[float] = []
        for belief in state.hard:
            coverage, violation = self._constraint_match(product, document_tokens, belief)
            coverage_values.append(coverage)
            score += 18.0 * coverage
            if violation:
                hard_violations += 1
                score -= 24.0
        for belief in state.soft:
            coverage, _ = self._constraint_match(product, document_tokens, belief)
            score += 4.0 * coverage
        for belief in state.negative:
            coverage, _ = self._constraint_match(product, document_tokens, belief)
            if coverage >= 0.7:
                score -= 28.0
                hard_violations += 1
        profile_terms = {term for tag in state.profile_tags for term in tokens(tag)}
        if profile_terms:
            score += min(1.5, 0.25 * sum(term in document_tokens for term in profile_terms))
        hard_coverage = sum(coverage_values) / len(coverage_values) if coverage_values else 0.0
        return RankedProduct(product, score, hard_violations, hard_coverage, lexical_rank)

    @staticmethod
    def _constraint_match(product: Product, document_tokens: set[str], belief: Belief) -> tuple[float, bool]:
        value_tokens = tokens(belief.value)
        if not value_tokens:
            return 0.0, False
        expected_materials = set(value_tokens) & MATERIALS
        if belief.attribute == "material" and expected_materials:
            present = bool(expected_materials & set(product.materials))
            return float(present), bool(product.materials) and not present
        expected_colors = set(value_tokens) & COLORS
        if belief.attribute == "color" and expected_colors:
            present = bool(expected_colors & set(product.colors))
            return float(present), bool(product.colors) and not present
        if belief.attribute == "budget":
            match = PRICE_RE.search(belief.value)
            desired = belief.numeric_value or (float(match.group(1)) if match else None)
            if desired is not None and product.price is not None:
                relative_error = abs(product.price - desired) / max(desired, 1.0)
                return max(0.0, 1.0 - relative_error), relative_error > 0.40
            return 0.0, False
        normalized_value = normalize(belief.value)
        if normalized_value and normalized_value in product.all_text:
            return 1.0, False
        informative = [token for token in value_tokens if len(token) > 2]
        if not informative:
            informative = value_tokens
        coverage = sum(token in document_tokens for token in informative) / len(informative)
        return coverage, False

    def _diversify(self, pool: list[RankedProduct], top_k: int) -> list[RankedProduct]:
        """A bounded MMR-like pass that preserves relevance before novelty."""
        selected: list[RankedProduct] = []
        type_counts: Counter[str] = Counter()
        brand_counts: Counter[str] = Counter()
        remaining = list(pool)
        while remaining and len(selected) < top_k:
            def value(candidate: RankedProduct) -> tuple[float, str]:
                type_penalty = self.config.diversity_product_type_penalty * type_counts[candidate.product.product_type]
                brand_penalty = self.config.diversity_brand_penalty * brand_counts[candidate.product.brand]
                return (candidate.score - type_penalty - brand_penalty, candidate.product.parent_asin)

            choice = max(remaining, key=value)
            selected.append(choice)
            remaining.remove(choice)
            type_counts[choice.product.product_type] += 1
            brand_counts[choice.product.brand] += 1
        return selected

    @staticmethod
    def _diversify_frozen_m1(pool: list[RankedProduct], top_k: int) -> list[RankedProduct]:
        selected: list[RankedProduct] = []
        type_counts: Counter[str] = Counter()
        brand_counts: Counter[str] = Counter()
        remaining = list(pool)
        while remaining and len(selected) < top_k:
            def value(candidate: RankedProduct) -> tuple[float, str]:
                type_penalty = 1.6 * type_counts[candidate.product.product_type]
                brand_penalty = 0.35 * brand_counts[candidate.product.brand]
                return (candidate.score - type_penalty - brand_penalty, candidate.product.parent_asin)

            choice = max(remaining, key=value)
            selected.append(choice)
            remaining.remove(choice)
            type_counts[choice.product.product_type] += 1
            brand_counts[choice.product.brand] += 1
        return selected


class SparseRetriever:
    """The frozen M1 production retriever."""

    def __init__(self, catalog: CatalogIndex) -> None:
        self.catalog = catalog

    def retrieve(self, state: DialogueState, top_k: int) -> RetrievalResult:
        terms = state.query_terms()
        candidates = self.catalog.search(terms, limit=max(300, top_k * 30))
        ranked = [self._score(candidate, rank, state) for rank, candidate in enumerate(candidates, start=1)]
        qualifying = [candidate for candidate in ranked if candidate.hard_violations == 0]
        # Do not fill a short list with explicit hard-constraint violations. Soft
        # preferences influence scores only, so this never relaxes a hard rule.
        pool = qualifying if qualifying else ranked
        pool.sort(key=lambda candidate: (-candidate.score, candidate.product.parent_asin))
        if state.scenario == "browsing" and len(state.hard) < 2:
            pool = self._diversify(pool, top_k)
        else:
            pool = pool[:top_k]
        trace = {
            "retriever": "sparse",
            "query_terms": terms,
            "candidate_count": len(candidates),
            "qualified_count": len(qualifying),
            "hard_constraint_count": len(state.hard),
            "negative_constraint_count": len(state.negative),
            "scenario": state.scenario,
            "selected": [
                {
                    "parent_asin": item.product.parent_asin,
                    "score": round(item.score, 6),
                    "hard_violations": item.hard_violations,
                    "hard_coverage": round(item.hard_coverage, 4),
                }
                for item in pool
            ],
        }
        return RetrievalResult(tuple(pool), trace)

    def _score(self, product: Product, lexical_rank: int, state: DialogueState) -> RankedProduct:
        document_tokens = set(tokens(product.all_text, include_stopwords=True))
        score = 12.0 / math.sqrt(lexical_rank)
        category_terms = tokens(state.category_text)
        if category_terms:
            category_coverage = sum(term in product.categories or term in product.title for term in category_terms) / len(category_terms)
            score += 5.0 * category_coverage

        hard_violations = 0
        coverage_values: list[float] = []
        for belief in state.hard:
            coverage, violation = self._constraint_match(product, document_tokens, belief)
            coverage_values.append(coverage)
            score += 18.0 * coverage
            if violation:
                hard_violations += 1
                score -= 24.0
        for belief in state.soft:
            coverage, _ = self._constraint_match(product, document_tokens, belief)
            score += 4.0 * coverage
        for belief in state.negative:
            coverage, _ = self._constraint_match(product, document_tokens, belief)
            if coverage >= 0.7:
                score -= 28.0
                hard_violations += 1
        profile_terms = {term for tag in state.profile_tags for term in tokens(tag)}
        if profile_terms:
            score += min(1.5, 0.25 * sum(term in document_tokens for term in profile_terms))
        hard_coverage = sum(coverage_values) / len(coverage_values) if coverage_values else 0.0
        return RankedProduct(product, score, hard_violations, hard_coverage, lexical_rank)

    @staticmethod
    def _constraint_match(product: Product, document_tokens: set[str], belief: Belief) -> tuple[float, bool]:
        value_tokens = tokens(belief.value)
        if not value_tokens:
            return 0.0, False
        expected_materials = set(value_tokens) & MATERIALS
        if belief.attribute == "material" and expected_materials:
            present = bool(expected_materials & set(product.materials))
            return float(present), bool(product.materials) and not present
        expected_colors = set(value_tokens) & COLORS
        if belief.attribute == "color" and expected_colors:
            present = bool(expected_colors & set(product.colors))
            return float(present), bool(product.colors) and not present
        if belief.attribute == "budget":
            match = PRICE_RE.search(belief.value)
            desired = belief.numeric_value or (float(match.group(1)) if match else None)
            if desired is not None and product.price is not None:
                relative_error = abs(product.price - desired) / max(desired, 1.0)
                return max(0.0, 1.0 - relative_error), relative_error > 0.40
            return 0.0, False
        normalized_value = normalize(belief.value)
        if normalized_value and normalized_value in product.all_text:
            return 1.0, False
        informative = [token for token in value_tokens if len(token) > 2]
        if not informative:
            informative = value_tokens
        coverage = sum(token in document_tokens for token in informative) / len(informative)
        return coverage, False

    @staticmethod
    def _diversify(pool: list[RankedProduct], top_k: int) -> list[RankedProduct]:
        """A bounded MMR-like pass that preserves relevance before novelty."""
        selected: list[RankedProduct] = []
        type_counts: Counter[str] = Counter()
        brand_counts: Counter[str] = Counter()
        remaining = list(pool)
        while remaining and len(selected) < top_k:
            def value(candidate: RankedProduct) -> tuple[float, str]:
                type_penalty = 1.6 * type_counts[candidate.product.product_type]
                brand_penalty = 0.35 * brand_counts[candidate.product.brand]
                return (candidate.score - type_penalty - brand_penalty, candidate.product.parent_asin)

            choice = max(remaining, key=value)
            selected.append(choice)
            remaining.remove(choice)
            type_counts[choice.product.product_type] += 1
            brand_counts[choice.product.brand] += 1
        return selected
