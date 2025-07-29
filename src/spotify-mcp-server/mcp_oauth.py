

import logging
from fastmcp import FastMCP
from fastmcp.server.auth import BearerAuthProvider

# Configure logging for both uvicorn and fastmcp
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT)

fastmcp_logger = logging.getLogger("fastmcp")
fastmcp_logger.setLevel(logging.DEBUG)

uvicorn_logger = logging.getLogger("uvicorn")
uvicorn_logger.setLevel(logging.DEBUG)


auth = BearerAuthProvider(
    jwks_uri="https://my-identity-provider.com/.well-known/jwks.json",
    issuer="https://accounts.spotify.com",
    algorithm="RS512",
    audience="my-mcp-server"
)

mcp = FastMCP(name="My MCP Server", auth=auth)

@mcp.tool()
async def spotify_create_playlist(name: str, public: bool = True, description: str = "") -> str:
    """
    Create a new Spotify playlist.
    
    Args:
        name (str): The name of the playlist.
        public (bool): Whether the playlist is public or private.
        description (str): A description for the playlist.
    
    Returns:
        str: The ID of the created playlist.
    """
    import spotipy
    from spotipy.oauth2 import SpotifyOAuth

    #sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope="playlist-modify-public"))
    #playlist = sp.user_playlist_create(user=sp.me()['id'], name=name, public=public, description=description)
    return '11111-22222-33333-44444'  # Replace with actual playlist ID

if __name__ == "__main__":
    mcp.run(
        transport="sse",
        port=8000
    )