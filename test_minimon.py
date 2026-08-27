import argparse
import asyncio
from datetime import UTC
from types import SimpleNamespace

import aiohttp
import pytest

import minimon


def write_config(path, password="$MINIMON_TEST_PASSWORD"):
    path.write_text(
        f"""check_interval: 15
http_client:
  timeout: 10
kafka:
  bootstrap_servers: localhost:9092
  group_id: minimon-test
  topic: checks
postgres:
  dbname: minimon
  dbpass: {password}
  dbuser: postgres
  host: localhost
  port: 5433
""",
        encoding="utf-8",
    )


def test_load_config_expands_environment(tmp_path, monkeypatch):
    config_path = tmp_path / "conf.yml"
    write_config(config_path)
    monkeypatch.setenv("MINIMON_TEST_PASSWORD", "secret")

    config = minimon.load_config(config_path)

    assert config.postgres.password == "secret"
    assert config.postgres.port == 5433
    assert config.kafka.topic == "checks"
    assert config.http_timeout == 10
    assert config.check_interval == 15


def test_load_config_rejects_missing_environment_variable(tmp_path, monkeypatch):
    config_path = tmp_path / "conf.yml"
    write_config(config_path)
    monkeypatch.delenv("MINIMON_TEST_PASSWORD", raising=False)

    with pytest.raises(minimon.ConfigurationError, match="MINIMON_TEST_PASSWORD"):
        minimon.load_config(config_path)


def test_load_config_rejects_invalid_numeric_value(tmp_path, monkeypatch):
    config_path = tmp_path / "conf.yml"
    write_config(config_path)
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace("port: 5433", "port: bad"),
        encoding="utf-8",
    )
    monkeypatch.setenv("MINIMON_TEST_PASSWORD", "secret")

    with pytest.raises(minimon.ConfigurationError, match="must be numeric"):
        minimon.load_config(config_path)


def test_event_from_message_preserves_url_and_uses_utc():
    message = SimpleNamespace(
        timestamp=1_700_000_000_000,
        value={
            "url_id": 42,
            "dns": {"dns_time": 0.1},
            "error": None,
            "http_rsp_time": 0.25,
            "rsp_regex_count": 2,
            "rsp_status_code": 200,
        },
    )

    event = minimon.event_from_message(message)

    assert event["url_id"] == 42
    assert event["event_timestamp"].tzinfo is UTC
    assert event["rsp_status_code"] == 200


class FakeCursor:
    def __init__(self, fetchone=None):
        self.fetchone_value = fetchone
        self.executions = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, query, parameters=()):
        self.executions.append((query, parameters))

    def fetchone(self):
        return self.fetchone_value


class FakeConnection:
    def __init__(self, cursor):
        self.cursor_instance = cursor

    def cursor(self, **kwargs):
        return self.cursor_instance


def test_add_url_inserts_missing_url():
    cursor = FakeCursor(fetchone=None)
    connection = FakeConnection(cursor)

    minimon.add_url(connection, 7, "https://example.com", "Example")

    assert cursor.executions[0][1] == ("https://example.com",)
    assert cursor.executions[1][1] == (
        7,
        "https://example.com",
        "Example",
    )


def test_insert_event_includes_url_id():
    cursor = FakeCursor()
    connection = FakeConnection(cursor)
    event = {
        "url_id": 8,
        "dns": "{}",
        "error": None,
        "event_timestamp": object(),
        "http_rsp_time": 0.2,
        "rsp_regex_count": 1,
        "rsp_status_code": 200,
    }

    minimon.insert_event(connection, event)

    assert cursor.executions[0][1][0] == 8
    assert len(cursor.executions[0][1]) == 7


class FakeResponse:
    status = 200
    url = "https://example.com/final"

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def text(self, **kwargs):
        return "Example response with Example twice"


class SuccessfulSession:
    def get(self, url, **kwargs):
        return FakeResponse()


class FailedSession:
    def get(self, url, **kwargs):
        raise aiohttp.ClientConnectionError("connection refused")


def test_get_url_builds_success_event(monkeypatch):
    dns_result = {"dns_time": 0.01, "tcp_times": [], "error": None}

    async def fake_resolve_dns(url):
        return dns_result

    monkeypatch.setattr(minimon, "resolve_dns", fake_resolve_dns)

    event = asyncio.run(minimon.get_url(
        SuccessfulSession(), 3, "https://example.com", "Example"
    ))

    assert event["url_id"] == 3
    assert event["rsp_status_code"] == 200
    assert event["rsp_regex_count"] == 2
    assert event["rsp_url"] == "https://example.com/final"
    assert event["http_rsp_time"] >= 0
    assert event["dns"] == dns_result


def test_get_url_returns_failure_event(monkeypatch):
    async def fake_resolve_dns(url):
        return {"dns_time": 0.01, "tcp_times": [], "error": None}

    monkeypatch.setattr(minimon, "resolve_dns", fake_resolve_dns)

    event = asyncio.run(minimon.get_url(
        FailedSession(), 4, "https://example.com", None
    ))

    assert event["url_id"] == 4
    assert event["rsp_status_code"] is None
    assert event["http_rsp_time"] is None
    assert event["error"] == "connection refused"


def test_publish_events_skips_empty_batch(monkeypatch):
    def unexpected_producer(config):
        raise AssertionError("producer should not be created")

    monkeypatch.setattr(minimon, "create_kafka_producer", unexpected_producer)

    minimon.publish_events(object(), [])


@pytest.mark.parametrize("value", ["0", "-1"])
def test_positive_int_rejects_non_positive_values(value):
    with pytest.raises(argparse.ArgumentTypeError, match="at least 1"):
        minimon.positive_int(value)
