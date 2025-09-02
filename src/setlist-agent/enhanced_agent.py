"""
Enhanced Setlist Agent with Spotify OAuth Integration
"""
from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.openai import OpenAIInstrumentor
from opentelemetry.instrumentation.asyncio import AsyncioInstrumentor
import os
import asyncio
import logging
import sys
from opentelemetry import trace
import semantic_kernel as sk
from dotenv import load_dotenv
from azure.identity import ManagedIdentityCredential
from semantic_kernel.utils.logging import setup_logging
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.agents import ChatCompletionAgent, ChatHistoryAgentThread
from semantic_kernel.connectors.ai.azure_ai_inference import AzureAIInferenceChatCompletion
from semantic_kernel.connectors.mcp import MCPSsePlugin
from semantic_kernel.connectors.mcp import MCPStreamableHttpPlugin

from semantic_kernel.functions import KernelArguments

from spotify_auth import SpotifyAuthManager, spotify_auth
import chainlit as cl
from opentelemetry import trace

# Configure logger for this module to ensure all messages are shown
logger = logging.getLogger("setlist_agent.enhanced_agent")
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s: %(message)s")
handler.setFormatter(formatter)
if not logger.hasHandlers():
    logger.addHandler(handler)


class EnhancedSetlistAgent:
    """Enhanced Setlist Agent with Spotify OAuth integration."""

    def __init__(self):
        self._kernel = sk.Kernel()
        self._agent = None
        self.plugin_setlistfm = None
        self.plugin_spotify = None
        logging.getLogger("kernel").setLevel(logging.DEBUG)

        # Validate required environment variables
        required_vars = [
            "AZURE_AI_INFERENCE_API_KEY",
            "AZURE_AI_INFERENCE_ENDPOINT",
            "MODEL_DEPLOYMENT_NAME"
        ]

        for var in required_vars:
            if not os.getenv(var):
                logger.error(f"{var} must be set")
                raise ValueError(f"{var} must be set")

        # Add Azure AI Inference service
        ai_inference_service = AzureAIInferenceChatCompletion(
            ai_model_id=os.getenv(
                "MODEL_DEPLOYMENT_NAME"),  # type: ignore
            api_key=os.getenv("AZURE_AI_INFERENCE_API_KEY"),
            endpoint=os.getenv("AZURE_AI_INFERENCE_ENDPOINT"),
        )
        self._kernel.add_service(ai_inference_service)

    def span(self, name: str):
        """Create a span for tracing."""
        tracer = trace.get_tracer(__name__)
        self._calls += 1
        return tracer.start_as_current_span(name=f"{name} {self._thread.id} / {self._calls}")

    async def initialize_agent(self):
        """Initialize the agent with necessary plugins and services."""
        logger.info("Initializing Enhanced SetlistAgent with plugins...")
        # Register Setlist FM MCP plugin
        await self.setup_setlistfm_plugin()
        await self._configure_telemetry()

        # Create the chat completion agent
        model_deployment_name = os.getenv("MODEL_DEPLOYMENT_NAME", "")
        logger.info(f"Using model deployment: {model_deployment_name}")

        # Adjust function choice behavior based on model
        if model_deployment_name and "phi-4" in model_deployment_name.lower():
            logger.info(
                "Using Phi-4 model - ensuring auto tool choice is properly configured")
            function_choice = FunctionChoiceBehavior.Auto(
                tool_call_parser="default", enable_auto_tool_choice=True)
        else:
            logger.info(
                "Using non-Phi-4 model - using default auto function choice behavior")
            function_choice = FunctionChoiceBehavior.Auto()

        self._agent = ChatCompletionAgent(
            kernel=self._kernel,
            name="enhanced_setlist_agent",
            function_choice_behavior=function_choice,
            instructions=self._get_agent_instructions())

        self._thread = ChatHistoryAgentThread(chat_history=ChatHistory())
        logger.info(f"New thread created with ID: {self._thread.id}")
        logger.info("Enhanced SetlistAgent initialized successfully.")
        self._calls = 0

    async def _configure_telemetry(self):

        logger = logging.getLogger(__name__)
        logger.info("Configuring telemetry for Enhanced SetlistAgent...")
        try:
            endpoint = os.environ["PROJECT_ENDPOINT"]
        except KeyError:
            logger.error("PROJECT_ENDPOINT environment variable is not set.")
            return
        logger.info("Project Endpoint: %s", endpoint)
        # Configure Application Insights if connection string is available
        from azure.identity import DefaultAzureCredential
        managed_identity = os.environ["AZURE_CLIENT_ID"]
        logger.info(
            f"Using managed identity client ID: {managed_identity} for Azure services")
        with DefaultAzureCredential() as credential:
            logger.info(f"Using {type(credential)} for Azure services")
            from azure.ai.projects import AIProjectClient
            with AIProjectClient(endpoint=endpoint, credential=credential) as project_client:
                logger.info(
                    "Retrieving Application Insights connection string...")
                connection_string = project_client.telemetry.get_connection_string()
                if connection_string:
                    logger.info(
                        "Application Insights connection string retrieved successfully.")
                else:
                    logger.warning(
                        "No Application Insights connection string found in project telemetry.")

                # connection_string = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
                logger.info("Configuring telemetry for Enhanced SetlistAgent...%s",
                            connection_string or "No connection string provided")
                if connection_string:
                    # Configure Application Insights with the connection string
                    try:
                        logger.info("Enabling logging of message contents...")
                        os.environ["AZURE_TRACING_GEN_AI_CONTENT_RECORDING_ENABLED"] = "true"
                        logger.info(
                            f"configure azure monitor {connection_string}")
                        configure_azure_monitor(connection_string=connection_string,  instrumentation_options={
                            "azure_sdk": {"enabled": True},
                            "django": {"enabled": True},
                            "fastapi": {"enabled": False},
                            "flask": {"enabled": True},
                            "psycopg2": {"enabled": False},
                            "requests": {"enabled": True},
                            "urllib": {"enabled": True},
                            "urllib3": {"enabled": True},
                        })
                        logger.info(
                            "Application Insights configured for Setlist Agent")
                    except Exception as e:
                        logger.warning(
                            f"Failed to configure Application Insights (configure_azure_monitor): {e}", exc_info=True)

            # Instrument HTTP clients and FastAPI
        if os.getenv("AZURE_MONITOR_OPENTELEMETRY_ENABLED") == "true":
            try:
                logger.info("*** Instrumenting HTTP clients and HTTPX")
                OpenAIInstrumentor().instrument()
                RequestsInstrumentor().instrument()
                HTTPXClientInstrumentor().instrument()
                AsyncioInstrumentor().instrument()
                logger.info(
                    "OpenTelemetry instrumentation configured for Setlist Agent")
            except Exception as e:
                logger.warning(
                    f"Failed to configure OpenTelemetry instrumentation: {e}")

    async def setup_setlistfm_plugin(self):
        """Setup Setlist FM plugin."""
        logger.info("Setting up Setlist FM plugin...")

        setlistfm_mcp_url = os.getenv("SETLISTFM_MCP_URL")
        if not setlistfm_mcp_url:
            logger.error("SETLISTFM_MCP_URL environment variable is not set.")
            raise ValueError(
                "SETLISTFM_MCP_URL must be set in environment variables.")
        try:
            self.plugin_setlistfm = MCPStreamableHttpPlugin(
                name="setlistfm_mcp_client",
                description="Setlist FM Plugin for concert and setlist data",
                url=setlistfm_mcp_url
            )
            await self.plugin_setlistfm.connect()
            self._kernel.add_plugin(self.plugin_setlistfm)
            logger.info("Setlist FM plugin connected successfully.")
        except Exception as e:
            logger.error(f"Failed to connect Setlist FM plugin: {e}")
            raise RuntimeError(f"Failed to connect Setlist FM plugin: {e}")

    async def _setup_spotify_plugin(self, access_token: str, refresh_token: str, expires_at: int):
        """Setup Spotify plugin with appropriate authentication."""
        logger.info("Setting up Spotify plugin with authentication...")

        spotify_mcp_url = os.getenv("SPOTIFY_MCP_URL")
        if not spotify_mcp_url:
            logger.error("SPOTIFY_MCP_URL environment variable is not set.")
            raise ValueError(
                "SPOTIFY_MCP_URL must be set in environment variables.")
        headers = {}
        headers["Authorization"] = f"Bearer {access_token}"
        headers["X-Spotify-Token"] = access_token
        logger.info(
            f"Using Chainlit OAuth token for Spotify MCP {access_token}")

        # await spotify_auth.refresh_token()

        logger.info(
            f"Connecting to Spotify MCP at {spotify_mcp_url} with headers: {headers}")

        self.plugin_spotify = MCPSsePlugin(
            name="spotify_mcp_client",
            description="Spotify Plugin with OAuth support",
            url=spotify_mcp_url,
            headers=headers
        )
        await self.plugin_spotify.connect()
        self._kernel.add_plugin(self.plugin_spotify)

    def _get_agent_instructions(self) -> str:
        """Get agent instructions based on authentication status."""
        base_instructions = """
        You are a helpful music assistant that provides information about artists, concerts, setlists, and Spotify data.
        You can search for artists, find setlists from concerts, provide venue information, and access Spotify features.
        
        When asked about an artist's concerts or setlists,always use the SetlistFM plugin to search for that information.
        For Spotify-related queries, always use the Spotify plugin.
        
        Always try to be helpful and provide as much relevant information as possible.
        """

        logger.info("Checking Spotify authentication status... is_authenticated: " +
                    str(spotify_auth.is_authenticated()))

        if spotify_auth.is_authenticated():
            user_profile = cl.user_session.get("spotify_user_profile")
            user_name = user_profile.get(
                "display_name", "user") if user_profile else "user"

            auth_instructions = f"""
            
            IMPORTANT: The user is authenticated with Spotify as {user_name}.
            You have access to their personal Spotify data including:
            - Personal playlists
            - Saved tracks and albums
            - Listening history
            - Currently playing tracks
            - Playback control (if available)
            
            When the user asks about "my music", "my playlists", or similar personal queries,
            use the Spotify plugin to access their personal data.
            """
            logger.info("instructions: " +
                        base_instructions + auth_instructions)
            return base_instructions + auth_instructions
        else:
            unauth_instructions = """
            
            NOTE: The user is not authenticated with Spotify.
            You can only access public Spotify data like:
            - Artist information
            - Public playlists
            - Track search
            
            If the user asks for personal Spotify data, suggest they authenticate first
            by typing "/spotify_login" to unlock personalized features.
            """
            logger.info("instructions: " +
                        base_instructions + unauth_instructions)
            # Return base instructions with unauthenticated notes
            return base_instructions + unauth_instructions

    async def refresh_spotify_connection(self, access_token: str = None, refresh_token: str = None, expires_at: int = None):
        """Refresh Spotify plugin connection with updated auth."""
        if self.plugin_spotify:
            # Close existing connection
            await self.plugin_spotify.close()
            self._kernel.remove_plugin("Spotify")

        new_token = await spotify_auth.refresh_token(refresh_token=refresh_token)

        # Re-setup with new auth
        logger.info("Refreshing Spotify plugin connection...")
        await self._setup_spotify_plugin(access_token=new_token, refresh_token=refresh_token, expires_at=expires_at)

        # Update agent instructions
        if self._agent:
            self._agent.instructions = self._get_agent_instructions()

    async def chat(self, user_input: str, thread: ChatHistoryAgentThread) -> str:
        """Process user input and return agent response."""
        logger.info(f"Processing user input: {user_input}")
        if not self._agent:
            await self.initialize_agent()

        # Check for special commands
        if user_input.startswith("/"):
            return await self._handle_command(user_input)

        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span(name="enhanced-agent-chat"):
            try:
                joined_response = []
                async for response in self._agent.invoke(messages=user_input, thread=thread):
                    logger.info(f"chat response: {response.to_dict()}")
                    joined_response.append(str(response.content))
                return "\n".join(joined_response)
            except Exception as e:
                logger.error(f"Error in chat processing: {e}")
                return f"I encountered an error: {str(e)}"

    async def _handle_command(self, command: str) -> str:
        """Handle special commands."""
        logger.info(f"Handling command: {command}")
        if command.startswith("/spotify_login"):
            return await self._handle_spotify_login()
        elif command.startswith("/spotify_logout"):
            return await self._handle_spotify_logout()
        elif command.startswith("/spotify_profile"):
            return await self._handle_spotify_profile()
        elif command.startswith("/help"):
            return self._get_help_message()
        else:
            return f"Unknown command: {command}. Type /help for available commands."

    async def _handle_spotify_login(self) -> str:
        """Handle Spotify login command."""
        logger.info("Handling Spotify login command...")
        if spotify_auth.is_authenticated():
            user_profile = await spotify_auth.get_user_profile()
            if user_profile:
                cl.user_session.set("spotify_user_profile", user_profile)
                user_name = user_profile.get("display_name", "Unknown")
                return f"You're already logged in to Spotify as {user_name}!"

        # Generate auth URL
        user_id = cl.user_session.get("id", "unknown")
        auth_url = spotify_auth.generate_auth_url(user_id)

        return f"""
To access your personal Spotify data, please authenticate:

🎵 **[Click here to connect your Spotify account]({auth_url})**

After authentication, you'll have access to:
- Your personal playlists
- Saved tracks and albums  
- Listening history
- Currently playing tracks
- Playback controls

Once you've completed the OAuth flow, come back and I'll have access to your personal music data!
"""

    async def _handle_spotify_logout(self) -> str:
        """Handle Spotify logout command."""
        if not spotify_auth.is_authenticated():
            return "You're not currently logged in to Spotify."

        spotify_auth.logout()
        await self.refresh_spotify_connection()
        return "You've been logged out from Spotify. Your session data has been cleared."

    async def _handle_spotify_profile(self) -> str:
        """Handle Spotify profile command."""
        if not spotify_auth.is_authenticated():
            return "You're not logged in to Spotify. Use /spotify_login to authenticate."

        profile = await spotify_auth.get_user_profile()
        if not profile:
            return "Couldn't retrieve your Spotify profile. You may need to re-authenticate."

        cl.user_session.set("spotify_user_profile", profile)

        followers = profile.get("followers", {}).get("total", "Unknown")
        country = profile.get("country", "Unknown")
        product = profile.get("product", "Unknown")

        return f"""
🎵 **Your Spotify Profile**
- **Name**: {profile.get('display_name', 'Unknown')}
- **Email**: {profile.get('email', 'Not available')}
- **Country**: {country}
- **Subscription**: {product}
- **Followers**: {followers}
- **Profile URL**: {profile.get('external_urls', {}).get('spotify', 'Not available')}
"""

    def _get_help_message(self) -> str:
        """Get help message with available commands."""
        return """
🎵 **Available Commands:**

**Spotify Authentication:**
- `/spotify_login` - Connect your Spotify account for personalized features
- `/spotify_logout` - Disconnect from Spotify
- `/spotify_profile` - View your Spotify profile information

**General:**
- `/help` - Show this help message

**What I can do:**
- Search for artists and their setlists
- Find concert information and venues
- Access Spotify music data (public or personal if authenticated)
- Provide music recommendations and information

Just ask me about any artist, concert, or music-related topic!
"""

    async def shutdown(self):
        """Shutdown the agent and clean up resources."""
        logger.info("Shutting down Enhanced SetlistAgent...")

        try:
            if self.plugin_setlistfm:
                logger.info("Closing SetlistFM plugin connection...")
                await self.plugin_setlistfm.close()

            if self.plugin_spotify:
                logger.info("Closing Spotify plugin connection...")
                await self.plugin_spotify.close()

            logger.info("Enhanced SetlistAgent shutdown complete.")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
