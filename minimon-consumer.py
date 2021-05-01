#!/usr/bin/env python3

from envyaml import EnvYAML
from kafka import KafkaConsumer
import psycopg2

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
