import time
import json
import os
from dotenv import load_dotenv
from azure.ai.agents.models import MessageTextContent, ListSortOrder
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

load_dotenv()

# Debug: Print all relevant environment variables
print("=== Environment Variables ===")
print(f"PROJECT_ENDPOINT: {os.getenv('PROJECT_ENDPOINT')}")
print(
    f"AZURE_AI_INFERENCE_ENDPOINT: {os.getenv('AZURE_AI_INFERENCE_ENDPOINT')}")
print(
    f"AZURE_OPENAI_CHAT_DEPLOYMENT_NAME: {os.getenv('AZURE_OPENAI_CHAT_DEPLOYMENT_NAME')}")
print(f"SETLISTFM_MCP_URL: {os.getenv('SETLISTFM_MCP_URL')}")
print("============================")

project_endpoint = os.getenv('PROJECT_ENDPOINT')
if not project_endpoint:
    raise ValueError("PROJECT_ENDPOINT environment variable is not set")

project_client = AIProjectClient(
    endpoint=project_endpoint,
    credential=DefaultAzureCredential(),
    api_version="2025-05-15-preview"

)

setlist_fm = {
    "type": "mcp",
    "server_label": "SetlistFM",
    "server_url": os.getenv("SETLISTFM_MCP_URL"),
    "require_approval": "never"
}
print(f"SetlistFM MCP server: {setlist_fm}")

with project_client:
    base_instructions = """
        You are a helpful music assistant that provides information about artists, concerts, setlists, and Spotify data.
        You can search for artists, find setlists from concerts, provide venue information, and access Spotify features.
        
        When asked about an artist's concerts or setlists, use the SetlistFM plugin to search for that information.
    
        Always try to be helpful and provide as much relevant information as possible.
    """

    # Use the model name from your Bicep deployment
    model_name = os.getenv(
        'MODEL_DEPLOYMENT_NAME', 'mysetlistagent-gpt-4o')
    print(f"Using model: {model_name}")

    agent = project_client.agents.create_agent(
        model=model_name,
        name="setlist-music-agent",
        instructions=base_instructions,
        tools=[setlist_fm],  # Enable the MCP tool
        tool_resources=None
    )
    print(f"Created agent, agent ID: {agent.id}")
    thread = project_client.agents.threads.create()
    print(f"Created thread, thread ID: {thread.id}")
    content = "Donne moi la setlist de EPICA"
    print(f"Creating message with content: {content}")
    message = project_client.agents.messages.create(
        thread_id=thread.id, role="user", content=content
    )
    print(f"Created message, message ID: {message.id}")

    run = project_client.agents.runs.create(
        thread_id=thread.id, agent_id=agent.id)

    # Poll the run as long as run status is queued or in progress
    while run.status in ["queued", "in_progress", "requires_action"]:
        # Wait for a second
        time.sleep(1)
        run = project_client.agents.runs.get(
            thread_id=thread.id, run_id=run.id)
        print(f"Run status: {run.status}")

    if run.status == "failed":
        print(f"Run error: {run.last_error}")

    run_steps = project_client.agents.run_steps.list(
        thread_id=thread.id, run_id=run.id)
    for step in run_steps:
        print(f"Run step: {step.id}, status: {step.status}, type: {step.type}")
        if step.type == "tool_calls":
            print(f"Tool call details:")
            for tool_call in step.step_details.tool_calls:
                print(json.dumps(tool_call.as_dict(), indent=2))

    messages = project_client.agents.messages.list(
        thread_id=thread.id, order=ListSortOrder.ASCENDING)
    for data_point in messages:
        last_message_content = data_point.content[-1]
        if isinstance(last_message_content, MessageTextContent):
            print(f"{data_point.role}: {last_message_content.text.value}")

    project_client.agents.delete_agent(agent.id)
    print(f"Deleted agent, agent ID: {agent.id}")
