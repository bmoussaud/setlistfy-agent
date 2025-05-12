"""
Spotify OAuth Authentication for Chainlit Integration
Handles Spotify user authentication flow with session management.
"""
from chainlit.oauth_providers import OAuthProvider, providers
from chainlit.user import User
import os
import asyncio
import logging
import json
import secrets
from typing import Optional, Dict, Any
from urllib.parse import urlencode
import httpx
import chainlit as cl
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class SpotifyAuthManager:
    """Manages Spotify OAuth authentication for Chainlit users."""

    def __init__(self, validate_env=True):
        self.client_id = os.getenv("OAUTH_SPOTIFY_CLIENT_ID")
        self.client_secret = os.getenv("OAUTH_SPOTIFY_CLIENT_SECRET")
        self.redirect_uri = os.getenv(
            "OAUTH_SPOTIFY_REDIRECT_URI", "http://localhost:8000/auth/spotify/callback")

        if validate_env and not all([self.client_id, self.client_secret]):
            raise ValueError(
                "OAUTH_SPOTIFY_CLIENT_ID and OAUTH_SPOTIFY_CLIENT_SECRET must be set")

        self.auth_url = "https://accounts.spotify.com/authorize"
        self.token_url = "https://accounts.spotify.com/api/token"

        self.scopes = os.environ.get("OAUTH_SPOTIFY_SCOPES", "").split(",")

    def generate_auth_url(self, user_id: str) -> str:
        """Generate Spotify OAuth authorization URL."""
        state = secrets.token_urlsafe(32)

        # Store state in user session for validation
        cl.user_session.set("spotify_auth_state", state)

        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(self.scopes),
            "state": state,
            "show_dialog": "true"  # Force user to re-authorize
        }

        auth_url = f"{self.auth_url}?{urlencode(params)}"
        logger.info(f"Generated auth URL for user {user_id}: {auth_url}")

        return auth_url

    async def exchange_code_for_token(self, code: str, state: str) -> Optional[Dict[str, Any]]:
        """Exchange authorization code for access token."""
        # Validate state
        stored_state = cl.user_session.get("spotify_auth_state")
        if not stored_state or stored_state != state:
            logger.error("Invalid state parameter")
            return None

        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.token_url,
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                response.raise_for_status()
                token_data = response.json()

                # Store token in user session
                cl.user_session.set("spotify_tokens", token_data)
                logger.info("Successfully obtained Spotify tokens")
                return token_data

            except httpx.HTTPError as e:
                logger.error(f"Failed to exchange code for token: {e}")
                return None

    async def refresh_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """Refresh the access token using refresh token."""
        logger.info("Refreshing Spotify access token")

        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }

        logger.info(f"Data for token refresh: {data}")

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.token_url,
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                response.raise_for_status()
                new_tokens = response.json()
                logger.info(f"New tokens received: {new_tokens}")

                # Update stored tokens
                updated_tokens = {**new_tokens}
                cl.user_session.set("spotify_tokens", updated_tokens)
                cl.user_session.set(
                    "spotify_token", updated_tokens["access_token"])
                logger.info(
                    "Successfully refreshed Spotify tokens, return new access token")
                return updated_tokens["access_token"]

            except httpx.HTTPError as e:
                logger.error(f"Failed to refresh token: {e}")
                return None

    def get_access_token(self) -> Optional[str]:
        """Get valid access token from session."""
        return cl.user_session.get("spotify_token") or None

    def is_authenticated(self) -> bool:
        """Check if user is authenticated with Spotify."""
        return self.get_access_token() is not None

    async def get_user_profile(self) -> Optional[Dict[str, Any]]:
        """Get Spotify user profile information."""
        access_token = self.get_access_token()
        if not access_token:
            return None

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    "https://api.spotify.com/v1/me",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                response.raise_for_status()
                return response.json()

            except httpx.HTTPError as e:
                logger.error(f"Failed to get user profile: {e}")
                # Try to refresh token
                if await self.refresh_token():
                    access_token = self.get_access_token()
                    response = await client.get(
                        "https://api.spotify.com/v1/me",
                        headers={"Authorization": f"Bearer {access_token}"}
                    )
                    response.raise_for_status()
                    return response.json()
                return None

    def logout(self):
        """Clear Spotify authentication from session."""
        cl.user_session.set("spotify_tokens", None)
        cl.user_session.set("spotify_auth_state", None)
        cl.user_session.set("spotify_user_profile", None)
        logger.info("User logged out from Spotify")


class SpotifyAuthOAuthProvider(OAuthProvider):
    """Handles Spotify OAuth authentication flow."""
    id = "spotify"
    env = ["OAUTH_SPOTIFY_CLIENT_ID",
           "OAUTH_SPOTIFY_CLIENT_SECRET", "OAUTH_SPOTIFY_SCOPES"]

    def __init__(self):
        self.client_id = os.environ.get("OAUTH_SPOTIFY_CLIENT_ID")
        self.client_secret = os.environ.get("OAUTH_SPOTIFY_CLIENT_SECRET")
        self.authorize_url = "https://accounts.spotify.com/authorize"
        self.token_url = "https://accounts.spotify.com/api/token"
        self.user_info_url = "https://api.spotify.com/v1/me"
        self.scopes = os.environ.get("OAUTH_SPOTIFY_SCOPES")
        self.user_identifier = os.environ.get(
            "OAUTH_SPOTIFY_USER_IDENTIFIER", "email")

        self.authorize_params = {
            "scope": self.scopes,
            "response_type": "code",
        }

        if prompt := self.get_prompt():
            self.authorize_params["prompt"] = prompt

    async def get_token(self, code: str, url: str):
        logger.info(f"Exchanging code for token: {code} at {url}")
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": url,
        }
        logger.info(f"Payload for token exchange: {payload}")
        async with httpx.AsyncClient() as client:
            response = await client.post(self.token_url, data=payload)
            response.raise_for_status()
            json = response.json()
            logger.info(
                f"Received response from Spotify token endpoint: {json}")
            token = json
            if not token:
                raise httpx.HTTPStatusError(
                    "Failed to get the access token",
                    request=response.request,
                    response=response,
                )
            return token

    async def get_user_info(self, token: str):
        logger.info(f"Fetching user info with token: {token}")
        access_token = token.get("access_token")
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.user_info_url,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            server_user = response.json()
            user = User(
                identifier=server_user.get(self.user_identifier),
                metadata={
                    "provider": self.id,
                },
            )
            return (server_user, user)


def register_spotify_oauth_provider():
    """Register the Spotify OAuth provider with Chainlit."""
    if not os.environ.get("OAUTH_SPOTIFY_CLIENT_ID") or not os.environ.get("OAUTH_SPOTIFY_CLIENT_SECRET"):
        logger.warning(
            "Spotify OAuth provider is not configured. Please set OAUTH_SPOTIFY_CLIENT_ID and OAUTH_SPOTIFY_CLIENT_SECRET environment variables.")
        return

    # Register the Spotify OAuth provider
    # cl.oauth_providers.register(SpotifyAuthOAuthProvider())

    logger.info("Registering Spotify OAuth provider")
    providers.append(
        SpotifyAuthOAuthProvider()  # Register Spotify OAuth provider
    )


# Global auth manager instance - only create if environment is configured
try:
    spotify_auth = SpotifyAuthManager()
    register_spotify_oauth_provider()
    logger.info("SpotifyAuthManager initialized successfully.")
    # spotify_auth = None
except ValueError:
    logger.error(
        "Spotify OAuth environment variables not set. Spotify authentication will not be available.")
    spotify_auth = None
