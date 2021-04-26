#!/usr/bin/env python3
from kafka import KafkaConsumer

pgconn = psycopg2.connect(host=conf['postgres.host'],
                          dbname=conf['postgres.dbname'],
                          user=conf['postgres.dbuser'],
                          password=conf['postgres.dbpass'])

def put_event(msg):
    cur = pgconn.cursor()
        # sql = "INSERT INTO event (msg) VALUES (%s)" % msg 
        sql = f"INSERT INTO event (msg) VALUES ({msg})" 
    	cur.execute(sql)
    	# rows = cur.fetchall()
    	pgconn.commit()

topic = "quickstart-events"
# consumer = KafkaConsumer('my_favorite_topic')
consumer = KafkaConsumer(topic)

for msg in consumer:
    print(msg)


