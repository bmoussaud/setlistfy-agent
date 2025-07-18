"""
SetlistFM Agent using AI Foundry SDK with Bing Grounding
"""
import asyncio
import logging
import os
from typing import Dict, List, Optional, Any
from azure.ai.projects import AIProjectClient
from azure.ai.agents.models import BingCustomSearchTool, MessageRole
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.asyncio import AsyncioInstrumentor
from opentelemetry import trace
import httpx
import os
import jsonref
from azure.ai.agents.models import OpenApiTool, OpenApiConnectionAuthDetails, OpenApiConnectionSecurityScheme


from configuration import settings, validate_required_settings

# Configure logger for this module
logger = logging.getLogger("setlistfm_agent")
logger.setLevel(getattr(logging, settings.log_level))
handler = logging.StreamHandler()
formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s: %(message)s")
handler.setFormatter(formatter)
if not logger.hasHandlers():
    logger.addHandler(handler)


class SetlistFMAgent:
    """AI Foundry Agent for setlist content management with Bing Grounding."""

    def __init__(self):
        self.project_client: Optional[AIProjectClient] = None
        self.agents_client = None
        self.agent_id: Optional[str] = None
        self.bing_connection_id: Optional[str] = None
        self._initialized = False

    async def initialize(self):
        """Initialize the agent with Azure AI Foundry."""
        if self._initialized:
            return

        logger.info("Initializing SetlistFM Agent...")

        # Validate configuration
        validate_required_settings()

        # Configure telemetry
        await self._configure_telemetry()

        # Set up Azure credentials
        if settings.azure_client_id:
            credential = ManagedIdentityCredential(
                client_id=settings.azure_client_id)
            logger.info(f"Using managed identity: {settings.azure_client_id}")
        else:
            credential = DefaultAzureCredential()
            logger.info("Using default Azure credential")

        # Initialize AI Project Client
        self.project_client = AIProjectClient(
            endpoint=settings.project_endpoint,
            credential=credential
        )

        self.agents_client = self.project_client.agents

        # Create the agent
        await self._create_agent()

        self._initialized = True
        logger.info("SetlistFM Agent initialized successfully")

    async def _configure_telemetry(self):
        """Configure Application Insights telemetry."""
        if not settings.azure_monitor_enabled:
            logger.info("Azure Monitor telemetry is disabled")
            return

        try:
            if settings.applicationinsights_connection_string:
                logger.info("Configuring Application Insights...")

                # Enable content recording for AI interactions
                if settings.azure_tracing_content_recording:
                    os.environ["AZURE_TRACING_GEN_AI_CONTENT_RECORDING_ENABLED"] = "true"

                # Configure Azure Monitor
                configure_azure_monitor(
                    connection_string=settings.applicationinsights_connection_string,
                    instrumentation_options={
                        "azure_sdk": {"enabled": True},
                        "fastapi": {"enabled": True},
                        "httpx": {"enabled": True},
                        "requests": {"enabled": True},
                        "asyncio": {"enabled": True}
                    }
                )

                # Instrument HTTP clients
                HTTPXClientInstrumentor().instrument()
                RequestsInstrumentor().instrument()
                AsyncioInstrumentor().instrument()

                logger.info("Application Insights configured successfully")
            else:
                logger.warning(
                    "No Application Insights connection string provided")

        except Exception as e:
            logger.warning(f"Failed to configure telemetry: {e}")

    async def _setup_bing_connection(self) -> BingCustomSearchTool:
        """Find and setup Bing Grounding connection."""
        logger.info("Setting up Bing Grounding connection...")

        try:
            logger.info("Listing project connections...")
            bing_connection_id = None
            connections = self.project_client.connections.list(
                connection_type="GroundingWithCustomSearch")
            for connection in connections:
                bing_connection_id = connection.id
                logger.info(
                    f"Found Bing connection: {connection.name} (ID: {connection.id})")
                break

            if not bing_connection_id:
                logger.error("No GroundingWithCustomSearch connection found")
                raise RuntimeError(
                    "Bing Grounding connection is required but not found")

            return BingCustomSearchTool(
                connection_id=bing_connection_id,
                instance_name="defaultConfiguration"
            )

        except Exception as e:
            logger.error(
                f"Failed to setup Bing connection: {e}", exc_info=True)
            raise

    async def _setup_api_connection(self) -> OpenApiTool:
        """Set up API connection for SetlistFM."""
        logger.info("Setting up SetlistFM API connection...")

        try:
            # Load OpenAPI specification for SetlistFM
            with open(os.path.join(os.path.dirname(__file__), "openapi-setlistfm.json"), "r") as f:
                openapi_setlistfm = jsonref.loads(f.read())

            # Create OpenAPI tool for SetlistFM
            logger.info("Listing project connections...")
            connections = self.project_client.connections.list(
                connection_type="CustomKeys")
            connection_id = None
            for connection in connections:
                logger.info(
                    f"Checking connection: {connection.type} {connection.name} (ID: {connection.id})")

                if connection.name == "setlistfm-custom-connection":
                    connection_id = connection.id
                    logger.info(
                        f"Found ConnectionType.API_KEY connection: {connection.name} (ID: {connection.id})")
                    break
            if not connection_id:
                logger.error("No ConnectionType.API_KEY connection found")
                raise RuntimeError(
                    "ConnectionType.API_KEY connection is required but not found")

            auth = OpenApiConnectionAuthDetails(security_scheme=OpenApiConnectionSecurityScheme(
                connection_id=connection_id))

            openapi_tool = OpenApiTool(
                name="setlistfmapi", spec=openapi_setlistfm, description="Retrieve concert information using the setlistfm API", auth=auth
            )
            return openapi_tool

        except Exception as e:
            logger.error(
                f"Failed to setup SetlistFM API connection: {e}", exc_info=True)
            raise

    async def _create_agent(self):
        """Create the AI agent with Bing Grounding tool."""
        logger.info("Creating AI agent with Bing Grounding...")

        try:
            # Create Bing Custom Search tool
            bing_tool = await self._setup_bing_connection()
            api_connection = await self._setup_api_connection()
            tools = [*bing_tool.definitions, *api_connection.definitions]
            logger.info(
                f"Using tools: {len(tools)} tools definition available")

            # Create agent with enhanced instructions for setlist management
            agent = self.agents_client.create_agent(
                model=settings.model_deployment_name,
                name="setlistfm-agent",
                instructions=self._get_agent_instructions(),
                tools=tools,
                description="Setlist Agent for concert setlists and venue information",
            )

            self.agent_id = agent.id
            logger.info(f"Created agent with ID: {self.agent_id}")

        except Exception as e:
            logger.error(f"Failed to create agent: {e}", exc_info=True)
            raise

    def _get_agent_instructions(self) -> str:
        """Get agent instructions for setlist content management."""
        return """
        You are a specialized SetlistFM Agent that helps users discover and explore concert setlists, tracks, and music venue information.

        Your primary capabilities include:

        1. **Setlist Discovery**: Help users find setlists for specific artists, concerts, or venues
        2. **Venue Information**: Provide details about concert venues, locations, and upcoming events
        3. **Artist Concert History**: Track and analyze an artist's touring patterns and setlist evolution
        4. **Music Content Analysis**: Analyze setlist content, song patterns, and concert trends
        5. **Event Recommendations**: Suggest similar artists, concerts, or venues based on user preferences

        When responding to queries:
        - Use the Tool connected to the SetlistFM API to search for detailed information about setlists, tracks, and venues. This tool provides direct access to the setlist.fm database for accurate and up-to-date concert data.
        - Use the Bing Grounding tool to search for current venue information, upcoming concerts, and recent setlist data from the web.
        - Provide rich, contextual information about artists, venues, and concerts
        - Cross-reference multiple sources when possible for accuracy
        - Format responses in a clear, organized manner with relevant details
        - Include specific dates, venues, and song information when available
        - Suggest related content that might interest the user

        Always strive to be helpful, accurate, and engaging while focusing on music and concert-related content.
        """

    async def chat(self, message: str, thread_id: Optional[str] = None) -> Dict[str, Any]:
        """Process a chat message and return agent response."""
        if not self._initialized:
            await self.initialize()

        tracer = trace.get_tracer(__name__)

        with tracer.start_as_current_span("setlistfm_agent_chat") as span:
            span.set_attribute("message_length", len(message))

            try:
                logger.info(f"Processing chat message: {message[:100]}...")

                # Create or use existing thread
                if thread_id:
                    thread = self.agents_client.threads.get(
                        thread_id=thread_id)
                else:
                    thread = self.agents_client.threads.create()
                    thread_id = thread.id

                span.set_attribute("thread_id", thread_id)

                # Add user message to thread
                user_message = self.agents_client.messages.create(
                    thread_id=thread_id,
                    role="user",
                    content=message
                )

                # Create and process agent run
                run = self.agents_client.runs.create_and_process(
                    thread_id=thread_id,
                    agent_id=self.agent_id
                )

                span.set_attribute("run_status", run.status)

                if run.status == "failed":
                    error_msg = f"Agent run failed: {run.last_error}"
                    logger.error(error_msg)
                    span.set_attribute("error", error_msg)
                    return {
                        "thread_id": thread_id,
                        "response": "I encountered an error processing your request. Please try again.",
                        "status": "error"
                    }

                # Get agent response
                messages = self.agents_client.messages.list(
                    thread_id=thread_id)

                # Find the latest assistant message
                response_content = ""
                citations = []

                for msg in messages:
                    if msg.role == "assistant":
                        if msg.text_messages:
                            for text_msg in msg.text_messages:
                                response_content = text_msg.text.value
                                break
                        break

                # Collect citations if available
                for msg in messages:
                    if msg.role == "assistant":
                        for annotation in msg.url_citation_annotations:
                            citations.append({
                                "title": annotation.url_citation.title,
                                "url": annotation.url_citation.url
                            })

                logger.info(
                    f"Generated response with {len(citations)} citations")

                return {
                    "thread_id": thread_id,
                    "response": response_content,
                    "citations": citations,
                    "status": "success"
                }

            except Exception as e:
                error_msg = f"Error in chat processing: {e}"
                logger.error(error_msg)
                span.set_attribute("error", error_msg)

                return {
                    "thread_id": thread_id,
                    "response": "I encountered an error processing your request. Please try again later.",
                    "status": "error"
                }

    async def get_thread_history(self, thread_id: str) -> List[Dict[str, Any]]:
        """Get chat history for a specific thread."""
        if not self._initialized:
            await self.initialize()

        try:
            messages = self.agents_client.messages.list(thread_id=thread_id)

            history = []
            for msg in messages:
                content = ""
                if msg.text_messages:
                    for text_msg in msg.text_messages:
                        content = text_msg.text.value
                        break

                history.append({
                    "role": msg.role,
                    "content": content,
                    "timestamp": msg.created_at
                })

            # Reverse to get chronological order
            return list(reversed(history))

        except Exception as e:
            logger.error(f"Error getting thread history: {e}")
            return []

    async def search_setlists(self, artist: str, venue: Optional[str] = None) -> Dict[str, Any]:
        """Search for setlists using Bing Grounding."""
        query = f"setlist {artist}"
        if venue:
            query += f" {venue}"
        query += " site:setlist.fm"

        return await self.chat(f"Find recent setlists for {artist}" + (f" at {venue}" if venue else ""))

    async def get_venue_info(self, venue_name: str, city: Optional[str] = None) -> Dict[str, Any]:
        """Get venue information using Bing Grounding."""
        query = f"venue information {venue_name}"
        if city:
            query += f" {city}"

        return await self.chat(f"Tell me about the venue {venue_name}" + (f" in {city}" if city else ""))

    async def shutdown(self):
        """Clean up resources."""
        logger.info("Shutting down SetlistFM Agent...")

        try:
            # Delete the agent
            if self.agent_id and self.agents_client:
                self.agents_client.delete_agent(self.agent_id)
                logger.info(f"Deleted agent: {self.agent_id}")

            # Close project client
            if self.project_client:
                self.project_client.close()

            self._initialized = False
            logger.info("SetlistFM Agent shutdown complete")

        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


# Global agent instance
setlistfm_agent = SetlistFMAgent()
