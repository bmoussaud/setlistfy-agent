import asyncio
from pathlib import Path

from fastmcp.client import Client

SERVER_URL = "http://localhost:9001/mcp"

from fastmcp.client.auth import OAuth

oauth = OAuth(mcp_url=SERVER_URL,token_storage_cache_dir=Path("/tmp/.spotify-mcp-token"), scopes=["user-top-read"])

#from fastmcp.client.auth.oauth import FileTokenStorage
#storage = FileTokenStorage(server_url=SERVER_URL)
#storage.clear()

async def main():
    try:
        async with Client(SERVER_URL, auth=oauth) as client:
            print("🔑 Authenticating with Spotify...")
            assert await client.ping()
            print("✅ Successfully authenticated!")
            tools = await client.list_tools()
            for tool in tools:
                print(f"🛠️ Available tool: {tool}")
            greet = await client.call_tool(
                "get_users_top_artists",raise_on_error=True
            )
            print(f"🤖 GPT-4-Turbo says: {greet.content[0].text}")
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
