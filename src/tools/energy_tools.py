"""AgentCore Platform v1.0 — RET-C3-008 store-energy tools.

Tools are the deterministic "Tool" layer the autonomous Agent drives. Each is a
plain callable with a ``.name`` attribute (ToolActNode resolves tools by name and
invokes them as ``tool(**args)``). No credentials, no LLM here — the think loop
decides which tool to call; these execute the action.

HITL policy (config `hitl.tool_policies`):
  - dispatch_maintenance_ticket / send_staff_alert : allow (no confirmation)
  - hvac_setpoint_write                            : confirm (D6 interrupt, INTERNAL)
"""

from __future__ import annotations

import math
from collections.abc import Callable
from typing import Any, TypeVar

_F = TypeVar("_F", bound=Callable[..., Any])


def _named(name: str) -> Callable[[_F], _F]:
    """Attach a stable ``.name`` so ToolActNode can resolve the tool by name."""

    def deco(fn: _F) -> _F:
        setattr(fn, "name", name)
        return fn

    return deco


@_named("observe_telemetry")
def observe_telemetry(store_id: str, window: dict[str, Any] | None = None) -> dict[str, Any]:
    """Normalize a telemetry frame for the cycle window (per equipment type).

    In production this reads smart-meter / BMS streams; here it normalizes the
    provided window payload deterministically.
    """
    window = window or {}
    equipment = {}
    for name, series in (window.get("equipment") or {}).items():
        values = [float(v) for v in (series or []) if isinstance(v, (int, float))]
        equipment[name] = {
            "mean": sum(values) / len(values) if values else 0.0,
            "n": len(values),
            "last": values[-1] if values else 0.0,
        }
    return {
        "store_id": store_id,
        "equipment": equipment,
        "outdoor_temp": window.get("outdoor_temp"),
        "store_hours": window.get("store_hours"),
    }


@_named("detect_anomaly")
def detect_anomaly(telemetry: dict[str, Any], baseline: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Deterministic anomaly detection vs per-store baseline (mean ± k·σ).

    baseline: {equipment_name: {"mean": float, "std": float}}. An equipment
    reading beyond mean ± 3σ is flagged. The LLM does NOT compute the baseline.
    """
    baseline = baseline or {}
    anomalies: list[dict[str, Any]] = []
    for name, obs in (telemetry.get("equipment") or {}).items():
        base = baseline.get(name)
        if not base:
            continue
        mean = float(base.get("mean", 0.0))
        std = float(base.get("std", 0.0)) or 1.0
        z = abs(obs.get("last", 0.0) - mean) / std
        if z >= 3.0:
            anomalies.append(
                {
                    "equipment": name,
                    "observed": obs.get("last"),
                    "baseline_mean": mean,
                    "z_score": round(z, 2),
                    "classification": _classify(name, obs, base),
                }
            )
    return anomalies


def _classify(name: str, obs: dict[str, Any], base: dict[str, Any]) -> str:
    if "hvac" in name.lower():
        return "equipment_fault" if obs.get("last", 0) > base.get("mean", 0) else "schedule_gap"
    if "refrigerat" in name.lower():
        return "equipment_fault"
    return "behavior"


@_named("dispatch_maintenance_ticket")
def dispatch_maintenance_ticket(store_id: str, equipment: str, detail: str = "") -> dict[str, Any]:
    """Dispatch a maintenance ticket (no approval gate)."""
    return {"action": "ticket", "store_id": store_id, "equipment": equipment, "detail": detail, "dispatched": True}


@_named("send_staff_alert")
def send_staff_alert(store_id: str, message: str) -> dict[str, Any]:
    """Send a staff alert (no approval gate)."""
    return {"action": "alert", "store_id": store_id, "message": message, "sent": True}


@_named("hvac_setpoint_write")
def hvac_setpoint_write(store_id: str, equipment: str, setpoint: float, bms_available: bool = True) -> dict[str, Any]:
    """Auto-adjust an HVAC setpoint via BMS (approval-gated write).

    Gated by `hitl.tool_policies['hvac_setpoint_write'] = confirm` (D6 interrupt).
    Degraded fallback: when the BMS is absent, no write is performed — the caller
    should fall back to a maintenance ticket (alert-only mode).
    """
    if not bms_available:
        return {"action": "hvac_write", "store_id": store_id, "written": False, "fallback": "ticket_only"}
    return {"action": "hvac_write", "store_id": store_id, "equipment": equipment, "setpoint": setpoint, "written": True}


@_named("verify_return_to_baseline")
def verify_return_to_baseline(
    store_id: str, equipment: str, recent_readings: list[Any] | None = None, baseline_mean: float = 0.0
) -> dict[str, Any]:
    """Confirm energy returns within 5% of baseline for ≥2 consecutive cycles."""
    readings = [float(r) for r in (recent_readings or []) if isinstance(r, (int, float))]
    if len(readings) < 2 or baseline_mean == 0:
        return {"store_id": store_id, "equipment": equipment, "verification": "pending"}
    in_band = all(abs(r - baseline_mean) / abs(baseline_mean) <= 0.05 for r in readings[-2:])
    return {
        "store_id": store_id,
        "equipment": equipment,
        "verification": "in_band" if in_band else "out_of_band",
    }


# Registry consumed by Graph.get_tools().
TOOL_REGISTRY = {
    "observe_telemetry": observe_telemetry,
    "detect_anomaly": detect_anomaly,
    "dispatch_maintenance_ticket": dispatch_maintenance_ticket,
    "send_staff_alert": send_staff_alert,
    "hvac_setpoint_write": hvac_setpoint_write,
    "verify_return_to_baseline": verify_return_to_baseline,
}


def std_dev(values: list[float]) -> float:
    """Sample standard deviation helper (used when computing baselines offline)."""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return math.sqrt(sum((v - mean) ** 2 for v in values) / (len(values) - 1))
