from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable


TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)
SPACE_RE = re.compile(r"\s+")
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from",
    "i", "in", "is", "it", "me", "my", "of", "on", "or", "please", "some",
    "that", "the", "this", "to", "want", "with", "would", "you", "looking",
    "what", "which", "have", "has", "do", "does", "about", "those", "yet",
}
COMMON_FASHION_VARIANTS = {
    "blak": "black",
    "blu": "blue",
    "cottn": "cotton",
    "lether": "leather",
    "shooes": "shoes",
    "sneekers": "sneakers",
    "trainers": "sneakers",
    "tee": "tshirt",
}


def flatten(value: object) -> str:
    """Flatten a catalog field without discarding its keys."""
    if value is None:
        return ""
    if isinstance(value, dict):
        return " ".join(f"{key} {item}" for key, item in value.items() if item not in (None, "", [], {}))
    if isinstance(value, list):
        return " ".join(str(item) for item in value if item not in (None, ""))
    return str(value)


def normalize(text: object) -> str:
    """Make catalog and dialogue text comparable while retaining useful tokens."""
    value = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode("ascii").lower()
    value = value.replace("women's", "women").replace("woman's", "women")
    value = value.replace("men's", "men").replace("man's", "men")
    value = re.sub(r"\bt[ -]?shirts?\b", "tshirt", value)
    value = re.sub(r"\bgrey\b", "gray", value)
    for variant, canonical in COMMON_FASHION_VARIANTS.items():
        value = re.sub(rf"\b{variant}\b", canonical, value)
    value = re.sub(r"[^a-z0-9$]+", " ", value)
    return SPACE_RE.sub(" ", value).strip()


def tokens(text: object, *, include_stopwords: bool = False) -> list[str]:
    result = [token.lower() for token in TOKEN_RE.findall(normalize(text))]
    if include_stopwords:
        return result
    return [token for token in result if len(token) > 1 and token not in STOPWORDS]


def unique(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def safe_fts_expression(terms: Iterable[str], limit: int = 48) -> str:
    """Return a conservative FTS5 OR expression using only normalized tokens."""
    selected = unique(token for term in terms for token in tokens(term))[:limit]
    return " OR ".join(f'"{term}"' for term in selected)
