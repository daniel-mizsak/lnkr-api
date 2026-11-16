#!/usr/bin/env bash

set -euo pipefail

# Run this file from the project root, where alembic.ini lives.
# Both Dockerfiles set WORKDIR /app, so the script runs from that directory.
alembic upgrade head
