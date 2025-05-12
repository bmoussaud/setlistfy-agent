from opentelemetry import trace
import json
from urllib import response
from fastmcp import FastMCP
from dotenv import load_dotenv
import os
import json

import spotipy
import logging

from starlette.requests import Request
from starlette.responses import JSONResponse
import httpx
from fastmcp.server.dependencies import get_access_token, AccessToken
from fastmcp.server.auth import BearerAuthProvider
from fastmcp.server.auth.auth import (
    ClientRegistrationOptions,
    OAuthProvider,
    RevocationOptions,
)
from fastmcp import FastMCP, Context
from fastmcp.server.dependencies import get_http_request
from fastmcp.server.middleware import Middleware, MiddlewareContext

# Application Insights configuration
from azure.monitor.opentelemetry import configure_azure_monitor


from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.starlette import StarletteInstrumentor


def configure_telemetry(mcp: FastMCP):
    """Configure OpenTelemetry for the application."""
    # Configure Application Insights if connection string is available
    logger.info("Configuring OpenTelemetry for SetlistFM MCP Server")
    connection_string = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
    if connection_string is None:
        logger.warning(
            "APPLICATIONINSIGHTS_CONNECTION_STRING not found, Application Insights not configured")
        return

    try:
        configure_azure_monitor(connection_string=connection_string)
        # Optionally, reduce verbosity of Azure SDK logs
        logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(
            logging.WARNING)
        logger.info("Application Insights configured for SetlistFM MCP Server")
    except Exception as e:
        logger.warning(
            f"Failed to configure Application Insights (configure_azure_monitor): {e}", exc_info=True)

    # Instrument HTTP clients
    try:
        logger.info(
            "Instrumenting HTTP clients for OpenTelemetry RequestsInstrumentor")
        RequestsInstrumentor().instrument()
        logger.info(
            "Instrumenting HTTP clients for OpenTelemetry HTTPXClientInstrumentor")
        HTTPXClientInstrumentor().instrument()

        logger.info(
            "OpenTelemetry instrumentation configured for SetlistFM MCP Server")
    except Exception as e:
        logger.warning(
            f"Failed to configure OpenTelemetry instrumentation: {e}")


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class LoggingMiddleware(Middleware):
    """Middleware that logs all MCP operations."""

    async def on_message(self, context: MiddlewareContext, call_next):
        """Called for all MCP messages."""
        logger.info(f"Processing {context.method} from {context.source}")
        logger.info(f"Context: {context}")
        result = await call_next(context)

        logger.info(f"Completed {context.method}")
        return result

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        """Called when a tool is called."""
        logger.info(
            f"Calling tool: {context.message.tool_name} with args: {context.message.args}")
        result = await call_next(context)
        logger.info(f"Tool call completed: {context.message.tool_name}")
        return result


def extract_access_token() -> str:
    """
    Extract the access token from the request headers.
    Tries 'Authorization' (Bearer) and 'X-Spotify-Token'.
    Returns the token string or an empty string if not found.
    """
    request: Request = get_http_request()
    # logger.info(f"Request Headers: {request.headers}")
    headers = request.headers
    # logger.info(f"Request Headers: {headers}")
    for header, value in headers.items():
        logger.info(f"Header: {header} = {value}")

    auth_header = headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.replace("Bearer ", "", 1)
    else:
        token = headers.get("X-Spotify-Token", "")

    logger.info(f"Extracted token: {token}")
    return token or ""


def spotipy_instance() -> spotipy.Spotify:
    """ Get an instance of the Spotipy client with the current access token. """
    return spotipy.Spotify(auth=extract_access_token())


"""
Spotify MCP Server Logic
Exposes Spotify API endpoints via Spotipy and FastMCP.
"""


# Configure logger to show all messages (DEBUG and above) with a clear format, even under Gunicorn
logger = logging.getLogger("spotify_mcp_server")
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s: %(message)s")
handler.setFormatter(formatter)
# Always add our handler (Gunicorn may pre-configure handlers, so forcibly add ours)
logger.handlers = []
logger.addHandler(handler)
logger.propagate = False


mcp = FastMCP("Spotify_MCP")
configure_telemetry(mcp)
# mcp.add_middleware(LoggingMiddleware())


# --- Playlist Lifecycle MCP Tools ---
@mcp.tool()
async def spotify_create_playlist(name: str, public: bool = True, description: str = "") -> str:
    """
    Create a new playlist for the current user.
    Args:
        name (str): The name of the playlist.
        public (bool): Whether the playlist is public. Defaults to True.
        description (str): Playlist description. Defaults to empty.
    Returns:
        str: The created playlist object as JSON, or an error message.
    """
    logger.info(f"Creating playlist: {name} (public={public})")
    try:
        user = spotipy_instance().me()
        playlist = spotipy_instance().user_playlist_create(
            user["id"], name, public=public, description=description)
        response = json.dumps(playlist, indent=2)
        logger.info(f"Playlist created successfully: {response}")
        return response
    except Exception as e:
        logger.error(f"Error creating playlist: {e}")
        return f"Error creating playlist: {str(e)}"


@mcp.tool()
async def spotify_add_track_to_playlist(playlist_id: str, track_uri: str) -> str:
    """
    Add a track to a playlist.
    Args:
        playlist_id (str): The Spotify playlist ID.
        track_uri (str): The Spotify track URI (e.g., 'spotify:track:...').
    Returns:
        str: Result message or error.
    """
    logger.info(f"Adding track {track_uri} to playlist {playlist_id}")
    try:
        result = spotipy_instance().playlist_add_items(
            playlist_id, [track_uri])
        response = json.dumps(result, indent=2)
        logger.info(f"Track added successfully: {response}")
        return response
    except Exception as e:
        logger.error(f"Error adding track to playlist: {e}")
        return f"Error adding track to playlist: {str(e)}"


@mcp.tool()
async def spotify_remove_track_from_playlist(playlist_id: str, track_uri: str) -> str:
    """
    Remove a track from a playlist.
    Args:
        playlist_id (str): The Spotify playlist ID.
        track_uri (str): The Spotify track URI (e.g., 'spotify:track:...').
    Returns:
        str: Result message or error.
    """
    logger.info(f"Removing track {track_uri} from playlist {playlist_id}")
    try:
        result = spotipy_instance().playlist_remove_all_occurrences_of_items(
            playlist_id, [track_uri])
        response = json.dumps(result, indent=2)
        logger.info(f"Track removed successfully: {response}")
        return response
    except Exception as e:
        logger.error(f"Error removing track from playlist: {e}")
        return f"Error removing track from playlist: {str(e)}"


@mcp.tool()
async def spotify_delete_playlist(playlist_id: str) -> str:
    """
    Unfollow (delete) a playlist for the current user.
    Args:
        playlist_id (str): The Spotify playlist ID.
    Returns:
        str: Result message or error.
    """
    logger.info(f"Deleting (unfollowing) playlist {playlist_id}")
    try:
        result = spotipy_instance().current_user_unfollow_playlist(playlist_id)
        return json.dumps({"message": "Playlist deleted (unfollowed)", "result": result}, indent=2)
    except Exception as e:
        logger.error(f"Error deleting playlist: {e}")
        return f"Error deleting playlist: {str(e)}"


@mcp.tool()
async def spotify_get_playlist(playlist_id: str) -> str:
    """
    Get details about a specific playlist.
    Args:
        playlist_id (str): The Spotify playlist ID.
    Returns:
        str: The playlist details as JSON, or an error message.
    """
    logger.info(f"Getting playlist details for {playlist_id}")
    try:
        playlist = spotipy_instance().playlist(playlist_id)
        # Remove 'available_markets' fields from playlist and tracks to reduce payload size
        if 'tracks' in playlist and 'items' in playlist['tracks']:
            for item in playlist['tracks']['items']:
                track = item.get('track')
                if track and 'available_markets' in track:
                    track['available_markets'] = None
                if track and 'album' in track and 'available_markets' in track['album']:
                    track['album']['available_markets'] = None
        if 'available_markets' in playlist:
            playlist['available_markets'] = None
        if 'album' in playlist and 'available_markets' in playlist['album']:
            playlist['album']['available_markets'] = None
        response = json.dumps(playlist, indent=2)
        # Log first 100 chars for brevity
        logger.info(
            f"Retrieved playlist details successfully: {response[:100]}...")
        return response
    except Exception as e:
        logger.error(f"Error getting playlist details: {e}")
        return f"Error getting playlist details: {str(e)}"


@mcp.custom_route("/liveness", methods=["GET"])
async def liveness(request: Request) -> JSONResponse:
    logger.info("Liveness check called")
    return JSONResponse({"mcp": mcp.name, "liveness": "ok"})


@mcp.custom_route("/readiness", methods=["GET"])
async def readiness(request: Request) -> JSONResponse:
    logger.info("Readiness check called")
    return JSONResponse({"mcp": mcp.name, "readiness": "ok"})


@mcp.tool()
def spotify_search_track(artist: str, track: str) -> str:
    """
    Search for a track on Spotify by artist and track name.
    Returns a formatted string with the top result.
    If no track is found or an error occurs, returns an error message.

    Args:
        artist (str): The artist name.
        track (str): The track name.

    Returns:
        str: A formatted string with the top search result, or an error message if no track is found or an error occurs.
    """
    query = f"{artist} {track}"
    logger.info(f"Searching for track: {query}")
    try:
        results = spotipy_instance().search(q=query, type='track', limit=1)
        items = results.get('tracks', {}).get('items', [])
        if not items:
            return f"{'message': 'No track found for query: {query}'}"
        track = items[0]
        # Remove available_markets to avoid large data transfer
        track['available_markets'] = None
        track['artists'] = None
        if 'album' in track:
            track['album']['available_markets'] = None
            track['album']['artists'] = None
        response = json.dumps(track, indent=2)
        logger.info(f"Found track: {response}")
        return response
    except Exception as e:
        logger.error(f"Error searching track: {e}")
        return f"Error searching track: {str(e)}"


@mcp.tool()
def spotify_search_artist(query: str) -> str:
    """
    Search for an artist on Spotify by query string.
    Returns a formatted string with the top result.
    If no artist is found or an error occurs, returns an error message.

    Args:
        query (str): The search query string for the artist.

    Returns:
        str: A formatted string with the top search result, or an error message if no artist is found or an error occurs.
    """
    logger.info(f"Searching for artist: {query}")
    try:
        results = spotipy_instance().search(q=query, type='artist', limit=1)
        items = results.get('artists', {}).get('items', [])
        if not items:
            return f"{'message': 'No artist found for query: {query}'}"
        artist = items[0]
        response = json.dumps(artist, indent=2)
        logger.info(f"Found artist: {response}")
        return response
    except Exception as e:
        logger.error(f"Error searching artist: {e}")
        return f"Error searching artist: {str(e)}"


@mcp.tool()
def spotify_get_artist_top_tracks(artist_id: str, country: str = "US") -> str:
    """
    Get the top tracks for an artist by Spotify artist ID.

    Args:
        artist_id (str): The Spotify artist ID.
        country (str, optional): The country code for track popularity. Defaults to "US".

    Returns:
        str: A formatted list of the artist's top tracks, or an error message if not found or on error.
    """
    logger.info(f"Fetching top tracks for artist: {artist_id} in {country}")
    try:
        results = spotipy_instance().artist_top_tracks(artist_id, country=country)
        tracks = results.get('tracks', [])
        if not tracks:
            return f"{'message': 'No top tracks found for artist: {artist_id}'}"
        return json.dumps(tracks, indent=2)
    except Exception as e:
        logger.error(f"Error fetching top tracks: {e}")
        return f"Error fetching top tracks: {str(e)}"


@mcp.tool()
async def spotify_get_user_playlists() -> str:
    """
    Get the playlists for a Spotify user by user ID.
    Returns:
        str: A formatted list of the user's playlists, or an error message if not found or on error.
    """
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("spotify_get_user_playlists") as span:
        span.set_attribute("spotify.query", "query")
        span.set_attribute("spotify.artist", "artist")
        span.set_attribute("spotify.track", "track")
        logger.info(f"Fetching playlists for current authenticated user")
        try:
            playlists = spotipy_instance().current_user_playlists().get('items', [])
            return json.dumps(playlists, indent=2)
        except Exception as e:
            return f"Error fetching user playlists: {str(e)}"


@mcp.tool()
async def spotify_get_user_profile() -> str:
    """
    Get the profile information for a Spotify user by user ID.
    Returns:
        str: A formatted list of the user's information, or an error message if not found or on error.
    """
    logger.info(f"Fetching the authenticated user profile")
    try:
        user_profile = spotipy_instance().me()
        return json.dumps(user_profile, indent=2)
    except Exception as e:
        return f"Error fetching user profile: {str(e)}"

if __name__ == "__main__":
    logger.info("Starting FastMCP server for Spotify")
    # if opentelemetry is configured, use default logging config should be reduced to None else a slow startup time (30s)
    uvicorn_config = {
        "log_config": None,  # Use default logging configuration
    }
    mcp.run(
        transport="sse",
        host="127.0.0.1",
        port=9001,
        log_level="debug",
        uvicorn_config=uvicorn_config
    )
