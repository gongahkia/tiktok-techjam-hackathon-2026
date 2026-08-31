from __future__ import annotations

import os
from pathlib import Path

from .catalog import CatalogIndex
from .policy import ClarificationPolicy, response_message
from .retrieval import SparseRetriever
from .state import DialogueState


class Agent:
    """Contract-compatible FacetFlow adapter; its default path is entirely offline."""

    def __init__(self, catalog_path: str | Path = "data/catalog.jsonl") -> None:
        cache_path = os.environ.get("FACETFLOW_CACHE_DIR")
        self.sparse_only = os.environ.get("FACETFLOW_SPARSE_ONLY", "1") != "0"
        self.catalog = CatalogIndex(catalog_path, cache_path)
        self.retriever = SparseRetriever(self.catalog)
        self.policy = ClarificationPolicy()
        self.sessions: dict[str, DialogueState] = {}
        self._response_cache: dict[tuple[str, tuple], tuple[dict, dict]] = {}

    def reset(self, session_id: str, user_profile: dict) -> None:
        self.sessions[session_id] = DialogueState.create(session_id, user_profile)

    def respond(self, session_id: str, user_message: str, turn: int, top_k: int) -> dict:
        if session_id not in self.sessions:
            raise RuntimeError("reset must be called before respond")
        state = self.sessions[session_id]
        state.ingest(user_message, turn)
        signature = state.retrieval_signature()
        cache_key = (session_id, signature)
        cached = self._response_cache.get(cache_key)
        if cached is not None:
            response, trace = cached
            state.mark_shown([item["parent_asin"] for item in response["recommendations"]])
            state.last_trace = dict(trace)
            return {
                **response,
                "recommendations": [dict(item) for item in response["recommendations"]],
                "usage": dict(response["usage"]),
            }
        result = self.retriever.retrieve(state, top_k)
        decision = self.policy.decide(state, result.ranked)
        if decision.ask_attribute:
            state.asked_attributes.add(decision.ask_attribute)
        recommendations = [{"parent_asin": item.product.parent_asin} for item in result.ranked[:top_k]]
        state.mark_shown([item["parent_asin"] for item in recommendations])
        state.last_trace = {
            **result.trace,
            "retrieval_mode": "sparse_only" if self.sparse_only else "sparse_fallback_no_dense_artifact",
            "clarification": decision.__dict__,
        }
        response = {
            "message": response_message(state, decision, len(recommendations)),
            "ask_attribute": decision.ask_attribute,
            "recommendations": recommendations,
            "usage": {"prompt_tokens": 0, "completion_tokens": 0},
        }
        self._response_cache[cache_key] = (response, dict(state.last_trace))
        return response

    def debug_trace(self, session_id: str) -> dict:
        """Inspection hook deliberately kept outside the official response schema."""
        return dict(self.sessions[session_id].last_trace)
