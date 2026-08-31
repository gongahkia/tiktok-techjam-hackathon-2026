from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
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
class RetrievalResult:
    ranked: tuple[RankedProduct, ...]
    trace: dict


class SparseRetriever:
    """Field-aware lexical retrieval followed by explicit, stable reranking."""

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
