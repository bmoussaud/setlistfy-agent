#!/usr/bin/env bash

# This script generates a .vscode/mcp.json configuration file using SPOTIFY_MCP_URL and SETLISTFM_MCP_URL environment variables.
# Usage: export SPOTIFY_MCP_URL=... SETLISTFM_MCP_URL=...; ./gen_mcp_json.sh

set -ex


# Get values from azd env get-value
SPOTIFY_MCP_URL=$(azd env get-value SPOTIFY_MCP_URL)
SETLISTFM_MCP_URL=$(azd env get-value SETLISTFM_MCP_URL)

if [[ -z "$SPOTIFY_MCP_URL" ]]; then
  echo "Error: SPOTIFY_MCP_URL is not set in azd environment." >&2
  exit 1
fi
if [[ -z "$SETLISTFM_MCP_URL" ]]; then
  echo "Error: SETLISTFM_MCP_URL is not set in azd environment." >&2
  exit 1
fi

cat > .vscode/mcp.json <<EOF
{

  "servers": {
    "setlistfm": {
      "type": "sse",
      "url": "${SETLISTFM_MCP_URL}",
      "url_local": "http://localhost:9000/sse",
    },
    "spotify": {
      "type": "sse",
      "url": "${SPOTIFY_MCP_URL}",
      "url_local": "http://localhost:9001/sse",
    }
  }
}
EOF

echo ".vscode/mcp.json generated successfully."
