import os

import pytest

from property_error_service import InfraiClient, MaintenanceRequest, process_request


class Reply:
    status_code = 200
    headers = {}

    def json(self):
        return {"ok": True, "data": {"event_id": "evt-1"}, "error": None, "metadata": {}}


class Session:
    def __init__(self):
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return Reply()


class RateLimitedSession(Session):
    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        if len(self.calls) == 1:
            return type("RateReply", (), {"status_code": 429, "headers": {"Retry-After": "0"}, "json": lambda self: {"ok": False, "error": {"code": "BUSY"}}})()
        return Reply()


def test_blank_summary_is_captured_and_not_saved(monkeypatch):
    monkeypatch.setenv("INFRAI_API_KEY", "test-key")
    session = Session()
    saved = []
    with pytest.raises(ValueError, match="summary"):
        process_request(MaintenanceRequest("mr-1", "p-1", "t-1", "  "), saved.append, InfraiClient(session))
    assert saved == []
    assert session.calls[0][0] == "POST"
    assert session.calls[0][1].endswith("/v1/errors/capture")
    assert session.calls[0][2]["json"]["fingerprint"] == ["maintenance_request", "p-1"]


def test_capture_retries_a_rate_limit(monkeypatch):
    monkeypatch.setenv("INFRAI_API_KEY", "test-key")
    session = RateLimitedSession()
    assert InfraiClient(session).capture({"message": "x"}) == {"event_id": "evt-1"}
    assert len(session.calls) == 2
