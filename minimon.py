#!/usr/bin/env python3
import argparse
import asyncio
import json
import re
import socket
import time

import aiohttp
import dns.resolver
from envyaml import EnvYAML
from kafka import KafkaConsumer, KafkaProducer
from kafka.admin import KafkaAdminClient, NewTopic
import psycopg2
import psycopg2.extras
from requests import get
from urllib.parse import urlparse


conf = EnvYAML('conf.yml')
try:
    pgconn = psycopg2.connect(host=conf['postgres.host'],
                              dbname=conf['postgres.dbname'],
                              user=conf['postgres.dbuser'],
                              password=conf['postgres.dbpass'])
    pgconn.autocommit = True
except Exception as e:
    print(f"E: Unable to connect to database! {e}")
topic = conf['kafka.topic']
bootstrap_servers = conf['kafka.bootstrap_servers']
consumer = KafkaConsumer(topic,
                         auto_offset_reset='latest',
                         bootstrap_servers=bootstrap_servers,
                         group_id=conf['kafka.group_id'])
producer = KafkaProducer(bootstrap_servers=bootstrap_servers,
                         value_serializer=lambda x:
                         json.dumps(x).encode('utf-8'))


def init_kafka_topic(topic='test', client_id='test'):
    admin_client = KafkaAdminClient(
        bootstrap_servers=bootstrap_servers,
        client_id=client_id
    )
    topic_list = []
    topic_list.append(NewTopic(name=topic, num_partitions=1,
                      replication_factor=1))
    admin_client.create_topics(new_topics=topic_list, validate_only=False)


def init_postgres():
    with pgconn.cursor() as cur:
        cur.execute("DROP DATABASE IF EXISTS %s", (conf['postgres.dbname'],))
        cur.execute("CREATE DATABASE %s", (conf['postgres.dbname'],))
        # cur.execute("WHERE NOT EXISTS
        #              (SELECT FROM pg_database WHERE = 'mydb')")
        cur.execute(open("schema.sql", "r").read())
        cur.execute(open("data.sql", "r").read())


def test_init():
    init_kafka_topic()


def add_urls(urls_file):
    with pgconn.cursor() as cur:
        sql = "SELECT url_group_id FROM url_group WHERE name = 'unassigned'"
        cur.execute(sql)
        url_group_id = cur.fetchone()[0]
    with open(urls_file) as f:
        lines = f.read().splitlines()
    for url in lines:
        add_url(url_group_id, url)


def add_url(url_group_id, url):
    with pgconn.cursor() as cur:
        cur.execute("select * from url where url = %s", (url,))
        if cur.rowcount == 0:
            print(f"Adding {url}")
            cur.execute("INSERT INTO url (url_group_id, url) VALUES (%s, %s)",
                        (url_group_id, url,))
            # pgconn.commit()


def test_tcp_port(host, port):
    start = time.time()
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1)
    try:
        s.connect((str(host), int(port)))
        s.shutdown(socket.SHUT_RDWR)
        s.close()
        tcp_rsp_time = time.time() - start
    except Exception as e:
        tcp_rsp_time = None
        str(e)
    return tcp_rsp_time


def get_internet_ip():
    ip = get('https://api.ipify.org').text
    return ip


def get_intranet_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip


def get_monitor_ips():
    intranet_ip = get_intranet_ip()
    internet_ip = get_internet_ip()
    monitor_location = f"{intranet_ip}-{internet_ip}"
    str(monitor_location)


def get_events(topic, offset='earliest'):
    consumer = KafkaConsumer(topic, auto_offset_reset=offset)
    for msg in consumer:
        try:
            print(msg)
        except Exception as e:
            print(e)


def get_event_count(topic, offset='earliest'):
    consumer = KafkaConsumer(topic, auto_offset_reset=offset)
    msg_count = 0
    for msg in consumer:
        msg_count += 1
    print(msg_count)


def put_event(topic, msg):
    if not isinstance(msg, dict):
        print("ERROR: Put event not dict!")
        return
    print(msg)
    producer.send(topic, msg)
    producer.flush()


def test_text_contains_string(text, string):
    if string in text:
        code = 0
    else:
        code = 1
    return code


def get_rsp_text_regex_count(regex, text):
    if not regex:
        return
    regexc = re.compile(regex)
    count = len(regexc.findall(text))
    return count


async def get_url(session, url_id, url, rsp_text_regex):
    msg = {}
    msg['url_id'] = url_id
    msg['error'] = None
    msg['rsp_regex_count'] = None
    msg['rsp_status_code'] = None
    msg['http_rsp_time'] = None
    msg['rsp_url'] = None
    msg['dns'] = None
    try:
        async with session.get(url, allow_redirects=True) as rsp:
            dns = get_dns(url)
            start = time.time()
            rsp_text = await rsp.text()
            http_rsp_time = time.time() - start
            regex_count = get_rsp_text_regex_count(rsp_text_regex, rsp_text)
            msg['rsp_regex_count'] = regex_count
            msg['rsp_status_code'] = rsp.status
            msg['http_rsp_time'] = http_rsp_time
            msg['rsp_url'] = str(rsp.url)
            msg['dns'] = dns
    except Exception as e:
        msg['error'] = str(e)
    return msg


def get_dns(url):
    fqdn = urlparse(url).hostname
    dns_start = time.time()
    dns_response = dns.resolver.resolve(fqdn, 'A')
    msg = {}
    dns_time = time.time() - dns_start
    msg['dns_time'] = dns_time
    msg['tcp_times'] = []
    try:
        hosts = {}
        hosts['error'] = None
        for host in dns_response:
            tcp_rsp_time = test_tcp_port(host, 443)
            hosts['host'] = str(host)
            hosts['tcp_rsp_time'] = tcp_rsp_time
            msg['tcp_times'].append(hosts)
    except Exception as e:
        msg['tcp_times'].append(hosts)
        hosts['error'] = str(e)
    return msg


async def check_urls():
    cur = pgconn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM url limit %s", (limit_urls,))
    rows = cur.fetchall()
    timeout = aiohttp.ClientTimeout(total=conf['http_client.timeout'])
    async with aiohttp.ClientSession(timeout=timeout) as session:
        tasks = []
        for row in rows:
            tasks.append(asyncio.ensure_future(get_url(session,
                                                       row['url_id'],
                                                       row['url'],
                                                       row['rsp_text_regex'])))
        msgs = await asyncio.gather(*tasks)
        for msg in msgs:
            try:
                put_event(topic, msg)
            except Exception as e:
                print(f"ERROR: Push event failed! {e}")


def main():
    parser = argparse.ArgumentParser(description='Simple monitor service')
    parser.add_argument('-a', '--add-urls-file', required=False, type=str,
                        help='file of urls, line by line, to add')
    parser.add_argument('-L', '--limit-urls', required=False, type=str,
                        default="all",
                        help='Limit the number of urls to check.')
    parser.add_argument('-s', '--service', action='store_true',
                        help='Run as a service')
    parser.add_argument('-T', '--test-init', action='store_true',
                        help='Initialize test')
    parser.add_argument('--test-kafka', action='store_true',
                        help='Initialize test')
    parser.add_argument('-G', '--get-events', action='store_true',
                        help='Get/consume events from earliest')
    args = parser.parse_args()
    global limit_urls
    limit_urls = args.limit_urls
    if args.test_kafka:
        put_event(topic, conf['kafka.test_topic'])
        return
    if args.get_events:
        get_events(topic)
        return
    if args.test_init:
        test_init()
        return
    if args.add_urls_file:
        add_urls(args.add_urls_file)
        return
    if args.service:
        while True:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(check_urls())
            time.sleep(conf['check_interval'])


if __name__ == "__main__":
    main()
