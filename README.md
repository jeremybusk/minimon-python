# Minimon
A miniture monitor that can actually do some mega monitoring

# Usage

vim conf.yml
```
edit values to match your Aiven or local postgres and kafka settings
```

Initialize persistent data stores
```
./minimon.py -K
./minimon.py -I
```

Run http url checker
```
./minimon.py -s
```

Run kafka to postgres consumer
```
./minimon.py -k
```

# App

# Scope
- Simple python, postgres, golang event message handling. Use Golang for improved performance.
- Used aiohttp single async session for more performant experience.

# Considerations
- WARNING! This is a first try. Got a little cowboy on this. Tried to do async and still have learning/work to do.
- I followed my interests while doing this project. Yes, it could have been done much simpler.
- Needs more refactoring.
- Yes, scope creep did happen. That's the way I roll sometimes and then I whack it back and in the process learn.
- Probably should have started simple. This needs some organization. I probably am inefficent on type conversions.
- Multiprocessing or threading are other options using python-requests and maybe some OOP
  - https://timber.io/blog/multiprocessing-vs-multithreading-in-python-what-you-need-to-know/
  - https://docs.python.org/3/library/multiprocessing.html
  - https://docs.python.org/3/library/threading.html
- https://github.com/spyoungtech/grequests is another way as well but I did not choose this route


# Major Parts
- https://aiven.io/
- Postgres
- Kafka
- Python (3.6 or higher preferably the latest)
- Python aiohttp (you could try using requests & grequests) 
- Python psycopg2 (If multi db interface you could use sqlalchemy raw (execute) - https://docs.sqlalchemy.org/en/14/core/engines.html


# Aiven Open Cloud Platform
- https://aiven.io/


# Docker Play Examples
```
docker run -dit --name minimon-postgres -e POSTGRES_PASSWORD=secret -d postgres
docker exec -it -e PGPASSWORD=secret minimon-postgres pg_dump -U postgres -h localhost -d minimon -s --no-comments > schema.sql
docker exec -it -e PGPASSWORD=secret minimon-postgres pg_dump -U postgres -h localhost -d minimon -a --no-comments > data.sql
docker exec -it -e PGPASSWORD=secret minimon-postgres psql -U postgres -h localhost -d minimon
cat data.sql | sed s/--.*$//g | sed -re '/^\s*$/d'

curl -sSL https://raw.githubusercontent.com/bitnami/bitnami-docker-kafka/master/docker-compose.yml > docker-compose.yml
docker-compose up -d
```

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

## Possible Extentions
 - https://github.com/petere/pguri  - uri type


# Timescaledb - Good for time partitioning your metric item history/timeline table
- https://docs.timescale.com/latest/using-timescaledb/hypertable://docs.timescale.com/latest/using-timescaledb/hypertabless
- https://docs.timescale.com/latest/getting-started/setup
- https://docs.timescale.com/latest/getting-started/installation


# Nanonsecond Accurracy
- Store as epoch seconds and nanoseconds in another table
- https://github.com/fvannee/timestamp9


# Python Kafka Clients
- kafka-python
  - https://github.com/dpkp/kafka-python
  - https://kafka-python.readthedocs.io/en/master/
  - https://kafka-python.readthedocs.io/en/master/usage.html
- confluent-kafka as alternative option
  - https://github.com/confluentinc/confluent-kafka-python
  - https://docs.confluent.io/platform/current/clients/confluent-kafka-python/html/index.html
  - https://docs.confluent.io/cloud/current/connectors/cc-postgresql-sink.html#:~:text=The%20Kafka%20Connect%20PostgreSQL%20Sink,limited%20auto%2Devolution%20are%20supported.

# Style Guideline & Enforcement
- https://www.python.org/dev/peps/pep-0008/
- https://github.com/PyCQA/flake8
- https://flake8.pycqa.org/en/latest/index.html#quickstart


# Interesting Resources of Possible Use
- https://github.com/debezium/debezium-examples
- https://debezium.io/documentation/faq/#what_is_debezium


# Other Resources of Discovery
- https://www.google.com/ 
- https://stackoverflow.com/ 
- Google using Stackoverflow in name with issue
- Not using Bing

# Github Actions
- https://docs.github.com/en/actions/reference/workflow-syntax-for-github-actions


# Todo
- [ ] Fix docs while checking it works from scratch
- [ ] Check conversions
- [ ] Refactor/simplify to fix organic growth.
- [ ] Unit/CI/CD tests using pytests - https://docs.pytest.org/en/latest/ 
- [ ] Row level permissions for users to control resources
- [ ] Tables/colums for user attributes like email
- [ ] Triggers interface tables/columns to make notification simple and easiy
- [ ] Actions interface for user in database for notifications sent to email, text, voice ...
- [ ] Low maintenance boilerplate rest interface - https://postgrest.org/en/stable/ and views for insta rest functions
- [ ] Test multiprocessing or threading to see how much of a process hit you would take doing so while making code simpler to read.
