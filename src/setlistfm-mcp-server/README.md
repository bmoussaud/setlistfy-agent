# Setlist.fm MCP Server

This microservice exposes Setlist.fm data via FastMCP tools, suitable for running in Azure Container Apps.

## Features

- Fetch setlists by artist name
- Fetch setlist details by setlist ID

## Running locally

Prerequisites:

- Python 3.11 or later
- [uv](https://docs.astral.sh/uv/getting-started/installation/)

Run the server locally:

```bash
uv venv
uv sync

# linux/macOS
export SETLISTFM_API_KEY=<AN_API_KEY>
# windows
set SETLISTFM_API_KEY=<AN_API_KEY>
uv run fastmcp version
uv run fastmcp run setlistfm.py  --transport streamable-http --port 9000 --log-level debug
or
uv run fastmcp dev setlistfm.py 
```

## Environment Variables

- `SETLISTFM_API_KEY`: Your Setlist.fm API key (required)

## Usage

### Local Development

1. Install dependencies:
   ```bash
   uv venv
   uv sync
   ```
1. Run the MCP inspector:
   ```bash
   uv run fastmcp dev setlistfm.py  -e .
   ```

### Container Deployment (Azure Container Apps)

1. Build the container:
   ```bash
   docker build -t setlistfm-mcp-server .
   ```
2. Run the container (with API key):
   ```bash
   docker run -e SETLISTFM_API_KEY=your_api_key_here setlistfm-mcp-server
   ```
3. For Azure deployment, use Bicep or Azure CLI to deploy as a container app, passing the API key as a secret/environment variable.

## Tools

- `get_setlists_by_artist(artist_name: str, page: int = 1) -> str`: Get recent setlists for an artist.
- `get_setlist_by_id(setlist_id: str) -> str`: Get details for a specific setlist.

## Notes

- This service uses the Setlist.fm public API. See https://api.setlist.fm/docs/ for details.
- All requests use a custom User-Agent and require an API key.

## Contact

See project root README.md or contact the maintainer for questions.
