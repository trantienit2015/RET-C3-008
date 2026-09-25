# RET-C3-008 — Unit tests for the per-store baseline service.

from src.services.baseline_service import BaselineService


BASELINES = {"store-1": {"hvac_1": {"mean": 10.0, "std": 2.0}}}


class TestBaselineService:
    def setup_method(self):
        self.svc = BaselineService(BASELINES)

    def test_for_store(self):
        assert self.svc.for_store("store-1")["hvac_1"]["mean"] == 10.0

    def test_unknown_store_empty(self):
        assert self.svc.for_store("store-x") == {}

    def test_has_baseline(self):
        assert self.svc.has_baseline("store-1") is True
        assert self.svc.has_baseline("store-x") is False

    def test_equipment_baseline(self):
        assert self.svc.equipment_baseline("store-1", "hvac_1") == {"mean": 10.0, "std": 2.0}
        assert self.svc.equipment_baseline("store-1", "fridge_1") is None
