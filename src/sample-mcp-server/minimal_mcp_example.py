import logging
import uvicorn
from fastmcp import FastMCP
from fastapi import FastAPI
from starlette.routing import Mount

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create your FastMCP server as well as any tools, resources, etc.
mcp = FastMCP("MyServer")

# Create the ASGI app
mcp_app = mcp.http_app(path='/mcp')

# Create a FastAPI app and mount the MCP server
app = FastAPI(lifespan=mcp_app.lifespan)
app.mount("/mcp-server", mcp_app)

# Define a simple route for testing


@mcp.tool
def hello(name: str) -> str:
    return f"Hello, {name}!"


@mcp.tool("test")
async def test_tool():
    """
    A simple test tool that returns a greeting.
    """
    return {"message": "Hello from the FastMCP server!"}

# Get a Starlette app instance for Streamable HTTP transport (recommended)
http_app = mcp.http_app()
