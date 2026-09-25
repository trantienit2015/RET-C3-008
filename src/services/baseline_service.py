"""AgentCore Platform v1.0 — RET-C3-008 per-store baseline service.

Service layer: loads and resolves the per-store energy baseline (a deployment-time
artifact) that the anomaly-detection tool checks against. Pure, deterministic, no
credentials — the baseline model itself is provisioned externally.
"""

from __future__ import annotations

from typing import Any, cast


class BaselineService:
    """Resolves per-store baselines: mean/σ per equipment × time-of-day × day-of-week × season.

    The baseline is a provisioned artifact injected at construction (a plain dict
    keyed by store_id). This service selects the applicable per-equipment baseline
    for a given cycle context; the LLM never computes the baseline.
    """

    def __init__(self, baselines: dict[str, Any] | None = None):
        # baselines: {store_id: {equipment: {"mean": float, "std": float}}}
        self._baselines = baselines or {}

    def for_store(self, store_id: str) -> dict[str, Any]:
        """Return the per-equipment baseline mapping for a store (empty if unknown)."""
        return dict(self._baselines.get(store_id, {}))

    def has_baseline(self, store_id: str) -> bool:
        """Whether a baseline has been provisioned for the store."""
        return store_id in self._baselines and bool(self._baselines[store_id])

    def equipment_baseline(self, store_id: str, equipment: str) -> dict[str, Any] | None:
        """Return {'mean','std'} for one equipment, or None when unprovisioned."""
        return cast(dict[str, Any] | None, self._baselines.get(store_id, {}).get(equipment))
