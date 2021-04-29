#!/usr/bin/env python3
from kafka import KafkaConsumer, KafkaProducer, TopicPartition
from kafka.admin import KafkaAdminClient, NewTopic
import asyncio
import aiohttp
import time
from envyaml import EnvYAML
import json
import socket
import dns.resolver
from urllib.parse import urlparse
from requests import get
import psycopg2
import psycopg2.extras
import re
import argparse
from html import escape


conf = EnvYAML('conf.yml')
topic = conf['kafka.topic']
bootstrap_servers = conf['kafka.bootstrap_servers']
pgconn = psycopg2.connect(host=conf['postgres.host'],
                          dbname=conf['postgres.dbname'],
                          user=conf['postgres.dbuser'],
                          password=conf['postgres.dbpass'])
producer = KafkaProducer(bootstrap_servers=bootstrap_servers,
                         value_serializer=lambda x: 
                         json.dumps(x).encode('utf-8'))
consumer = KafkaConsumer(topic, bootstrap_servers=bootstrap_servers, auto_offset_reset='latest')


def init_kafka_topic(topic='test', client_id='test'):
    admin_client = KafkaAdminClient(
        bootstrap_servers=bootstrap_servers, 
        client_id=client_id
    )
    topic_list = []
    topic_list.append(NewTopic(name=topic, num_partitions=1, replication_factor=1))
    admin_client.create_topics(new_topics=topic_list, validate_only=False)


def init_postgres():
    cur.execute("DROP DATABASE IF EXISTS" %s, (conf['postgres.dbname'],))
    cur.execute("CREATE DATABASE" %s, (conf['postgres.dbname'],))
    # cur.execute("WHERE NOT EXISTS (SELECT FROM pg_database WHERE = 'mydb')")
    cur.execute(open("schema.sql", "r").read())


def test_init():
    init_kafka_topic()


def add_urls(urls_file):
    with pgconn.cursor() as cur:
        sql = "select url_group_id from url_group where name = 'unassigned'"
        cur.execute(sql)
        url_group_id = cur.fetchone()[0]
    with open(urls_file) as f:
        # lines = f.readlines().strip()
        lines = f.read().splitlines()
    for url in lines:
        add_url(url_group_id, url)


def add_url(url_group_id, url):
    with pgconn.cursor() as cur:
        # https://www.psycopg.org/docs/cursor.html#cursor.copy_from
        cur.execute("select * from url where url = %s", (url,))
        if cur.rowcount == 0:
            print(f"Adding {url}")
            cur.execute("INSERT INTO url (url_group_id, url) VALUES (%s, %s)", (url_group_id, url,))
            pgconn.commit()


def test_tcp_port(host, port):
    start = time.time()
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1)
    address = (host, port)
    try:
        s.connect((str(host), int(port)))
        s.shutdown(socket.SHUT_RDWR)
        s.close()
        tcp_rsp_time = time.time() - start
    except Exception as e:
        tcp_rsp_time = None 
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
    monitor_id = f"{intranet_ip}-{internet_ip}"


def get_events(topic, offset='earliest'):
    consumer = KafkaConsumer(topic, auto_offset_reset=offset)
    for msg in consumer:
        try:
            print(msg)
        except Exception as e:
            print(e)


def get_event_count(topic, offset='earliest'):
    consumer = KafkaConsumer(topic, auto_offset_reset=offset)  # earliest/latest
    msg_count = 0
    for msg in consumer:
        count += 1
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


async def get_url(session, url_id, url, rsp_text_regex ):
    r = {} 
    r['url_id'] = url_id
    try:
        async with session.get(url, allow_redirects=True) as rsp:
            dns = get_dns(url)
            start = time.time()
            rsp_text = await rsp.text()
            rsp_time = time.time() - start
            regex_count = get_rsp_text_regex_count(rsp_text_regex, rsp_text)
            r['error'] = None 
            r['rsp_regex_count'] = regex_count 
            r['rsp_status_code'] =rsp.status 
            r['rsp_time'] = rsp_time
            r['rsp_url'] =str(rsp.url)
            r['dns'] = dns
            return r 
    except Exception as e:
        r['error'] = str(e)
        r['rsp_regex_count'] = None 
        r['rsp_status_code'] = None
        r['rsp_time'] = None
        r['rsp_url'] = None
        r['dns'] = None 
        return r 


def get_dns(url):
    fqdn = urlparse(url).hostname
    dns_start = time.time()
    dns_response = dns.resolver.resolve(fqdn, 'A')
    r = {}
    dns_time = time.time() - dns_start
    r['dns_time'] = dns_time
    r['tcp_times'] = []
    try:
        for host in dns_response:
            tcp_rsp_time = test_tcp_port(host, 443)
            hosts = {}
            hosts['host'] = str(host)
            hosts['tcp_rsp_time'] = tcp_rsp_time
            r['tcp_times'].append(hosts)
        return r 
    except Exception as e:
        return str(e)


async def check_urls():
    cur = pgconn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    # sql = "SELECT * FROM url limit 3"
    sql = f"SELECT * FROM url limit {limit_urls}"
    cur.execute(sql)
    rows = cur.fetchall()
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        tasks = []
        for row in rows:
            tasks.append(asyncio.ensure_future(get_url(session, row['url_id'], row['url'], row['rsp_text_regex'])))
        rsps = await asyncio.gather(*tasks)
        for rsp in rsps:
            try:
                put_event(topic, rsp)
            except Exception as e:
                print(f"ERROR: Push event failed! {e}")


def main():
    parser = argparse.ArgumentParser(description='Simple monitor service')
    parser.add_argument('-a', '--add-urls-file', required=False, type=str,
                        help='file of urls, line by line, to add')
    parser.add_argument('-L', '--limit-urls', required=False, type=str, default="all",
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
        put_event(topic, "foobar")
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
            time.sleep(30)
            time.sleep(conf['check_interval'])


if __name__ == "__main__":
    main() 
