#!/usr/bin/env python3
import argparse
import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import re
import socket
import sys
import time
from urllib.parse import urlparse

import aiohttp
import dns.resolver
import psycopg2
from psycopg2 import sql
import psycopg2.extras
import yaml


BASE_DIR = Path(__file__).resolve().parent
ENV_VAR_PATTERN = re.compile(r"\$(?:{(?P<braced>[A-Za-z_][A-Za-z0-9_]*)}|"
                             r"(?P<plain>[A-Za-z_][A-Za-z0-9_]*))")


class ConfigurationError(ValueError):
    pass


@dataclass(frozen=True)
class PostgresConfig:
    host: str
    dbname: str
    user: str
    password: str
    port: int = 5432


@dataclass(frozen=True)
class KafkaConfig:
    bootstrap_servers: str | list[str]
    topic: str
    group_id: str
    test_topic: str = "test"


@dataclass(frozen=True)
class AppConfig:
    postgres: PostgresConfig
    kafka: KafkaConfig
    http_timeout: float = 30
    check_interval: float = 30


def _expand_environment(value):
    if isinstance(value, dict):
        return {key: _expand_environment(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_expand_environment(item) for item in value]
    if not isinstance(value, str):
        return value

    def replace(match):
        name = match.group("braced") or match.group("plain")
        try:
            return os.environ[name]
        except KeyError as exc:
            raise ConfigurationError(
                f"Environment variable {name} is required by the configuration"
            ) from exc

    return ENV_VAR_PATTERN.sub(replace, value)


def _required(section, key, section_name):
    try:
        value = section[key]
    except (KeyError, TypeError) as exc:
        raise ConfigurationError(
            f"Missing configuration value: {section_name}.{key}"
        ) from exc
    if value in (None, ""):
        raise ConfigurationError(
            f"Configuration value cannot be empty: {section_name}.{key}"
        )
    return value


def _positive_number(value, name, converter):
    try:
        parsed = converter(value)
    except (TypeError, ValueError) as exc:
        raise ConfigurationError(
            f"Configuration value must be numeric: {name}"
        ) from exc
    if parsed <= 0:
        raise ConfigurationError(
            f"Configuration value must be greater than zero: {name}"
        )
    return parsed


def load_config(path="conf.yml"):
    config_path = Path(path)
    try:
        with config_path.open(encoding="utf-8") as config_file:
            raw = yaml.safe_load(config_file)
    except yaml.YAMLError as exc:
        raise ConfigurationError(f"Invalid YAML in {config_path}: {exc}") from exc

    if not isinstance(raw, dict):
        raise ConfigurationError(f"Configuration in {config_path} must be a mapping")

    raw = _expand_environment(raw)
    postgres = _required(raw, "postgres", "configuration")
    kafka = _required(raw, "kafka", "configuration")
    http_client = raw.get("http_client", {})

    return AppConfig(
        postgres=PostgresConfig(
            host=str(_required(postgres, "host", "postgres")),
            port=_positive_number(
                postgres.get("port", 5432), "postgres.port", int
            ),
            dbname=str(_required(postgres, "dbname", "postgres")),
            user=str(_required(postgres, "dbuser", "postgres")),
            password=str(_required(postgres, "dbpass", "postgres")),
        ),
        kafka=KafkaConfig(
            bootstrap_servers=_required(
                kafka, "bootstrap_servers", "kafka"
            ),
            topic=str(_required(kafka, "topic", "kafka")),
            group_id=str(_required(kafka, "group_id", "kafka")),
            test_topic=str(kafka.get("test_topic", "test")),
        ),
        http_timeout=_positive_number(
            http_client.get("timeout", 30), "http_client.timeout", float
        ),
        check_interval=_positive_number(
            raw.get("check_interval", 30), "check_interval", float
        ),
    )


def create_pgconn(config, dbname=None, autocommit=True):
    pgconn = psycopg2.connect(
        host=config.postgres.host,
        port=config.postgres.port,
        dbname=dbname or config.postgres.dbname,
        user=config.postgres.user,
        password=config.postgres.password,
    )
    pgconn.autocommit = autocommit
    return pgconn


def create_kafka_consumer(config, offset="earliest"):
    from kafka import KafkaConsumer

    return KafkaConsumer(
        config.kafka.topic,
        auto_offset_reset=offset,
        bootstrap_servers=config.kafka.bootstrap_servers,
        value_deserializer=lambda value: json.loads(value.decode("utf-8")),
        group_id=config.kafka.group_id,
    )


def create_kafka_producer(config):
    from kafka import KafkaProducer

    return KafkaProducer(
        bootstrap_servers=config.kafka.bootstrap_servers,
        value_serializer=lambda value: json.dumps(value).encode("utf-8"),
    )


def init_kafka_topic(config):
    from kafka.admin import KafkaAdminClient, NewTopic

    admin_client = KafkaAdminClient(
        bootstrap_servers=config.kafka.bootstrap_servers,
        client_id="minimon-admin",
    )
    try:
        if config.kafka.topic not in admin_client.list_topics():
            admin_client.create_topics(new_topics=[
                NewTopic(
                    name=config.kafka.topic,
                    num_partitions=1,
                    replication_factor=1,
                )
            ])
    finally:
        admin_client.close()


def init_postgres(config):
    maintenance_conn = create_pgconn(config, dbname="template1")
    try:
        with maintenance_conn.cursor() as cursor:
            database = sql.Identifier(config.postgres.dbname)
            cursor.execute(
                sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(database)
            )
            cursor.execute(sql.SQL("CREATE DATABASE {}").format(database))
    finally:
        maintenance_conn.close()

    pgconn = create_pgconn(config)
    try:
        with pgconn.cursor() as cursor:
            cursor.execute((BASE_DIR / "schema.sql").read_text(encoding="utf-8"))
            cursor.execute("INSERT INTO url_group (name) VALUES (%s)",
                           ("unassigned",))
        seed_urls(pgconn, BASE_DIR / "seed-url.csv")
    finally:
        pgconn.close()


def seed_urls(pgconn, urls_file):
    for line in Path(urls_file).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        url, separator, rsp_regex = line.partition("|")
        add_url(pgconn, 1, url.strip(), rsp_regex if separator else None)


def add_urls(pgconn, urls_file):
    with pgconn.cursor() as cursor:
        cursor.execute(
            "SELECT url_group_id FROM url_group WHERE name = %s",
            ("unassigned",),
        )
        row = cursor.fetchone()
    if row is None:
        raise RuntimeError("The unassigned URL group does not exist")

    for url in Path(urls_file).read_text(encoding="utf-8").splitlines():
        url = url.strip()
        if url:
            add_url(pgconn, row[0], url)


def add_url(pgconn, url_group_id, url, rsp_regex=None):
    with pgconn.cursor() as cursor:
        cursor.execute("SELECT 1 FROM url WHERE url = %s", (url,))
        if cursor.fetchone() is None:
            cursor.execute(
                """INSERT INTO url (url_group_id, url, rsp_regex)
                   VALUES (%s, %s, %s)""",
                (url_group_id, url, rsp_regex),
            )


def event_from_message(message):
    value = message.value
    return {
        "url_id": value["url_id"],
        "dns": json.dumps(value.get("dns")),
        "error": value.get("error"),
        "event_timestamp": datetime.fromtimestamp(
            message.timestamp / 1000, tz=UTC
        ),
        "http_rsp_time": value.get("http_rsp_time"),
        "rsp_regex_count": value.get("rsp_regex_count"),
        "rsp_status_code": value.get("rsp_status_code"),
    }


def insert_event(pgconn, event):
    with pgconn.cursor() as cursor:
        cursor.execute(
            """INSERT INTO url_history
               (url_id, dns, error, event_timestamp, http_rsp_time,
                rsp_regex_count, rsp_status_code)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (
                event["url_id"],
                event["dns"],
                event["error"],
                event["event_timestamp"],
                event["http_rsp_time"],
                event["rsp_regex_count"],
                event["rsp_status_code"],
            ),
        )


def kafka_to_pg(config, offset="earliest"):
    consumer = create_kafka_consumer(config, offset)
    pgconn = create_pgconn(config, autocommit=False)
    try:
        for message in consumer:
            try:
                insert_event(pgconn, event_from_message(message))
                pgconn.commit()
            except (KeyError, TypeError, ValueError, psycopg2.Error) as exc:
                pgconn.rollback()
                print(f"Unable to store Kafka event: {exc}", file=sys.stderr)
    finally:
        consumer.close()
        pgconn.close()


def get_events(config, offset="earliest"):
    consumer = create_kafka_consumer(config, offset)
    try:
        for message in consumer:
            print(message.value)
    finally:
        consumer.close()


def get_tcp_response_time(host, port, timeout=1):
    start = time.perf_counter()
    try:
        with socket.create_connection((str(host), int(port)), timeout=timeout):
            return time.perf_counter() - start
    except OSError:
        return None


def get_dns(url):
    parsed_url = urlparse(url)
    if not parsed_url.hostname:
        raise ValueError(f"URL does not contain a hostname: {url}")

    dns_start = time.perf_counter()
    resolver = dns.resolver.Resolver()
    resolver.nameservers = ["8.8.8.8"]
    try:
        answers = resolver.resolve(parsed_url.hostname, "A")
    except dns.exception.DNSException as exc:
        return {
            "dns_time": time.perf_counter() - dns_start,
            "tcp_times": [],
            "error": str(exc),
        }

    port = parsed_url.port or (443 if parsed_url.scheme == "https" else 80)
    result = {
        "dns_time": time.perf_counter() - dns_start,
        "tcp_times": [],
        "error": None,
    }
    for answer in answers:
        host = str(answer)
        tcp_time = get_tcp_response_time(host, port)
        result["tcp_times"].append({
            "host": host,
            "tcp_rsp_time": tcp_time,
            "error": None if tcp_time is not None else "TCP connection failed",
        })
    return result


def get_rsp_regex_count(regex, text):
    if not regex:
        return None
    return len(re.findall(regex, text))


async def get_url(session, url_id, url, rsp_regex):
    event = {
        "url_id": url_id,
        "error": None,
        "rsp_regex_count": None,
        "rsp_status_code": None,
        "http_rsp_time": None,
        "rsp_url": None,
        "dns": None,
    }
    dns_task = asyncio.create_task(resolve_dns(url))
    start = time.perf_counter()
    try:
        async with session.get(url, allow_redirects=True) as response:
            response_text = await response.text(errors="replace")
            event["rsp_regex_count"] = get_rsp_regex_count(
                rsp_regex, response_text
            )
            event["rsp_status_code"] = response.status
            event["http_rsp_time"] = time.perf_counter() - start
            event["rsp_url"] = str(response.url)
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError, re.error) as exc:
        event["error"] = str(exc)

    try:
        event["dns"] = await dns_task
    except Exception as exc:
        event["dns"] = {"dns_time": None, "tcp_times": [], "error": str(exc)}
    return event


async def resolve_dns(url):
    return await asyncio.to_thread(get_dns, url)


def fetch_urls(config, limit=None):
    pgconn = create_pgconn(config)
    try:
        with pgconn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cursor:
            query = "SELECT url_id, url, rsp_regex FROM url ORDER BY url_id"
            parameters = ()
            if limit is not None:
                query += " LIMIT %s"
                parameters = (limit,)
            cursor.execute(query, parameters)
            return cursor.fetchall()
    finally:
        pgconn.close()


def publish_events(config, events):
    if not events:
        return
    producer = create_kafka_producer(config)
    try:
        for event in events:
            producer.send(config.kafka.topic, event).get(timeout=10)
        producer.flush()
    finally:
        producer.close()


async def check_urls(config, limit=None):
    rows = await asyncio.to_thread(fetch_urls, config, limit)
    timeout = aiohttp.ClientTimeout(total=config.http_timeout)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        events = await asyncio.gather(*(
            get_url(session, row["url_id"], row["url"], row["rsp_regex"])
            for row in rows
        ))
    await asyncio.to_thread(publish_events, config, events)
    return events


async def run_service(config, limit=None):
    while True:
        await check_urls(config, limit)
        await asyncio.sleep(config.check_interval)


def positive_int(value):
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return parsed


def build_parser():
    parser = argparse.ArgumentParser(description="Simple monitor service")
    parser.add_argument(
        "-c", "--config", default="conf.yml", help="configuration file"
    )
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument(
        "-a", "--add-urls-file", metavar="FILE",
        help="add URLs from a file, one per line",
    )
    actions.add_argument(
        "-i", "--init-postgres", action="store_true",
        help="delete, recreate, and populate the database",
    )
    actions.add_argument(
        "-I", "--init-kafka-topic", action="store_true",
        help="create the Kafka topic if it does not exist",
    )
    actions.add_argument(
        "-k", "--kafka-to-pg", action="store_true",
        help="consume Kafka URL events and store them in PostgreSQL",
    )
    actions.add_argument(
        "-g", "--get-events", action="store_true",
        help="print events from the earliest available offset",
    )
    actions.add_argument(
        "-s", "--service", action="store_true",
        help="continuously check configured URLs",
    )
    actions.add_argument(
        "--once", action="store_true", help="check configured URLs once"
    )
    actions.add_argument(
        "--test-kafka", action="store_true", help="publish a test event"
    )
    parser.add_argument(
        "-l", "--limit-urls", type=positive_int,
        help="maximum number of URLs to check",
    )
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not any((
        args.add_urls_file,
        args.init_postgres,
        args.init_kafka_topic,
        args.kafka_to_pg,
        args.get_events,
        args.service,
        args.once,
        args.test_kafka,
    )):
        parser.print_help()
        return 0

    try:
        config = load_config(args.config)
        if args.init_postgres:
            init_postgres(config)
        elif args.init_kafka_topic:
            init_kafka_topic(config)
        elif args.kafka_to_pg:
            kafka_to_pg(config, offset="latest")
        elif args.get_events:
            get_events(config)
        elif args.add_urls_file:
            pgconn = create_pgconn(config)
            try:
                add_urls(pgconn, args.add_urls_file)
            finally:
                pgconn.close()
        elif args.service:
            asyncio.run(run_service(config, args.limit_urls))
        elif args.once:
            asyncio.run(check_urls(config, args.limit_urls))
        elif args.test_kafka:
            publish_events(config, [{"test": config.kafka.test_topic}])
    except Exception as exc:
        print(f"minimon: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
