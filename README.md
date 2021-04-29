# Minimon
A miniture monitor that can actually do some mega monitoring

WARNING! This is a first try. Tried to do async and still have learning/work to do.
Needs a refactor too
It's been a long time since did much async (javascript FE).


# Parts
- https://aiven.io/
- Postgres
- Kafka
- Python (3.6 or higher preferably the latest)
- Python aiohttp (you could try using requests & grequests) 
- Python psycopg2 (If multiplatform you could use sqlalchemy raw (execute) - https://docs.sqlalchemy.org/en/14/core/engines.html


# Aiven Open Cloud Platform
- https://aiven.io/


# Docker
```
docker run -dit --name minimon-postgres -e POSTGRES_PASSWORD=secret -d postgres
docker exec -it -e PGPASSWORD=secret minimon-postgres pg_dump -U postgres -h localhost -d minimon -s > schema.sql
docker exec -it -e PGPASSWORD=secret minimon-postgres pg_dump -U postgres -h localhost -d minimon -a > data.sql
docker exec -it -e PGPASSWORD=secret minimon-postgres psql -U postgres -h localhost -d minimon
curl -sSL https://raw.githubusercontent.com/bitnami/bitnami-docker-kafka/master/docker-compose.yml > docker-compose.yml
docker-compose up -d
```


### psql -U postgres -W -h $IP -d minimon


# Python Concurrent Code
- https://docs.python.org/3/library/asyncio.html


# Python HTTP Clients
- aiohttp
  - https://github.com/aio-libs/aiohttp
  - https://docs.aiohttp.org/en/stable/http_request_lifecycle.html
  - https://docs.aiohttp.org/en/stable/client_reference.html
  - https://docs.aiohttp.org/en/stable/client_advanced.html
  - https://pypi.org/project/aiohttp/
- python-requests
  - https://github.com/psf/requests
  - https://docs.python-requests.org/en/master/
  - https://2.python-requests.org/en/master/user/advanced/
- Libs
  - https://urllib3.readthedocs.io/en/latest/
  - https://github.com/urllib3/urllib3
  - https://docs.python.org/3/library/urllib.html


# Python Postgres Clients
- psycopg2
  - https://www.psycopg.org/docs/usage.html
- sqlalchemy (engine.connect -> execute( 'raw sql query' )
  - https://docs.sqlalchemy.org/en/14/dialects/postgresql.html with raw sql queries


# Kafka Server:
- https://kafka.apache.org/quickstart


# Postgres
  - https://www.postgresql.org/docs/current/index.html


# Timescaledb - Good for time partitioning your metric item history/timeline table
- https://docs.timescale.com/latest/using-timescaledb/hypertable://docs.timescale.com/latest/using-timescaledb/hypertabless
- https://docs.timescale.com/latest/getting-started/setup
- https://docs.timescale.com/latest/getting-started/installation


# Nanonsecond Accurracy
- Store as epoch seconds and nanoseconds in another table
- https://github.com/fvannee/timestamp9


#Python Kafka Clients
- kafka-python
  - https://kafka-python.readthedocs.io/en/master/
  - https://github.com/dpkp/kafka-python
- confluent-kafka
  - https://github.com/confluentinc/confluent-kafka-python
  - https://docs.confluent.io/platform/current/clients/confluent-kafka-python/html/index.html


# Psycopg2
```
# PSYCOPG2_TESTDB
# PSYCOPG2_TESTDB_HOST
# PSYCOPG2_TESTDB_PORT
# PSYCOPG2_TESTDB_USER
# python -c "import tests; tests.unittest.main(defaultTest='tests.test_suite')" --verbose
```


# Other Resources
- https://www.google.com/ 
- https://stackoverflow.com/ 
- Google using Stackoverflow in name with issue

