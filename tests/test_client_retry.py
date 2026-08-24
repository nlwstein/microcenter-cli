"""Retry/rate-limit logic tests. Network calls (curl_cffi.requests.get) and
time.sleep are monkeypatched out entirely -- these test the control flow in
client._request, not real HTTP behavior."""

from __future__ import annotations

import pytest

from microcenter_cli import client as client_module
from microcenter_cli import session as session_module
from microcenter_cli.client import (
    MicroCenterBlockedError,
    MicroCenterClient,
    MicroCenterError,
)
from microcenter_cli.config import Config


class FakeResponse:
    def __init__(self, status_code: int, text: str = "<html>ok</html>"):
        self.status_code = status_code
        self.text = text

    def raise_for_status(self):
        if self.status_code >= 400:
            raise client_module.curl_requests.exceptions.HTTPError(str(self.status_code))


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(
        session_module,
        "load",
        lambda: session_module.Session(cookies={"cf_clearance": "x"}, saved_at=0),
    )
    monkeypatch.setattr("time.sleep", lambda _seconds: None)  # skip real backoff/rate-limit waits
    cfg = Config(max_retries=3, retry_backoff_seconds=0, min_request_interval_seconds=0)
    return MicroCenterClient(cfg)


def test_succeeds_first_try(client, monkeypatch):
    calls = []
    monkeypatch.setattr(
        client_module.curl_requests, "get", lambda *a, **kw: calls.append(1) or FakeResponse(200)
    )
    resp = client._request("http://x", "121")
    assert resp.status_code == 200
    assert len(calls) == 1


def test_retries_transient_network_error_then_succeeds(client, monkeypatch):
    attempts = {"n": 0}

    def fake_get(*a, **kw):
        attempts["n"] += 1
        if attempts["n"] < 2:
            raise client_module.CurlError("boom")
        return FakeResponse(200)

    monkeypatch.setattr(client_module.curl_requests, "get", fake_get)
    resp = client._request("http://x", "121")
    assert resp.status_code == 200
    assert attempts["n"] == 2


def test_gives_up_after_max_retries(client, monkeypatch):
    def fake_get(*a, **kw):
        raise client_module.CurlError("still broken")

    monkeypatch.setattr(client_module.curl_requests, "get", fake_get)
    with pytest.raises(MicroCenterError):
        client._request("http://x", "121")


def test_retries_5xx_then_succeeds(client, monkeypatch):
    attempts = {"n": 0}

    def fake_get(*a, **kw):
        attempts["n"] += 1
        return FakeResponse(500) if attempts["n"] < 2 else FakeResponse(200)

    monkeypatch.setattr(client_module.curl_requests, "get", fake_get)
    resp = client._request("http://x", "121")
    assert resp.status_code == 200
    assert attempts["n"] == 2


def test_403_is_not_retried(client, monkeypatch):
    calls = []
    monkeypatch.setattr(
        client_module.curl_requests, "get", lambda *a, **kw: calls.append(1) or FakeResponse(403)
    )
    with pytest.raises(MicroCenterBlockedError):
        client._get("http://x", "121")
    assert len(calls) == 1  # no retry burned against a dead session


def test_no_session_raises_immediately(monkeypatch):
    monkeypatch.setattr(session_module, "load", lambda: session_module.Session())
    with pytest.raises(MicroCenterBlockedError):
        MicroCenterClient(Config())
