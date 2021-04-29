#!/usr/bin/env python3
from kafka import KafkaConsumer

pgconn = psycopg2.connect(host=conf['postgres.host'],
                          dbname=conf['postgres.dbname'],
                          user=conf['postgres.dbuser'],
                          password=conf['postgres.dbpass'])
