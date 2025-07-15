import os
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.agents.models import BingGroundingTool
import os
from azure.ai.projects import AIProjectClient
from azure.ai.agents.models import MessageRole, BingGroundingTool
from azure.identity import DefaultAzureCredential
from azure.ai.agents.models import BingCustomSearchTool

from dotenv import load_dotenv
load_dotenv()
# Create an Azure AI Client from an endpoint, copied from your Azure AI Foundry project.
# You need to login to Azure subscription via Azure CLI and set the environment variables
# Ensure the PROJECT_ENDPOINT environment variable is set
project_endpoint = os.environ["PROJECT_ENDPOINT"]

# Create an AIProjectClient instance
project_client = AIProjectClient(
    endpoint=project_endpoint,
    # Use Azure Default Credential for authentication
    credential=DefaultAzureCredential()
)

conn_id = None
for c in project_client.connections.list():
    if c.type == "GroundingWithCustomSearch":
        print(f"Connection ID: {c.id}, Name: {c.name}, Type: {c.type}")
        conn_id = c.id


if not conn_id:
    print("No GroundingWithCustomSearch connection found. Please create one in the Azure AI Foundry project.")
    exit(1)
# Ensure the BING_CONNECTION_NAME environment variable is set
# conn_id = os.environ["BING_CONNECTION_NAME"]
# Initialize Bing Custom Search tool with connection id and instance name
bing_custom_tool = BingCustomSearchTool(
    connection_id=conn_id, instance_name="defaultConfiguration")

# Create Agent with the Bing Custom Search tool and process Agent run
with project_client:
    agents_client = project_client.agents

    agent = agents_client.create_agent(
        model=os.environ["MODEL_DEPLOYMENT_NAME"],
        name="my-agent",
        instructions="You are a helpful agent",
        tools=bing_custom_tool.definitions,
    )
    print(f"Created agent, ID: {agent.id}")

    # Create thread for communication
    thread = agents_client.threads.create()
    print(f"Created thread, ID: {thread.id}")

    # Create message to thread
    message = agents_client.messages.create(
        thread_id=thread.id,
        role="user",
        content="Qui sera a l'arena ladefense le week end prochain ?",
    )
    print(f"Created message, ID: {message.id}")

    # Create and process Agent run in thread with tools
    run = agents_client.runs.create_and_process(
        thread_id=thread.id, agent_id=agent.id)
    print(f"Run finished with status: {run.status}")

    if run.status == "failed":
        print(f"Run failed: {run.last_error}")

    # Delete the Agent when done
    agents_client.delete_agent(agent.id)
    print("Deleted agent")

    # Fetch and log all messages
    messages = agents_client.messages.list(thread_id=thread.id)
    for msg in messages:
        if msg.text_messages:
            for text_message in msg.text_messages:
                print(f"Agent response: {text_message.text.value}")
            for annotation in msg.url_citation_annotations:
                print(
                    f"URL Citation: [{annotation.url_citation.title}]({annotation.url_citation.url})")
