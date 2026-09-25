# RET-C3-008 - offline deterministic LLM stand-in (non-production; STG smoke / local demo).

from framework.schemas.agent_status import AgentStatus
from framework.schemas.invocation_context import InvocationContext
from framework.schemas.trust_level import TrustLevel

from src.graph.graph import Graph
from src.services.offline_llm import OfflineStoreEnergyLLM


def _agent():
    agent = Graph(config={"llm": OfflineStoreEnergyLLM(), "budget_usd": 0.10, "max_iterations": 12, "max_retry": 1})
    agent.compile()
    return agent


def test_first_step_observes_telemetry_from_prompt_state():
    prompt = "Store: 'store-7'\nTelemetry: {'equipment': {'hvac_1': [10.0, 11.0]}}\nPrior tool results: []\n"
    reply = OfflineStoreEnergyLLM().complete(prompt)
    assert [c["name"] for c in reply["tool_calls"]] == ["observe_telemetry"]
    assert reply["tool_calls"][0]["args"]["store_id"] == "store-7"
    assert reply["tool_calls"][0]["args"]["window"]["equipment"]["hvac_1"] == [10.0, 11.0]


def test_second_step_checks_the_observed_frame():
    frame = {"store_id": "store-7", "equipment": {"hvac_1": {"mean": 10.5, "n": 2, "last": 11.0}}}
    prompt = f"Prior tool results: [{{'tool': 'observe_telemetry', 'result': {frame!r}, 'args': {{}}}}]\n"
    reply = OfflineStoreEnergyLLM().complete(prompt)
    assert [c["name"] for c in reply["tool_calls"]] == ["detect_anomaly"]
    assert reply["tool_calls"][0]["args"]["telemetry"] == frame


def test_never_writes_setpoint_and_loop_terminates():
    ctx = InvocationContext(session_id="offline-1", caller_trust_level=TrustLevel.INTERNAL, caller_id="ops")
    result = _agent().invoke("Check tonight's energy use at store-7.", ctx=ctx)
    assert result["status"] in (AgentStatus.SUCCESS, AgentStatus.SUCCESS.value)
    # observe -> detect -> stop: three think steps, two tool steps, no setpoint write.
    history = result.get("node_history", [])
    assert history.count("GuardedThinkNode") == 3
    assert history.count("ToolActNode") == 2
    assert "hvac_setpoint_write was not called" in result["thoughts"][-1]
