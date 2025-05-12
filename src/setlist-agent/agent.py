from azure.ai.agents.models import CodeInterpreterTool
import os
import asyncio
import logging
from opentelemetry import trace

import semantic_kernel as sk
from dotenv import load_dotenv
from semantic_kernel.utils.logging import setup_logging
from semantic_kernel.planners.sequential_planner import SequentialPlanner
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
from semantic_kernel.connectors.ai.open_ai.services.open_ai_chat_completion import OpenAIChatCompletion
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.connectors.ai.open_ai.prompt_execution_settings.azure_chat_prompt_execution_settings import (
    AzureChatPromptExecutionSettings,
)
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.agents import ChatCompletionAgent, ChatHistoryAgentThread
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.functions import KernelArguments
from semantic_kernel.connectors.mcp import MCPSsePlugin
from semantic_kernel.connectors.ai.azure_ai_inference import AzureAIInferenceChatCompletion
from config import enable_telemetry

from azure.monitor.opentelemetry import configure_azure_monitor

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class SetlistAgent:
    def __init__(self):
        self._kernel = sk.Kernel()

        # setup_logging()
        enable_telemetry(log_to_project=True)
        logging.getLogger("kernel").setLevel(logging.DEBUG)

        # test if AZURE_AI_INFERENCE_API_KEY  is set
        if not os.getenv("AZURE_AI_INFERENCE_API_KEY"):
            logger.error("AZURE_AI_INFERENCE_API_KEY must be set")
            raise ValueError("AZURE_AI_INFERENCE_API_KEY must be set")
        # and test AZURE_AI_INFERENCE_ENDPOINT is set
        if not os.getenv("AZURE_AI_INFERENCE_ENDPOINT"):
            logger.error("AZURE_AI_INFERENCE_ENDPOINT must be set")
            raise ValueError("AZURE_AI_INFERENCE_ENDPOINT must be set")
        # and test AZURE_OPENAI_CHAT_DEPLOYMENT_NAME is set
        if not os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"):
            logger.error("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME must be set")
            raise ValueError("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME must be set")

        logger.info(
            "Initializing SetlistAgent with Azure AI Inference Chat Completion service")
        logger.info(
            f"Using Azure AI Inference Endpoint: {os.getenv('AZURE_AI_INFERENCE_ENDPOINT')}")
        logger.info(
            f"Using Azure OpenAI Chat Deployment Name: {os.getenv('AZURE_OPENAI_CHAT_DEPLOYMENT_NAME')}")

        self._kernel.add_service(AzureAIInferenceChatCompletion(
            service_id="SetList Agent Service",
            api_key=os.getenv("AZURE_AI_INFERENCE_API_KEY"),
            endpoint=os.getenv("AZURE_AI_INFERENCE_ENDPOINT"),
            ai_model_id=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME")
        ))

    def new_thread(self):
        """Create a new thread for the agent."""
        logger.info("Creating new chat history thread")
        thread = ChatHistoryAgentThread(chat_history=ChatHistory())
        return thread

    async def initialize_agent(self):
        """Initialize the SetlistAgent with necessary plugins and services."""
        # Register Setlist FM MCP plugin
        logger.info(
            f"Registering MCPSsePlugin tools for SetlistFM {os.getenv('SETLISTFM_MCP_URL')}")
        setlistfm_mcp_url = os.getenv("SETLISTFM_MCP_URL")
        self.plugin_setlistfm = MCPSsePlugin(
            name="SetlistFM",
            description="SetlistFM Plugin",
            url=setlistfm_mcp_url,
        )
        await self.plugin_setlistfm.connect()
        self._kernel.add_plugin(self.plugin_setlistfm, "SetlistFM")

        # Register Spotify plugin
        logger.info(
            f"Registering MCPSsePlugin tools for Spotify {os.getenv('SPOTIFY_MCP_URL')}")
        self.plugin_spotify = MCPSsePlugin(
            name="Spotify",
            description="Spotify Plugin",
            url=os.getenv("SPOTIFY_MCP_URL"),
        )
        await self.plugin_spotify.connect()
        self._kernel.add_plugin(self.plugin_spotify, "Spotify")

        # Create a chat history object
        self._agent = ChatCompletionAgent(
            kernel=self._kernel,
            name="my_setlist_agent",
            function_choice_behavior=FunctionChoiceBehavior.Auto(),
            instructions=f"""
            You are a helpful music assistant that provides information about artists, concerts, and setlists.
            You can search for artists, find setlists from concerts, and provide venue information.

            When asked about an artist's concerts or setlists, use the SetlistFM plugin to search for that information.
            Always try to be helpful and provide as much relevant information as possible.

            If the user asks for something you can't do, politely explain your limitations.
            """
        )

        logger.info("SetlistAgent initialized successfully.")

    async def shutdown(self):
        logger.info("Shutting down SetlistAgent...")

        try:
            if self.plugin_setlistfm is not None:
                logger.info("Closing SetlistFM plugin connection...")
                await self.plugin_setlistfm.close()
            if self.plugin_spotify is not None:
                logger.info("Closing Spotify plugin connection...")
                await self.plugin_spotify.close()

        except Exception as e:
            logger.error(f"Error shutting down plugins: {e}")

    async def chat(self, user_input: str, thread=None):
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("setlist-agent-chat"):
            logger.info(f"chat user_input: {user_input}")
            joined_response = []
            async for response in self._agent.invoke(messages=user_input, thread=thread):
                logger.info(f"chat response: {response.to_dict()}")
                joined_response.append(str(response.content))
            return "\n".join(joined_response)


if __name__ == "__main__":
    async def main():
        # Load environment variables from .env file
        load_dotenv()
        logger.info("initialize the agent....")
        agent = SetlistAgent()
        thread = agent.get_thread(thread_id=None)
        await agent.initialize_agent()
        logger.info("chat....")
        response = await agent.chat("Hello", thread_id=thread.id, raw=False)
        print(response)
        await agent.shutdown()
        import sys
        sys.exit(0)
        response = await agent.chat("I need information about the lastest concert performed by Muse, for each entry of the list, find the track in spotify", raw=True)
        print(response)
        # print(thread)
        # response, thread = await agent.chat("I need information about the lastest concert performed by Epica, for each entry of the list, find the track in spotify")
        # print(response)
        # print(thread)
        logger.info("shutdown......")
        await agent.shutdown()

    asyncio.run(main())
