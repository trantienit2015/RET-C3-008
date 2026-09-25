# RET-C3-008 — Unit tests for the InputValidate initialize node (S-1/S-2).

from framework.schemas.trust_level import TrustLevel

from src.nodes.input_validate_node import InputValidateInitializeNode


def _s(user_input):
    return {
        "user_input": user_input,
        "node_history": [],
        "error_log": [],
        "execution_time": {},
        "correlation_id": "c",
        "caller_trust_level": TrustLevel.INTERNAL.value,
    }


class TestInputValidate:
    def setup_method(self):
        self.node = InputValidateInitializeNode()

    def test_clean_telemetry_passes(self):
        r = self.node.on_initialize(_s('{"store_id": "s1", "equipment": {"hvac_1": [10, 12]}}'))
        assert r["working_memory"]["input_rejected"] is False
        assert r["action_trace"] == []

    def test_rejects_jwt(self):
        r = self.node.on_initialize(_s("telemetry eyJabc.def.ghi embedded"))
        assert r["working_memory"]["input_rejected"] is True

    def test_rejects_credential_json(self):
        r = self.node.on_initialize(_s('{"api_key": "leak", "store_id": "s1"}'))
        assert r["working_memory"]["input_rejected"] is True

    def test_rejects_mynumber(self):
        r = self.node.on_initialize(_s("operator 1234-5678-9012 present"))
        assert r["working_memory"]["input_rejected"] is True

    def test_trust_level_internal(self):
        assert self.node.required_trust_level == TrustLevel.INTERNAL
