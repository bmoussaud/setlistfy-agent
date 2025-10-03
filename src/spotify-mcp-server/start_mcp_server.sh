#/bin/bash
set -ex
source .venv/bin/activate
uv sync
uv run mcp_server.py 