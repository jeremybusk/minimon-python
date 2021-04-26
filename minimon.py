#!/usr/bin/env python3
from kafka import KafkaConsumer, KafkaProducer, TopicPartition
import asyncio
import aiohttp
import time
import yaml
from envyaml import EnvYAML
import requests
import json
import time
import socket
import dns.resolver
from urllib.parse import urlparse
from requests import get
import psycopg2
import psycopg2.extras
from bs4 import BeautifulSoup
import re
from html import escape
# urlibpars
# urllib.parse

# print(env['project.name'])
conf = EnvYAML('conf.yml')
kafka_topic = conf['kafka.topic']
kafka_socket = conf['kafka.socket']



pgconn = psycopg2.connect(host=conf['postgres.host'],
                          dbname=conf['postgres.dbname'],
                          user=conf['postgres.dbuser'],
                          password=conf['postgres.dbpass'])


def test_text_contains_regexc(regexc, text):
    code = 1
    match = regexc.search(text)
    # r'<title[^>]*>([^<]+)</title>'
    # match = re.search(pattern, string)
    if match:
        code = 0
        # process(match)
    else:
        code = 1
    return code
    
    response = urllib2.urlopen(url)
    soup = BeautifulSoup(response.read(), from_encoding=response.info().getparam('charset'))
    title = soup.find('title').text


def init_db():
    with connection as cursor:
        cursor.execute(open("schema.sql", "r").read())


def get_service_urls():
    cur = pgconn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    sql = "SELECT name, url FROM apis"
    cur.execute(sql)
    return jsonify(cur.fetchall())


def test_tcp_port_open(host, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1)
    address = (host, port)
    try:
        # r = s.connect_ex(address)
        s.connect((host, int(port)))
        s.shutdown(socket.SHUT_RDWR)
        s.close()
        return 0
    # sock.settimeout(None)
    except:
        return 1


def get_internet_ip():
    # url = "https://api.ipify.org/"
    ip = get('https://api.ipify.org').text
    return ip


def get_intranet_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip

intranet_ip = get_intranet_ip()
internet_ip = get_internet_ip()
monitor_id = f"{intranet_ip}-{internet_ip}"


# def get_event(topic):
#     consumer = KafkaConsumer(topic)
#     consumer = KafkaConsumer(topic, auto_offset_reset='latest')  # earliest
#    for msg in consumer:
#         print(msg)


def fput_event(socket, topic, msg):
    producer = KafkaProducer(bootstrap_servers=socket)
    # for count in range(10):
    msgb = f"msg bytes".encode()
    msgb = msg.encode()
    producer.send(topic, msgb)
    producer.flush()


def test_text_contains_string(text, string):
    if string in text:
        code = 0
    return code


class URL():
    def __init__(self, uuid, url, regex):
        self.uuid = uuid
        self.url = url
        self.regex = regex
        self.fqdn = urlparse(url).hostname


    async def get(self, client):
        start = time.time()
        async with client.get(self.url) as rsp:
            self.rsp_text = await rsp.text()
            end = time.time()
            self.load_time = end - start
            self.rsp_code = rsp.status
            self.test_rsp_text_regex_code = self.test_rsp_text_regex()


    def test_rsp_text_regex(self):
        regexc = re.compile(self.regex)
        code = 1
        match = regexc.search(self.rsp_text)
        match = regexc.search(self.rsp_text)
        if match:
            code = 0
        else:
            code = 1
        return code


    async def get_dns(self):
        start = time.time()
        dns_response = dns.resolver.query(self.fqdn, 'A')
        for host in dns_response: 
            socket_open = test_tcp_port_open(host, 443)
            end = time.time()
            time_delta = end - start
            msg = f"{fqdn} {host} {socket_open} {time_delta}"
            fput_event(kafka_socket, kafka_topic, msg)


    def put_event(self, kafka_socket, topic, msg):
        producer = KafkaProducer(bootstrap_servers=kafka_socket)
        msgb = msg.encode()
        producer.send(topic, msgb)
        producer.flush()


async def check_urls():
    cur = pgconn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    sql = "SELECT * FROM url"
    cur.execute(sql)
    rows = cur.fetchall()
    i = 1
    urls = []
    async with aiohttp.ClientSession() as client:
        for row in rows:
            fqdn = urlparse(row['url']).hostname
            url = URL(row['uuid'], row['url'], row['rsp_text_regex'])
            urls.append(url)
            await url.get(client)
            url.rsp_text = None
            url.event = json.dumps(url.__dict__)
            print(url.event)
            url.put_event(kafka_socket, kafka_topic, url.event)


def main():
    while True:
        fput_event("localhost:9092", "quickstart-events", "foo")
        loop = asyncio.get_event_loop()
        loop.run_until_complete(check_urls())
        # loop.run_until_complete(check_dns())
        time.sleep(conf['check_interval'])


if __name__ == "__main__":
    main() 
    # mmain() 
