from uuid import uuid4

import pytest
from testcontainers.community.kafka import KafkaContainer
from testcontainers.community.postgres import PostgresContainer

import minimon


pytestmark = pytest.mark.integration


def test_kafka_event_is_stored_in_postgres():
    postgres = PostgresContainer(
        image="postgres:17-alpine",
        username="minimon",
        password="minimon",
        dbname="minimon",
    )
    kafka = KafkaContainer(
        image="confluentinc/cp-kafka:7.6.0"
    ).with_kraft()

    with postgres, kafka:
        config = minimon.AppConfig(
            postgres=minimon.PostgresConfig(
                host=postgres.get_container_host_ip(),
                port=int(postgres.get_exposed_port(5432)),
                dbname=postgres.dbname,
                user=postgres.username,
                password=postgres.password,
            ),
            kafka=minimon.KafkaConfig(
                bootstrap_servers=kafka.get_bootstrap_server(),
                topic="minimon-integration",
                group_id=f"minimon-integration-{uuid4()}",
            ),
        )

        connection = minimon.create_pgconn(config)
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    (minimon.BASE_DIR / "schema.sql").read_text(encoding="utf-8")
                )
                cursor.execute(
                    "INSERT INTO url_group (name) VALUES (%s) "
                    "RETURNING url_group_id",
                    ("integration",),
                )
                url_group_id = cursor.fetchone()[0]
            minimon.add_url(
                connection,
                url_group_id,
                "https://example.com",
                "Example Domain",
            )
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT url_id FROM url WHERE url = %s",
                    ("https://example.com",),
                )
                url_id = cursor.fetchone()[0]
        finally:
            connection.close()

        minimon.init_kafka_topic(config)
        minimon.publish_events(config, [{
            "url_id": url_id,
            "dns": {"dns_time": 0.01, "tcp_times": [], "error": None},
            "error": None,
            "http_rsp_time": 0.2,
            "rsp_regex_count": 1,
            "rsp_status_code": 200,
        }])

        assert minimon.kafka_to_pg(
            config,
            offset="earliest",
            max_messages=1,
            timeout_ms=15_000,
        ) == 1

        connection = minimon.create_pgconn(config)
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """SELECT url_id, dns, http_rsp_time, rsp_regex_count,
                              rsp_status_code
                       FROM url_history"""
                )
                stored = cursor.fetchone()
        finally:
            connection.close()

        assert stored is not None
        assert stored[0] == url_id
        assert stored[1] == {
            "dns_time": 0.01,
            "tcp_times": [],
            "error": None,
        }
        assert float(stored[2]) == 0.2
        assert stored[3:] == (1, 200)
