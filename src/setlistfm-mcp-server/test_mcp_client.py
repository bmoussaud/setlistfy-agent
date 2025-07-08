"""
Test for simulating an MCP client using FastMCP against setlistfm-mcp-server.
"""
import asyncio
import os
import pytest
import httpx
import logging
import dotenv
from fastmcp import Client

dotenv.load_dotenv()

# Configure logging to show INFO messages in pytest output
logging.basicConfig(level=logging.INFO, force=True)
logger = logging.getLogger()
logger.setLevel(logging.INFO)


API_URL = os.getenv(
    "MCP_SERVER_URL", "https://setlistfm-mcp-server.nicehill-27600660.francecentral.azurecontainerapps.io/sse")

API_URL = "http://localhost:9001/sse"


@pytest.mark.asyncio
async def test_list_tools(caplog):
    """Test the MCP root endpoint for FastMCP server."""
    caplog.set_level(logging.INFO)
    async with Client(API_URL) as client:
        tools = await client.list_tools()
        assert isinstance(tools, list), "Expected tools to be a list"
        # logging.info("Available tools: %s", tools)
        assert len(
            tools) == 15, "15 resources should be available, check the server configuration"
        tool = tools[0]
        logging.info(f"Tool: {tool.name} - {tool.description}")
        assert tool.name, "Resource name should not be empty"
        assert tool.description, "Resource description should not be empty"
    # Print captured log output for pytest
    print("\n".join(caplog.messages))


@pytest.mark.asyncio
async def test_call_tool(caplog):
    """Test the MCP root endpoint for FastMCP server."""
    caplog.set_level(logging.INFO)
    async with Client(API_URL) as client:
        tool_name = "getArtists"
        # Call the tool with parameters
        response = await client.call_tool(tool_name, {"name": "The Beatles"})
        assert response, "Response should not be empty"
        logging.info(f"Response: {response}")
