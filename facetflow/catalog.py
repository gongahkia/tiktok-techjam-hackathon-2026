from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import tempfile
from typing import Iterable

from .state import COLORS, MATERIALS
from .text import flatten, normalize, safe_fts_expression, tokens, unique


INDEX_VERSION = "facetflow-catalog-v3"
FACET_RE = re.compile(r"\b(" + "|".join(sorted(MATERIALS | COLORS)) + r")\b", re.I)


@dataclass(frozen=True)
class Product:
    parent_asin: str
    title: str
    categories: str
    features: str
    details: str
    description: str
    store: str
    price: float | None
    materials: tuple[str, ...]
    colors: tuple[str, ...]
    product_type: str
    brand: str
    fts_score: float

    @property
    def all_text(self) -> str:
        return " ".join((self.title, self.categories, self.features, self.details, self.store, self.description))


def catalog_fingerprint(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def cache_directory() -> Path:
    return Path(os.environ.get("FACETFLOW_CACHE_DIR", ".facetflow_cache"))


def _facet_values(text: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    values = unique(normalize(value) for value in FACET_RE.findall(text))
    return tuple(value for value in values if value in MATERIALS), tuple(value for value in values if value in COLORS)


def _product_type(categories: str, title: str) -> str:
    category_terms = [part for part in categories.split(" ") if part not in {"clothing", "shoes", "jewelry", "and"}]
    if category_terms:
        return " ".join(category_terms[-3:])
    return " ".join(tokens(title)[:3]) or "product"


def _brand(store: str, details: str) -> str:
    match = re.search(r"(?:brand|manufacturer|brand name)\s+([a-z0-9 ]{2,80})", details)
    return normalize(match.group(1)) if match else store


def _index_path(catalog_path: Path, cache_path: Path, fingerprint: str) -> Path:
    return cache_path / f"{catalog_path.stem}-{fingerprint[:16]}-{INDEX_VERSION}.sqlite3"


def build_catalog_index(catalog_path: str | Path, cache_path: str | Path | None = None) -> Path:
    """Build a versioned SQLite/FTS cache from an immutable JSONL catalog."""
    source = Path(catalog_path)
    if not source.is_file():
        raise FileNotFoundError(f"catalog not found: {source}")
    cache = Path(cache_path) if cache_path is not None else cache_directory()
    cache.mkdir(parents=True, exist_ok=True)
    fingerprint = catalog_fingerprint(source)
    destination = _index_path(source, cache, fingerprint)
    if destination.exists() and _index_matches(destination, fingerprint):
        return destination

    fd, temp_name = tempfile.mkstemp(prefix=f".{destination.name}.", suffix=".tmp", dir=cache)
    os.close(fd)
    temporary = Path(temp_name)
    try:
        connection = sqlite3.connect(temporary)
        try:
            connection.executescript(
                """
                PRAGMA journal_mode=OFF;
                PRAGMA synchronous=OFF;
                PRAGMA temp_store=MEMORY;
                CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE products (
                    parent_asin TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    categories TEXT NOT NULL,
                    features TEXT NOT NULL,
                    details TEXT NOT NULL,
                    description TEXT NOT NULL,
                    store TEXT NOT NULL,
                    price REAL,
                    materials TEXT NOT NULL,
                    colors TEXT NOT NULL,
                    product_type TEXT NOT NULL,
                    brand TEXT NOT NULL,
                    CHECK (parent_asin <> '')
                ) WITHOUT ROWID;
                CREATE VIRTUAL TABLE product_fts USING fts5(
                    parent_asin UNINDEXED, title, categories, features, details, store, description,
                    tokenize='unicode61 remove_diacritics 2'
                );
                """
            )
            product_rows: list[tuple] = []
            fts_rows: list[tuple] = []
            rows = 0
            with source.open(encoding="utf-8") as handle:
                for line in handle:
                    if not line.strip():
                        continue
                    raw = json.loads(line)
                    parent_asin = str(raw["parent_asin"])
                    title = normalize(raw.get("title"))
                    categories = normalize(flatten(raw.get("categories")))
                    features = normalize(flatten(raw.get("features")))
                    details = normalize(flatten(raw.get("details")))
                    description = normalize(flatten(raw.get("description")))
                    store = normalize(raw.get("store"))
                    all_text = " ".join((title, categories, features, details, store, description)).strip()
                    materials, colors = _facet_values(all_text)
                    price = raw.get("price")
                    price_value = float(price) if isinstance(price, (int, float)) else None
                    product_rows.append((
                        parent_asin, title, categories, features, details, description, store, price_value,
                        json.dumps(materials), json.dumps(colors), _product_type(categories, title),
                        _brand(store, details),
                    ))
                    fts_rows.append((parent_asin, title, categories, features, details, store, description))
                    rows += 1
                    if len(product_rows) >= 1_000:
                        connection.executemany("INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", product_rows)
                        connection.executemany("INSERT INTO product_fts VALUES (?, ?, ?, ?, ?, ?, ?)", fts_rows)
                        product_rows.clear()
                        fts_rows.clear()
            if product_rows:
                connection.executemany("INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", product_rows)
                connection.executemany("INSERT INTO product_fts VALUES (?, ?, ?, ?, ?, ?, ?)", fts_rows)
            connection.executemany(
                "INSERT INTO metadata VALUES (?, ?)",
                (("version", INDEX_VERSION), ("catalog_sha256", fingerprint), ("row_count", str(rows))),
            )
            connection.execute("INSERT INTO product_fts(product_fts) VALUES ('optimize')")
            connection.commit()
        finally:
            connection.close()
        os.replace(temporary, destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return destination


def _index_matches(path: Path, fingerprint: str) -> bool:
    try:
        connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            rows = dict(connection.execute("SELECT key, value FROM metadata"))
        finally:
            connection.close()
    except sqlite3.Error:
        return False
    return rows.get("version") == INDEX_VERSION and rows.get("catalog_sha256") == fingerprint and int(rows.get("row_count", "0")) > 0


class CatalogIndex:
    """Read-only query layer over a reproducible local catalog index."""

    def __init__(self, catalog_path: str | Path, cache_path: str | Path | None = None) -> None:
        self.catalog_path = Path(catalog_path)
        self.path = build_catalog_index(self.catalog_path, cache_path)
        self.connection = sqlite3.connect(f"file:{self.path}?mode=ro", uri=True)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA query_only=ON")

    def close(self) -> None:
        self.connection.close()

    def search(self, terms: Iterable[str], limit: int = 600) -> list[Product]:
        expression = safe_fts_expression(terms)
        if expression:
            rows = self.connection.execute(
                """
                SELECT p.*, bm25(product_fts, 0.0, 8.0, 6.0, 3.5, 2.5, 3.0, 1.0) AS fts_score
                FROM product_fts
                JOIN products AS p ON p.parent_asin = product_fts.parent_asin
                WHERE product_fts MATCH ?
                ORDER BY fts_score, p.parent_asin
                LIMIT ?
                """,
                (expression, limit),
            ).fetchall()
        else:
            rows = self.connection.execute(
                """
                SELECT p.*, 0.0 AS fts_score FROM products AS p
                ORDER BY p.parent_asin LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._product(row) for row in rows]

    def products_by_id(self, parent_asins: Iterable[str]) -> list[Product]:
        """Fetch known catalog products in caller order for opt-in diagnostics."""
        ordered = list(dict.fromkeys(str(parent_asin) for parent_asin in parent_asins))
        if not ordered:
            return []
        placeholders = ", ".join("?" for _ in ordered)
        rows = self.connection.execute(
            f"SELECT p.*, 0.0 AS fts_score FROM products AS p WHERE p.parent_asin IN ({placeholders})",
            ordered,
        ).fetchall()
        products = {str(row["parent_asin"]): self._product(row) for row in rows}
        return [products[parent_asin] for parent_asin in ordered if parent_asin in products]

    def size_bytes(self) -> int:
        return self.path.stat().st_size

    @staticmethod
    def _product(row: sqlite3.Row) -> Product:
        return Product(
            parent_asin=str(row["parent_asin"]), title=str(row["title"]), categories=str(row["categories"]),
            features=str(row["features"]), details=str(row["details"]), description=str(row["description"]),
            store=str(row["store"]), price=row["price"], materials=tuple(json.loads(row["materials"])),
            colors=tuple(json.loads(row["colors"])), product_type=str(row["product_type"]), brand=str(row["brand"]),
            fts_score=float(row["fts_score"]),
        )
