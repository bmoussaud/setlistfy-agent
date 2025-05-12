# ------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# ------------------------------------

"""
DESCRIPTION:
    This sample demonstrates how to use basic agent operations from
    the Azure Agents service using a synchronous client with Azure Monitor tracing.
    View the results in the "Tracing" tab in your Azure AI Foundry project page.

USAGE:
    python sample_agents_basics_with_azure_monitor_tracing.py

    Before running the sample:

    pip install azure-ai-projects azure-ai-agents azure-identity azure-monitor-opentelemetry

    Set these environment variables with your own values:
    1) PROJECT_ENDPOINT - The Azure AI Project endpoint, as found in the Overview
                          page of your Azure AI Foundry portal.
    2) MODEL_DEPLOYMENT_NAME - The deployment name of the AI model, as found under the "Name" column in
       the "Models + endpoints" tab in your Azure AI Foundry project.
    3) AZURE_TRACING_GEN_AI_CONTENT_RECORDING_ENABLED - Optional. Set to `true` to trace the content of chat
       messages, which may contain personal data. False by default.
    4) APPLICATIONINSIGHTS_CONNECTION_STRING - Set to the connection string of your Application Insights resource.
       This is used to send telemetry data to Azure Monitor. You can also get the connection string programmatically
       from AIProjectClient using the `telemetry.get_connection_string` method. A code sample showing how to do this
       can be found in the `sample_telemetry.py` file in the azure-ai-projects telemetry samples.
"""

import chainlit as cl
import asyncio
from semantic_kernel.agents import ChatCompletionAgent, ChatHistoryAgentThread
from enhanced_agent import EnhancedSetlistAgent
from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry import trace
import os
from azure.ai.projects import AIProjectClient
from azure.ai.agents.models import ListSortOrder
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
load_dotenv()

# [START enable_tracing]

# Enable Azure Monitor tracing
application_insights_connection_string = os.environ["APPLICATIONINSIGHTS_CONNECTION_STRING"]
configure_azure_monitor(
    connection_string=application_insights_connection_string)

scenario = os.path.basename(__file__)
tracer = trace.get_tracer(__name__)


@cl.on_message
async def on_message(message: cl.Message):
    with tracer.start_as_current_span("Chainlit"):
        # with project_client:
        # agents_client = project_client.agents
        agent = EnhancedSetlistAgent()
        await agent.initialize_agent()
        msg = await cl.Message("🤔 Je pense à quelque chose...", author="agent").send()

        response = await agent.chat(message.content, thread=ChatHistoryAgentThread())
        print(response)
        print("=========================================")
        msg.content = response
        await msg.update()
        # [END enable_tracing]

if __name__ == "__main__":
    asyncio.run(main())
