"""AgentCore Platform v1.0 — RET-C3-008 GuardedThinkNode.

Wraps the framework ThinkNode with an S-2 rejection short-circuit: the
autonomous backbone routes initialize → think unconditionally, so a terminal
ERROR set in the initialize node would be overwritten. This node checks the
`working_memory["input_rejected"]` flag set by InputValidate and terminates the
loop with ERROR before any LLM call when the input was rejected.
"""

from typing import Any, cast
from framework.nodes.defaults.think_node import ThinkNode
from framework.schemas.agent_status import AgentStatus
from shared.utils.audit_logger import emit_trace_event


class GuardedThinkNode(ThinkNode):
    """ThinkNode variant that halts the loop on an S-2 input rejection."""

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        if (state.get("working_memory") or {}).get("input_rejected"):
            emit_trace_event(
                "input_rejected_halt",
                {"correlation_id": state.get("correlation_id")},
                state,
            )
            return {
                "status": AgentStatus.ERROR.value,
                "error_log": ["InputValidate: sensitive content (token / credential / PII) rejected"],
                "tool_calls": [],
                "iterations": state.get("iterations", 0) + 1,
            }
        return cast(dict[str, Any], super().execute(state))
