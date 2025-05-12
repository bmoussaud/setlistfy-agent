
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
import logging
from typing import Optional, Dict
from opentelemetry import trace
from enhanced_agent import EnhancedSetlistAgent
from spotify_auth import spotify_auth
import chainlit as cl
from dotenv import load_dotenv
import os

# Application Insights configuration

# Load environment variables
load_dotenv()


# Configure root logger for the application
logger = logging.getLogger("setlist_agent")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s: %(message)s")
handler.setFormatter(formatter)
if not logger.hasHandlers():
    logger.addHandler(handler)

# Optionally, reduce verbosity of Azure SDK logs
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(
    logging.WARNING)


@cl.on_chat_start
async def on_chat_start():
    """Initialize chat session with welcome message and authentication status."""
    logger.info("Chat session started.")
    # Get the authenticated user
    user = cl.user_session.get("user")
    logger.info(f"Authenticated user: {user.identifier if user else 'None'}")
    logger.info(
        f"user.metadata.get('provider'): {user.metadata.get('provider') if user else 'None'}")
    agent = EnhancedSetlistAgent()
    await agent.initialize_agent()

    if user:
        # Store in user session for later use
        logger.info(f"User {user.identifier} is authenticated with Spotify.")
        cl.user_session.set("spotify_user_data",
                            user.metadata.get("spotify_data", {}))
        logger.info(
            f"User {user.identifier} Spotify data: {user.metadata.get('spotify_data', {})}")
        # logger.info(
        #    f"User {user.identifier} Spotify token: {user.token}")
        # Store token in user session for later use
        cl.user_session.set("spotify_token", user.metadata.get("access_token"))
        cl.user_session.set("spotify_refresh_token",
                            user.metadata.get("refresh_token"))
        cl.user_session.set("spotify_expires_at",
                            user.metadata.get("expires_at"))
        logger.info(f"User {user.identifier} Spotify token stored in session.")

        # Show welcome message with Spotify info
        user_name = user.display_name or "there"
        await cl.Message(
            content=f"🎉 Welcome back {user_name}! You're connected to Spotify.\n\n"
            f"I have access to your personal music data. Ask me about your playlists, "
            f"saved tracks, listening history, and more!"
        ).send()

        # Initialize agent with Spotify authentication
        logger.info(
            f"Initializing agent with Spotify auth for user: {user.identifier}")
        await agent.refresh_spotify_connection(access_token=user.metadata.get("access_token"),
                                               refresh_token=user.metadata.get(
            "refresh_token"),
            expires_at=user.metadata.get("expires_at"))
        # Display the Spotify access token in the chat (for debugging/demo purposes)
        access_token = cl.user_session.get("spotify_token")
        # if access_token:
        #    await cl.Message(
        #        content=f"🔑 **Your Spotify Access Token:**\n```\n{access_token}\n```"
        #    ).send()
    else:
        # User is not authenticated, show login prompt
        await cl.Message(
            content="🔒 Please log in to Spotify to use the Setlist Agent features.").send()
        # Redirect to Spotify authentication
        await cl.redirect(spotify_auth.get_auth_url())

    # Initialize agent and create thread
    cl.user_session.set("agent", agent)
    cl.user_session.set("thread", agent.new_thread())
    cl.user_session.set("calls", 0)
    logger.info("Setlist Agent initialized and chat thread created.")


@cl.on_message
async def on_message(message: cl.Message):
    """Handle incoming messages with enhanced features."""

    tracer = trace.get_tracer(__name__)
    agent = cl.user_session.get("agent", None)
    thread = cl.user_session.get("thread", None)

    if thread is None:
        logger.info("No thread found in user session, creating a new one.")
        cl.user_session.set("thread", agent.new_thread())
        thread = cl.user_session.get("thread", None)

    calls = cl.user_session.get("calls", None)
    if calls is None:
        calls = 0
        cl.user_session.set("calls", calls)

    calls = calls + 1
    cl.user_session.set("calls", calls)
    span = f"setlistfy-agent-on_message {thread.id if thread else '0000'}/{calls}"
    logger.info(f"Starting span: {span}")
    with tracer.start_as_current_span(name=span):
        logger.info(f"Received message: {message.content}")
        logger.info(f"Current thread: {thread.id if thread else 'None'}")
        try:
            # Show thinking message to user
            msg = await cl.Message("🤔 Thinking...", author="agent").send()
            # Process message through enhanced agent
            response = await agent.chat(user_input=message.content, thread=thread)
            logger.info(f"Agent response: {response}")
            # Update message with response
            msg.content = response
            await msg.update()

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            await cl.Message(content=f"❌ Error: {str(e)}").send()


@cl.oauth_callback
async def oauth_callback(
    provider_id: str,
    token: str,
    raw_user_data: Dict[str, str],
    default_user: cl.User,
) -> Optional[cl.User]:
    """Handle OAuth callback for Spotify authentication."""
    logger.error(f"OAuth callback received for provider: {provider_id}")
    logger.error(f"Token: {token}")
    logger.error(f"Raw user data: {raw_user_data}")
    logger.error(f"Default user: {default_user}")
    # https://spotify.server.open-mcp.org/latest/mcp?FORWARD_VAR_OPEN_MCP_BASE_URL=https%3A%2F%2Fapi.example.com&&OAUTH2_TOKEN=BQB2YyM7D2bqSe5A1kQ2KXW6mhvAFvZiXSWmsZ0rujLS_QNb3Veg8i9uVAKD5ugR4_LdLXnfpa4mn7SI24PSJx_oD4GEXw4Gad1rNdzXAW_mZONprhaaVpbb-kmktlgLW2p51If80ZwzhwF7AFZBJ78SMcb0aIr_CRNYBTSzEXaZuM_5YAPix_DYUn6GiFrAHADnAIxhEqYpms5OXx2jHwCOZ9Z8-J4VRi8X_vgk2mkLU1hMSnvYJA9G9txIO2pFKx_LeUMVCJouF8Y46oB1bRJ4mIhyoLlcvX19U6N4AWpd4JBhEZ7yZcOUAMVOJA
    if provider_id == "spotify":
        # Create user with Spotify info
        return cl.User(
            identifier=raw_user_data.get("id", default_user.identifier),
            display_name=raw_user_data.get(
                "display_name", default_user.display_name),
            metadata={
                "provider": "spotify",
                "spotify_data": raw_user_data,
                "token": token,
                "access_token": token.get("access_token"),
                "refresh_token": token.get("refresh_token"),
                "expires_at": token.get("expires_at"),
                **default_user.metadata
            }
        )

    return default_user


if __name__ == "__main__":
    # Chainlit will automatically run the application
    pass
