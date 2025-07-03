from dotenv import load_dotenv
import httpx
from fastmcp import FastMCP
import json
import logging
import os

from configuration import configure_telemetry


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

load_dotenv()

# Create an HTTP client for your API
headers = {
    "x-api-key": os.getenv("SETLISTFM_API_KEY", ""),
    "Accept": "application/json",
    "User-Agent": "setlistfm-mcp/1.0"
}
client = httpx.AsyncClient(base_url="https://api.setlist.fm/rest",
                           headers=headers)
# Load your OpenAPI spec from a file
with open("openapi-setlistfm.json", "r", encoding="utf-8") as f:
    openapi_spec = json.load(f)

# Create the MCP server
mcp = FastMCP.from_openapi(
    openapi_spec=openapi_spec,
    client=client,
    name="Setlist.fm MCP Server",
    version="1.0.0",
)
configure_telemetry()

if __name__ == "__main__":
    uvicorn_config = {
        "log_config": None,  # Use default logging configuration
    }
    mcp.run(
        transport="sse",
        host="127.0.0.1",
        port=9000,
        log_level="debug",
        uvicorn_config=uvicorn_config
    )
