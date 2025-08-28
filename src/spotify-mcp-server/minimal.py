import logging
from fastmcp import FastMCP
from fastmcp.server.auth import BearerAuthProvider
from fastmcp import FastMCP
from fastmcp.server.auth import OAuthProxy
# from fastmcp.server.auth.providers.jwt import JWTVerifier

# Configure logging for both uvicorn and fastmcp
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT)

fastmcp_logger = logging.getLogger("fastmcp")
fastmcp_logger.setLevel(logging.DEBUG)

uvicorn_logger = logging.getLogger("uvicorn")
uvicorn_logger.setLevel(logging.DEBUG)


auth = OAuthProxy(
    # Upstream provider endpoints
    upstream_authorization_endpoint="https://accounts.spotify.com/authorize",
    upstream_token_endpoint="https://accounts.spotify.com/api/token",

    # Your registered app credentials
    upstream_client_id="1c3e47d871fe46c1bdc787e487233019",
    upstream_client_secret="490e086df740497b90d36362ffa18ec2",

    # Token validation
    token_verifier=token_verifier,

    # Your FastMCP server URL (string automatically converted to AnyHttpUrl)
    base_url="https://your-server.com",

    # Optional: customize callback path (defaults to "/auth/callback")
    redirect_path="/auth/callback"
)

mcp = FastMCP(name="My Server", auth=auth)

auth = BearerAuthProvider(
    jwks_uri="https://my-identity-provider.com/.well-known/jwks.json",
    issuer="https://accounts.spotify.com",
    algorithm="RS512",
    audience="my-mcp-server"
)

mcp = FastMCP(name="My MCP Server", auth=auth)
