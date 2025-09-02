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


API_URL = "https://api.githubcopilot.com/mcp/"
API_URL = "https://setlistfyagent-api-management-dev.azure-api.net/setlistfm-mcp/mcp"


async def test_list_tools():
    """Test the MCP root endpoint for FastMCP server."""
    async with Client(API_URL) as client:
        tools = await client.list_tools()
        assert isinstance(tools, list), "Expected tools to be a list"
        # logging.info("Available tools: %s", tools)

        for tool in tools:
            logging.info(f"Tool 1: {tool.name}")
            # logging.info(f"Tool 2: {tool.description}")
            assert tool.name, "Resource name should not be empty"
            assert tool.description, "Resource description should not be empty"
        assert len(
            tools) == 14, f"{len(tools)} resources should be available, check the server configuration"


async def test_call_tool():
    async with Client(API_URL) as client:
        tool_name = "getArtist"
        tool_name = "returnsAnArtistForAGivenMusicbrainzMbid"
        tool_name = "searchForArtists"
        logger.info(f"Calling tool: {tool_name}")
        response = await client.call_tool(tool_name, {"artistName": "Coldplay", "p": "1", "sort": "relevance"})
        assert response, "Response should not be empty"
        logging.info(f"Response: {response}")
        for item in response.content or []:
            logging.info(f"Item: {item.text}")

if __name__ == "__main__":
    asyncio.run(test_list_tools())
    asyncio.run(test_call_tool())
