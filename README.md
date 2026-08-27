# Minimon

Minimon checks HTTP URLs concurrently, publishes check results to Kafka, and
stores consumed events in PostgreSQL.

## Requirements

- Python 3.10 or newer
- PostgreSQL
- Kafka

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
test -f conf.yml || cp conf.yml.example conf.yml
export PGPASS='replace-me'
```

Edit `conf.yml` for the local PostgreSQL and Kafka endpoints. Environment
variables in `$NAME` or `${NAME}` form are expanded when configuration is
loaded. Do not commit credentials to the repository.

## Usage

Create the Kafka topic if it does not already exist:

```bash
./minimon.py -I
```

Recreate the PostgreSQL database, load the schema, and seed URLs. This command
deletes the configured database first:

```bash
./minimon.py -i
```

Check URLs once or run continuously:

```bash
./minimon.py --once
./minimon.py --service
./minimon.py --once --limit-urls 50
```

Consume Kafka events into PostgreSQL:

```bash
./minimon.py --kafka-to-pg
# Compatibility entry point:
./minimon-consumer.py
```

Add URLs from a file, one URL per line:

```bash
./minimon.py --add-urls-file top50.txt
```

Use a different configuration file with `--config PATH`. Run `./minimon.py
--help` for all commands.

## Development

```bash
python -m pytest
python -m flake8 minimon.py minimon-consumer.py test_minimon.py
```
