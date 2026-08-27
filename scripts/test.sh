#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python3}"

"${PYTHON_BIN}" -m flake8 \
    minimon.py minimon-consumer.py test_minimon.py test_integration.py
"${PYTHON_BIN}" -m pytest -m "not integration"

if ! command -v docker >/dev/null 2>&1; then
    echo "Docker is required for integration tests." >&2
    exit 1
fi
if ! docker info >/dev/null 2>&1; then
    echo "Docker is installed, but its daemon is unavailable to this user." >&2
    exit 1
fi

"${PYTHON_BIN}" -m pytest -m integration -v
