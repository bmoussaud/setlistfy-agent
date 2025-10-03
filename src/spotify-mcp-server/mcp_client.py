import asyncio

from fastmcp.client import Client

SERVER_URL = "http://127.0.0.1:8000/mcp"

from fastmcp.client.auth.oauth import FileTokenStorage

storage = FileTokenStorage(server_url=SERVER_URL)
#storage.clear()

async def main():
    try:
        async with Client(SERVER_URL, auth="oauth") as client:
            assert await client.ping()
            print("✅ Successfully authenticated!")

            greet = await client.call_tool(
                "get_users_top_artists",raise_on_error=True
            )
            print(f"🤖 GPT-4-Turbo says: {greet.content[0].text}")
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
