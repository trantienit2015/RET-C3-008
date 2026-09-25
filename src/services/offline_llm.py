"""Deterministic, offline stand-in for the LLM of RET-C3-008 (store energy, Cat 3).

NON-PRODUCTION. It lets the autonomous think -> act -> observe loop run end to end
with no model, no API key and no network egress (STG smoke runs, local demos). It
makes no judgement: it normalises whatever telemetry window the think prompt carries,
runs the baseline anomaly check on that frame, and then stops. It never calls
``hvac_setpoint_write``: equipment writes stay behind the confirmation policy.
A real deployment injects a ``BaseLLM`` client instead.

The client is stateless: every decision is derived from the prompt it receives, so
one instance can be shared across concurrent invocations.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Iterator
from typing import Any

from shared.services.llm.base_llm import BaseLLM

_MODEL = "offline-deterministic"


def _reply(content: str, tool_calls: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "content": content,
        "tool_calls": tool_calls or [],
        "model": _MODEL,
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "model": _MODEL},
    }


def _as_text(messages: Any) -> str:
    if isinstance(messages, str):
        return messages
    if isinstance(messages, list):
        return "\n".join(str(m.get("content", "")) if isinstance(m, dict) else str(m) for m in messages)
    return str(messages)


def _field(prompt: str, label: str, default: Any) -> Any:
    """Read one ``<label>: <python literal>`` line of the think prompt; default if absent/unparsable."""
    match = re.search(rf"^{re.escape(label)}: (.*)$", prompt, re.M)
    if not match:
        return default
    try:
        value = ast.literal_eval(match.group(1).strip())
    except (ValueError, SyntaxError):
        return default
    return value if isinstance(value, type(default)) else default


class OfflineStoreEnergyLLM(BaseLLM):
    """Scripted ``BaseLLM`` that drives one observe -> detect -> stop cycle."""

    def complete(self, messages: list[Any]) -> dict[str, Any]:
        prompt = _as_text(messages)
        results = _field(prompt, "Prior tool results", [])
        used = {r.get("tool") for r in results if isinstance(r, dict)}
        if "detect_anomaly" in used:
            return _reply(
                "Offline stand-in: telemetry observed and checked against the baseline. "
                "Equipment writes need confirmation; hvac_setpoint_write was not called."
            )
        observed = next(
            (r for r in reversed(results) if isinstance(r, dict) and r.get("tool") == "observe_telemetry"), None
        )
        if observed is None:
            return _reply(
                "Normalising the telemetry window.",
                [
                    {
                        "name": "observe_telemetry",
                        "args": {"store_id": _field(prompt, "Store", ""), "window": _field(prompt, "Telemetry", {})},
                    }
                ],
            )
        telemetry = observed.get("result") if isinstance(observed.get("result"), dict) else {}
        return _reply(
            "Checking the telemetry against the store baseline.",
            [{"name": "detect_anomaly", "args": {"telemetry": telemetry, "baseline": {}}}],
        )

    def stream(self, messages: list[Any]) -> Iterator[str]:
        yield str(self.complete(messages)["content"])

    def bind_tools(self, tools: list[Any]) -> BaseLLM:
        return self
