#!/usr/bin/env python3
"""Compatibility entry point for the Kafka-to-PostgreSQL consumer."""

import sys

from minimon import main


if __name__ == "__main__":
    raise SystemExit(main(["--kafka-to-pg", *sys.argv[1:]]))
