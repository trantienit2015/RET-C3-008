"""AgentCore Platform v1.0 — RET-C3-008 autonomous graph (Cat 3).

Inherits AutonomousBaseGraph. Fixed pipeline: initialize → think ⇄ act → finalize.
The template supplies max_iterations, get_tools(), build_think_prompt(),
assemble_output(), and (CASE 2) a custom initialize node (S-1/S-2 InputValidate)
plus a report finalize node that runs assemble_output() to surface action_trace.
"""

from typing import Any, cast
from framework.graph.autonomous_base_graph import AutonomousBaseGraph
from framework.nodes.defaults.finalize_node import FinalizeNode

from src.nodes.input_validate_node import InputValidateInitializeNode
from src.schemas.state import State
from src.tools.energy_tools import TOOL_REGISTRY

_MAX_ITERATIONS = 12


class ReportFinalizeNode(FinalizeNode):
    """Finalize node that runs assemble_output() so action_trace + reports surface."""

    def __init__(self, agent: Any) -> None:
        self._agent = agent

    def on_finalize(self, state: Any) -> dict[str, Any]:
        return cast(dict[str, Any], self._agent.assemble_output(state))


class Graph(AutonomousBaseGraph):
    """RET-C3-008 — Retail Autonomous Store Energy Anomaly Detection & Cost Reduction Agent."""

    @property
    def name(self) -> str:
        return "ret-c3-008"

    @property
    def state_schema(self) -> type:
        return State

    @property
    def max_iterations(self) -> int:
        return int(self.config.get("max_iterations", _MAX_ITERATIONS))

    def get_tools(self) -> list[Any]:
        return list(TOOL_REGISTRY.values())

    def build_think_prompt(self, state: Any) -> str:
        return (
            "You are an autonomous store-energy agent. Detect anomalies vs the per-store "
            "baseline and act: dispatch a maintenance ticket, send a staff alert, or (with "
            "approval) write an HVAC setpoint; then verify return-to-baseline.\n"
            f"Store: {state.get('store_id')}\n"
            f"Telemetry: {state.get('telemetry', {})}\n"
            f"Anomalies so far: {state.get('anomalies', [])}\n"
            f"Prior tool results: {state.get('tool_results', [])}\n"
            "What is your next action? Stop when anomalies are resolved (in-band ≥2 cycles)."
        )

    def assemble_output(self, state: Any) -> dict[str, Any]:
        return {
            "final_output": {
                "store_id": state.get("store_id"),
                "anomalies": state.get("anomalies", []),
                "action_trace": state.get("action_trace", []),
                "iterations": state.get("iterations", 0),
            },
            "artifacts": state.get("artifacts", []),
            "thoughts": state.get("thoughts", []),
            "iterations": state.get("iterations", 0),
        }

    def register_nodes(self) -> None:
        super().register_nodes()  # wires initialize/think/act/finalize
        # CASE 2: replace initialize (S-1/S-2 InputValidate), think (S-2 rejection
        # short-circuit — the backbone routes initialize→think unconditionally),
        # and finalize (assemble_output → action_trace + reports).
        from src.graph.guarded_think_node import GuardedThinkNode

        self._nodes["initialize"] = InputValidateInitializeNode()
        self._nodes["think"] = GuardedThinkNode(self, self._build_llm_with_tools())
        self._nodes["finalize"] = ReportFinalizeNode(self)
