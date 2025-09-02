"""
Test script for SetlistFM Agent
"""
from configuration import settings
from setlistfm_agent import SetlistFMAgent
import asyncio
import os
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))


def dump_info(obj, indent=0):
    """Recursively print all information from dicts/lists/objects.

    This is a generic dump utility used by the tests to print the full
    contents of the agent response for debugging and validation.
    """
    prefix = " " * indent
    # Protect against very large / deeply nested structures
    try:
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, (dict, list)):
                    print(f"{prefix}{k}:")
                    dump_info(v, indent + 2)
                else:
                    print(f"{prefix}{k}: {v}")
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                print(f"{prefix}[{i}]:")
                dump_info(item, indent + 2)
        else:
            print(f"{prefix}{obj}")
    except Exception as e:
        print(f"{prefix}<error dumping object: {e}>")


async def test_agent():
    """Test the SetlistFM Agent functionality."""
    print("Testing SetlistFM Agent...")

    # Create agent instance
    agent = SetlistFMAgent()

    try:
        # Initialize the agent
        print("Initializing agent...")
        await agent.initialize()
        print("✓ Agent initialized successfully")

        # Test chat functionality
        print("\nTesting chat functionality...")
        response = await agent.chat("Tell me what do you know about Linkin Park")
        print(f"✓ Chat response received:")
        dump_info(response)
        print("---------------------------------------------------------------------")

        # Test setlist search
        print("\nTesting setlist search...")
        response = await agent.chat("Find recent setlists for Linkin Park in 2025", thread_id=response['thread_id'])
        print(f"✓ Chat response received:")
        dump_info(response)
        print("---------------------------------------------------------------------")

        # Test furuther setlist search with venue
        print("\nTesting setlist searchGrounding")
        response = await agent.chat("When does Linkin Park come back in France in 2026", thread_id=response['thread_id'])
        print(f"✓ Chat response received:")
        dump_info(response)
        print("---------------------------------------------------------------------")

        print("\n✓ All tests completed successfully!")

    except Exception as e:
        print(f"✗ Test failed: {e}")
        raise
    finally:
        # Clean up
        print("\nCleaning up...")
        await agent.shutdown()
        print("✓ Agent shutdown complete")


def validate_environment():

    from dotenv import load_dotenv
    load_dotenv()
    """Validate required environment variables."""
    required_vars = [
        "PROJECT_ENDPOINT",
        "MODEL_DEPLOYMENT_NAME",

    ]

    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        print(
            f"✗ Missing required environment variables: {', '.join(missing_vars)}")
        print("Please set these variables before running the test.")
        return False

    print("✓ Environment variables validated")
    return True


if __name__ == "__main__":
    print("SetlistFM Agent Test")
    print("=" * 50)

    # Validate environment
    if not validate_environment():
        sys.exit(1)

    # Run the test
    try:
        asyncio.run(test_agent())
        print("\n🎉 All tests passed!")
    except Exception as e:
        print(f"\n💥 Test failed: {e}")
        sys.exit(1)
