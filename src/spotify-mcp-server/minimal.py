import logging
from fastmcp import FastMCP
from fastmcp import FastMCP
from fastmcp.server.auth import OAuthProxy
from fastmcp.server.dependencies import get_access_token
# from fastmcp.server.auth.providers.jwt import JWTVerifier

# Configure logging for both uvicorn and fastmcp
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT)

fastmcp_logger = logging.getLogger("fastmcp")
fastmcp_logger.setLevel(logging.DEBUG)

uvicorn_logger = logging.getLogger("uvicorn")
uvicorn_logger.setLevel(logging.DEBUG)



# SpotifyProvider for managing Spotify OAuth authentication
import httpx
from fastmcp.server.auth import TokenVerifier
from fastmcp.server.auth.auth import AccessToken
from fastmcp.server.auth.oauth_proxy import OAuthProxy
from fastmcp.utilities.logging import get_logger
from fastmcp.utilities.types import NotSet, NotSetT

logger = get_logger(__name__)

class SpotifyTokenVerifier(TokenVerifier):
    """Token verifier for Spotify OAuth tokens."""
    def __init__(self, required_scopes=None, timeout_seconds=10):
        super().__init__(required_scopes=required_scopes)
        self.timeout_seconds = timeout_seconds

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                # Get user info from Spotify API
                response = await client.get(
                    "https://api.spotify.com/v1/me",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/json",
                    },
                )
                if response.status_code != 200:
                    logger.debug(
                        "Spotify token verification failed: %d - %s",
                        response.status_code,
                        response.text[:200],
                    )
                    return None
                user_data = response.json()

                # Spotify does not provide scopes in user API, so assume required scopes if successful
                token_scopes = self.required_scopes or ["user-read-email"]

                return AccessToken(
                    token=token,
                    client_id=str(user_data.get("id", "unknown")),
                    scopes=token_scopes,
                    expires_at=None,
                    claims={
                        "sub": str(user_data.get("id")),
                        "display_name": user_data.get("display_name"),
                        "email": user_data.get("email"),
                        "spotify_user_data": user_data,
                    },
                )
        except httpx.RequestError as e:
            logger.debug("Failed to verify Spotify token: %s", e)
            return None
        except Exception as e:
            logger.debug("Spotify token verification error: %s", e)
            return None

class SpotifyProvider(OAuthProxy):
    """Spotify OAuth provider for FastMCP."""
    def __init__(
        self,
        *,
        client_id: str | NotSetT = NotSet,
        client_secret: str | NotSetT = NotSet,
        base_url: str | NotSetT = NotSet,
        redirect_path: str | NotSetT = NotSet,
        required_scopes: list[str] | NotSetT = NotSet,
        timeout_seconds: int | NotSetT = NotSet,
        allowed_client_redirect_uris: list[str] | NotSetT = NotSet,
        client_storage=None,
    ):
        if client_id is NotSet or client_secret is NotSet:
            raise ValueError("client_id and client_secret are required for SpotifyProvider")

        timeout_seconds_final = timeout_seconds if timeout_seconds is not NotSet else 10
        required_scopes_final = required_scopes if required_scopes is not NotSet else ["user-read-email"]
        allowed_client_redirect_uris_final = allowed_client_redirect_uris if allowed_client_redirect_uris is not NotSet else None

        token_verifier = SpotifyTokenVerifier(
            required_scopes=required_scopes_final,
            timeout_seconds=timeout_seconds_final,
        )

        super().__init__(
            upstream_authorization_endpoint="https://accounts.spotify.com/authorize",
            upstream_token_endpoint="https://accounts.spotify.com/api/token",
            upstream_client_id=client_id,
            upstream_client_secret=client_secret,
            token_verifier=token_verifier,
            base_url=base_url,
            redirect_path=redirect_path,
            issuer_url=base_url,
            allowed_client_redirect_uris=allowed_client_redirect_uris_final,
            client_storage=client_storage,
        )
        logger.info(
            "Initialized Spotify OAuth provider for client %s with scopes: %s",
            client_id,
            required_scopes_final,
        )

auth = SpotifyProvider(
    # Your registered app credentials
    client_id="1c3e47d871fe46c1bdc787e487233019",
    client_secret="490e086df740497b90d36362ffa18ec2",
    base_url="http://localhost:8000",
    redirect_path="/auth/callback",
    required_scopes=["user-read-email", "playlist-read-private"],
    timeout_seconds=10,
)

mcp = FastMCP(name="My Spotify MCP Server", auth=auth)  

@mcp.tool(description="Greet a person with their name")
def greet(name: str) -> str:
    
    token = get_access_token()
    
    return f"Hello, {name} you have the following token {token.token} type {type(token)} "





