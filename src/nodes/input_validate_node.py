"""AgentCore Platform v1.0 — RET-C3-008 InputValidate entry node (S-1/S-2)."""

import re
from typing import Any, ClassVar

from framework.nodes.defaults.autonomous_initialize_node import AutonomousInitializeNode
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event

# S-2 deterministic sensitive-content patterns (non-LLM).
_JWT_RE = re.compile(r"\beyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+")
_BEARER_RE = re.compile(r"\bBearer\s+[A-Za-z0-9._\-]+", re.IGNORECASE)
_CRED_JSON_RE = re.compile(r'"(password|secret|api_key|token)"\s*:', re.IGNORECASE)
# 個人番号 / staff personal number: 12-digit (optionally hyphenated).
_MYNUMBER_RE = re.compile(r"\b\d{4}-?\d{4}-?\d{4}\b")


class InputValidateInitializeNode(AutonomousInitializeNode):
    """Autonomous initialize node with an S-1/S-2 input safety gate.

    Runs before the think→act loop. S-1 trust is enforced by the framework
    `__call__` against `required_trust_level`; this node adds the S-2
    deterministic scan (tokens / credential JSON / operator PII embedded in the
    telemetry payload) and seeds `action_trace`.
    """

    # S-1: autonomous energy control (BMS write reachable in the loop) — INTERNAL.
    required_trust_level: ClassVar[TrustLevel] = TrustLevel.INTERNAL

    def on_initialize(self, state: dict[str, Any]) -> dict[str, Any]:
        raw = state.get("user_input", "")
        emit_trace_event(
            "input_validate",
            {"correlation_id": state.get("correlation_id")},
            state,
        )
        text = raw if isinstance(raw, str) else str(raw)
        rejected = bool(
            _JWT_RE.search(text) or _BEARER_RE.search(text) or _CRED_JSON_RE.search(text) or _MYNUMBER_RE.search(text)
        )
        # The autonomous backbone always routes initialize -> think, so a terminal
        # ERROR set here would be overwritten by think. Instead, flag the rejection
        # in working_memory; GuardedThinkNode short-circuits to ERROR before the LLM.
        return {
            "action_trace": [],
            "working_memory": {"input_rejected": rejected},
        }
