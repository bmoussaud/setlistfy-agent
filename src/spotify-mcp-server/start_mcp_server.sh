#/bin/bash
set -ex
source .venv/bin/activate
uv sync
uv run fastmcp run minimal.py  --transport http --host localhost --port 9001 --log-level DEBUG