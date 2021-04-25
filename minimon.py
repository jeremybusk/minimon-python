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

# print(env['project.name'])
conf = EnvYAML('conf.yml')
kafka_topic = conf['kafka.topic']
kafka_socket = conf['kafka.socket']


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

def consume(topic):
    consumer = KafkaConsumer(topic)
    consumer = KafkaConsumer(topic, auto_offset_reset='latest')  # earliest
    for msg in consumer:
        print(msg)


def produce(socket, topic):
    producer = KafkaProducer(bootstrap_servers=socket)
    for count in range(10):
        msgb = f"{count} msg bytes".encode()
        producer.send(topic, msgb)


def check_url(url):
    r = requests.get(url)
    vars(r)


async def check_dns(fqdn):
    start = time.time()
    dns_response = dns.resolver.query(fqdn, 'A')
    for host in dns_response: 
        # print(host)
        socket_open = test_tcp_port_open(host, 443)
        # print(f"{host} {socket_open}")
        # status = await resp.status()
        end = time.time()
        time_delta = end - start
        retval = f"{fqdn} {host} {socket_open} {time_delta}"
        print(retval)

    # return retval
    return None 


async def check_url(client, url, contains_string):
    # async with client.get('http://python.org') as resp:
    start = time.time()
    async with client.get(url) as resp:

        text = await resp.text()
        # rjson = await resp.json()
        end = time.time()
        load_time = end - start
        # status_time = status_end - start
        if contains_string in text:
            text_contains_string = True
        else:
            text_contains_string = False

        # print(url, ": ", load_time, "response length:", len(text))
        text_length = len(text)
        status_code = resp.status
        # retval = f"url: {url}, load_time: {load_time}, status_time: {status_time}, text_contains_string: {text_contains_string}, text_length: {text_length}"
        retval = f"mid: {monitor_id},  url: {url}, load_time: {load_time}, status_code: {status_code}, text_contains_string: {text_contains_string}, text_length: {text_length}"
        # assert resp.status == 200
        # assert "Example" in resp.text() 
        return retval 


async def check_urls():
    for app in conf['apps']:
        i = f"apps.{app}.url"
        url = conf[i]
        i = f"apps.{app}.contains_string"
        fqdn = urlparse(url).hostname
        r = await check_dns(fqdn)
        print(r)
        contains_string = conf[i]
        # print(url)
        async with aiohttp.ClientSession() as client:
            # url = 'https://example.com'
            # url = 'https://.asdfdasff.example.com'
            r = await check_url(client, url, contains_string)
            print(r)
            # assert "Example" in html
            # print(html)



def main():
    while True:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(check_urls())
        # loop.run_until_complete(check_dns())
        time.sleep(conf['check_interval'])
    # asyncio.run(fmain())
    # produce()
    # consume(kafka_topic)
    # url = "https://uvoo.io"
    # check_url(url)


if __name__ == "__main__":
    main() 
