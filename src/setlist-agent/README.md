# setlist-agent: Semantic Kernel ACA Microservice

This is the entrypoint for the setlist agent, implemented as a Python microservice using Semantic Kernel and MCPSsePlugin to orchestrate the setlistfm-mcp-server and spotify-mcp-server tools.

- **Language:** Python 3.11+
- **Framework:** FastAPI (for HTTP server, can be adapted to FastMCP if required)
- **Purpose:** Expose an endpoint for Semantic Kernel orchestration, using setlistfm and spotify MCP servers as tools.

## Main Entrypoint

- `main.py`: Starts the agent service on port 8080.
- `agent.py`: Contains the orchestration logic using Semantic Kernel and MCPSsePlugin.

## Environment

- This service is designed to run as an Azure Container App (ACA).
- It will be deployed with managed identity and connect to other MCP servers via HTTP.

## Dependencies

- semantic-kernel
- httpx
- fastapi
- uvicorn

## Usage

Build and run locally (using [uv](https://github.com/astral-sh/uv)):

```bash
uv venv
uv sync
uv run uvicorn main:app --host 0.0.0.0 --port 8080
or
uv run main.py

uv run  --prerelease=allow  chainlit run chain_setlist.py
```

```
curl -X POST -H "Content-Type: application/json" -d @data.json http://
localhost:8000/chat
```

## Azure Deployment

This service is configured for deployment as an Azure Container App. See the project root `infra/` folder for Bicep IaC files.

```
docker build -t setlist-agent .
docker run --env-file .env  setlist-agent
```
