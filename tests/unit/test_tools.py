# RET-C3-008 — Unit tests for energy tools (pure functions).

from src.tools import energy_tools as et


class TestObserveTelemetry:
    def test_normalizes_equipment(self):
        window = {"equipment": {"hvac_1": [10.0, 12.0, 40.0]}, "outdoor_temp": 30}
        frame = et.observe_telemetry("store-1", window)
        assert frame["store_id"] == "store-1"
        assert frame["equipment"]["hvac_1"]["last"] == 40.0
        assert frame["equipment"]["hvac_1"]["n"] == 3

    def test_empty_window(self):
        frame = et.observe_telemetry("store-1", None)
        assert frame["equipment"] == {}


class TestDetectAnomaly:
    def test_flags_out_of_band(self):
        telemetry = {"equipment": {"hvac_1": {"last": 100.0}}}
        baseline = {"hvac_1": {"mean": 10.0, "std": 2.0}}
        anomalies = et.detect_anomaly(telemetry, baseline)
        assert len(anomalies) == 1
        assert anomalies[0]["classification"] == "equipment_fault"

    def test_no_anomaly_in_band(self):
        telemetry = {"equipment": {"hvac_1": {"last": 11.0}}}
        baseline = {"hvac_1": {"mean": 10.0, "std": 2.0}}
        assert et.detect_anomaly(telemetry, baseline) == []

    def test_no_baseline_skips(self):
        telemetry = {"equipment": {"hvac_1": {"last": 100.0}}}
        assert et.detect_anomaly(telemetry, {}) == []


class TestActTools:
    def test_ticket(self):
        r = et.dispatch_maintenance_ticket("store-1", "hvac_1", "overheating")
        assert r["dispatched"] is True and r["action"] == "ticket"

    def test_alert(self):
        r = et.send_staff_alert("store-1", "check refrigeration")
        assert r["sent"] is True

    def test_hvac_write_bms_available(self):
        r = et.hvac_setpoint_write("store-1", "hvac_1", 24.0, bms_available=True)
        assert r["written"] is True and r["setpoint"] == 24.0

    def test_hvac_write_degraded_fallback(self):
        r = et.hvac_setpoint_write("store-1", "hvac_1", 24.0, bms_available=False)
        assert r["written"] is False and r["fallback"] == "ticket_only"


class TestVerify:
    def test_in_band(self):
        r = et.verify_return_to_baseline("store-1", "hvac_1", [10.2, 10.1], baseline_mean=10.0)
        assert r["verification"] == "in_band"

    def test_out_of_band(self):
        r = et.verify_return_to_baseline("store-1", "hvac_1", [20.0, 21.0], baseline_mean=10.0)
        assert r["verification"] == "out_of_band"

    def test_pending_insufficient(self):
        r = et.verify_return_to_baseline("store-1", "hvac_1", [10.0], baseline_mean=10.0)
        assert r["verification"] == "pending"


class TestToolMetadata:
    def test_all_tools_named(self):
        for name, fn in et.TOOL_REGISTRY.items():
            assert getattr(fn, "name", None) == name

    def test_std_dev(self):
        assert et.std_dev([2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0]) > 0
