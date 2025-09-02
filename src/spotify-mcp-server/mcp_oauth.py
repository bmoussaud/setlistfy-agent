

from fastmcp.server.auth.providers.github import GitHubProvider
import logging
from fastmcp import FastMCP


# Configure logging for both uvicorn and fastmcp
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT)

fastmcp_logger = logging.getLogger("fastmcp")
fastmcp_logger.setLevel(logging.DEBUG)

uvicorn_logger = logging.getLogger("uvicorn")
uvicorn_logger.setLevel(logging.DEBUG)


# GitHub provider with automatic API-based token validation
auth = GitHubProvider(
    client_id="Ov23liUQ9TBFbENd1uGQ",
    client_secret="dacafc66121cff28e283fa9778c24cb086cf2b2d",
    base_url="http://localhost:8000",
    resource_server_url="http://localhost:8000/mcp",
)

mcp = FastMCP("My MCP Server", auth=auth)


@mcp.tool(description="Greet a person with their name")
def greet(name: str) -> str:
    return f"Hello, {name}!"


if __name__ == "__main__":
    mcp.run(
        transport="http",
        port=8000
    )
