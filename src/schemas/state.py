"""AgentCore Platform v1.0 — RET-C3-008 state schema (Cat 3)."""

from typing import NotRequired

from framework.schemas.autonomous_state import AutonomousState


class State(AutonomousState):
    """Autonomous store-energy anomaly detection agent state.

    Extends AutonomousState (which provides plan, thoughts, tool_calls,
    tool_results, working_memory, memory_loaded, artifacts, final_output,
    cost_usd, plus the shared AgentState fields). Only agent-specific fields
    are declared here; all are NotRequired[...] (contract C8) and read via state.get().
    """

    store_id: NotRequired[str]  # type: ignore[valid-type]
    # Normalized telemetry frame for the cycle window.
    telemetry: NotRequired[dict]  # type: ignore[valid-type]
    # Per-store baseline config (provisioned deployment-time artifact).
    baseline_config: NotRequired[dict]  # type: ignore[valid-type]
    # Detected anomalies for the current cycle.
    anomalies: NotRequired[list[dict]]  # type: ignore[valid-type]
    # Append-only audit of every observe→reason→act→verify entry.
    action_trace: NotRequired[list[dict]]  # type: ignore[valid-type]
