# Catalog profile

Fingerprint: `da979b05a68af864cb0dcf9ee6a81c010c7e66a57978ad286c7a2e005fc69a67`. Rows: `50000`.

## Usable fields

| Field | Non-empty rows | Use in FacetFlow |
| --- | ---: | --- |
| title | 49998 | strongest lexical field |
| categories | 50000 | category and product-type routing |
| features | 44781 | requirements and material evidence |
| details | 48330 | sparse color, material, brand and size evidence |
| description | 26113 | lower-weight supporting evidence |
| store | 49686 | brand-like supporting evidence |
| price | 10527 | budget verification only; sparse |

Price is intentionally a verifier rather than a mandatory retriever because it is missing for most rows. The catalog JSONL remains the raw-value audit source; the generated index stores normalized fields and is ignored by Git.

## Frequent extracted facets

| Material | Rows mentioning it | Color | Rows mentioning it |
| --- | ---: | --- | ---: |
| cotton | 20495 | black | 12534 |
| leather | 17589 | silver | 9371 |
| polyester | 16740 | gold | 6926 |
| rubber | 10506 | white | 6682 |
| spandex | 7992 | blue | 4922 |
| nylon | 4060 | red | 3505 |
| suede | 2453 | gray | 3439 |
| denim | 2051 | pink | 2539 |
| wool | 1899 | green | 2487 |
| rayon | 1813 | yellow | 2006 |
| canvas | 1514 | brown | 1765 |
| acrylic | 1359 | navy | 1429 |
| silk | 993 | purple | 1112 |
| linen | 886 | orange | 724 |
| viscose | 704 | khaki | 405 |
| cashmere | 463 | beige | 398 |
|  |  | tan | 364 |
|  |  | ivory | 170 |
