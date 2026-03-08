"""Retrieval post-processing: decay / MMR / hard-min."""

from __future__ import annotations

import math
from typing import Any


def apply_time_decay(score: float, age_hours: float, half_life_hours: float = 24.0) -> float:
    """Apply exponential time decay to score."""

    return score * math.exp(-max(age_hours, 0.0) / max(half_life_hours, 1.0))


def hard_min_filter(items: list[dict[str, Any]], min_score: float) -> list[dict[str, Any]]:
    """Filter out items below score threshold."""

    return [it for it in items if float(it.get("score", 0.0)) >= min_score]


def mmr_rerank(items: list[dict[str, Any]], lambda_weight: float = 0.7) -> list[dict[str, Any]]:
    """Simple deterministic rerank placeholder for MMR integration."""

    return sorted(items, key=lambda x: float(x.get("score", 0.0)) * lambda_weight, reverse=True)
