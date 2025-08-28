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
    "SETLISTFM_MCP_URL", "http://localhost:9001/sse")


API_URL="https://setlistfyagent-api-management-dev.azure-api.net/setlistfm-mcp/mcp"

@pytest.mark.asyncio
async def test_list_tools(caplog):
    """Test the MCP root endpoint for FastMCP server."""
    caplog.set_level(logging.INFO)
    async with Client(API_URL) as client:
        tools = await client.list_tools()
        assert isinstance(tools, list), "Expected tools to be a list"
        #logging.info("Available tools: %s", tools)
        
        for tool in tools:
            logging.info(f"Tool 1: {tool.name}")
            logging.info(f"Tool 2: {tool.description}")
            assert tool.name, "Resource name should not be empty"
            assert tool.description, "Resource description should not be empty"
        assert len(
            tools) == 14, f"{len(tools)} resources should be available, check the server configuration"
    # Print captured log output for pytest
    print("\n".join(caplog.messages))


@pytest.mark.asyncio
async def test_call_tool(caplog):
    """Test the MCP root endpoint for FastMCP server."""
    caplog.set_level(logging.INFO)
    async with Client(API_URL) as client:
        tool_name = "getArtist"
        tool_name = "returnsAnArtistForAGivenMusicbrainzMbid"
        # Call the tool with parameters
        response = await client.call_tool(tool_name, {"mbid": "b10bbbfc-cf9e-42e0-be17-e2c3e1d2600d"})
        assert response, "Response should not be empty"
        logging.info(f"Response: {response}")
