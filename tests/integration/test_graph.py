# RET-C3-008 — Integration test: autonomous loop compile + invoke (budget-bounded).

from framework.schemas.agent_status import AgentStatus
from framework.schemas.invocation_context import InvocationContext
from framework.schemas.trust_level import TrustLevel

from src.graph.graph import Graph


class FakeLLM:
    """Emits one tool call, then terminates (empty tool_calls -> SUCCESS)."""

    def __init__(self):
        self._calls = 0

    def bind_tools(self, tools):
        return self

    def complete(self, prompt):
        self._calls += 1
        if self._calls == 1:
            return {
                "content": "Dispatch a maintenance ticket for the anomalous HVAC unit.",
                "tool_calls": [
                    {"name": "dispatch_maintenance_ticket", "args": {"store_id": "store-1", "equipment": "hvac_1", "detail": "z-score high"}}
                ],
            }
        return {"content": "Anomaly resolved; stopping.", "tool_calls": []}


def _ctx(session="it-1"):
    return InvocationContext(session_id=session, caller_trust_level=TrustLevel.INTERNAL, caller_id="scheduler")


def _agent(llm=None):
    a = Graph(config={"llm": llm or FakeLLM(), "budget_usd": 0.10, "max_iterations": 12, "max_retry": 1})
    a.compile()
    return a


def test_full_loop_terminates():
    result = _agent().invoke("Monitor store-1 energy telemetry for anomalies.", ctx=_ctx())
    # Loop terminates (SUCCESS) within the iteration/budget bound.
    assert result["status"] in (AgentStatus.SUCCESS, AgentStatus.SUCCESS.value)
    assert (result.get("iterations") or 0) <= 12


def test_input_validate_rejects_token():
    result = _agent().invoke("telemetry with Bearer abc.def token", ctx=_ctx("it-2"))
    # InputValidate (initialize) sets ERROR before the loop runs.
    assert result["status"] in (AgentStatus.ERROR, AgentStatus.ERROR.value)


def test_budget_ceiling_bounds_iterations():
    # A never-stopping LLM must still terminate via the budget / iteration ceiling.
    class LoopingLLM:
        def bind_tools(self, tools):
            return self

        def complete(self, prompt):
            return {"content": "keep going", "tool_calls": [{"name": "send_staff_alert", "args": {"store_id": "s", "message": "m"}}]}

    result = _agent(LoopingLLM()).invoke("monitor", ctx=_ctx("it-3"))
    assert (result.get("iterations") or 0) <= 12
