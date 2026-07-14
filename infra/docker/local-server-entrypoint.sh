#!/bin/sh
set -eu

python -m inkdesk_server.db_migrations upgrade
exec uvicorn "$@"
