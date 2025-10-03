import asyncio

from fastmcp.client import Client

SERVER_URL = "http://127.0.0.1:8000/mcp"


async def main():
    try:
        async with Client(SERVER_URL, auth="oauth") as client:
            assert await client.ping()
            print("✅ Successfully authenticated!")

            tools = await client.list_tools()
            print(f"🔧 Available tools ({len(tools)}):")
            for tool in tools:
                print(f"   - {tool.name}: {tool.description}")

            greet = await client.call_tool(
                "greet", arguments={'name': 'Benoit'}
            )
            print(f"🤖 GPT-4-Turbo says: {greet.content[0].text}")
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
