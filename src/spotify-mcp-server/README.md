# Spotify MCP Server

This microservice exposes selected Spotify API endpoints via FastMCP and Spotipy.

## Features

- Search for tracks by query
- Get top tracks for an artist

## Requirements

- Python 3.11+
- Spotipy
- FastMCP
- Set environment variables: `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET`

## Usage

### Example Tools

- `search_track(query: str) -> str`: Search for a track by name or keyword.
- `get_artist_top_tracks(artist_id: str, country: str = "US") -> str`: Get top tracks for an artist.

### Running the Server

```
export SPOTIFY_CLIENT_ID=your_client_id
export SPOTIFY_CLIENT_SECRET=your_client_secret
python3 main.py
```

## Azure Deployment

- Containerize using the provided Dockerfile.
- Deploy as an Azure Container App (see infra/main.bicep).

## Contact

See project root README.md for more details.

https://techcommunity.microsoft.com/blog/integrationsonazureblog/azure-api-management-your-auth-gateway-for-mcp-servers/4402690
https://learn.microsoft.com/en-us/semantic-kernel/concepts/plugins/adding-mcp-plugins?pivots=programming-language-python
https://techcommunity.microsoft.com/blog/integrationsonazureblog/azure-api-management-your-auth-gateway-for-mcp-servers/4402690
https://modelcontextprotocol.io/specification/2025-03-26/basic/authorization
https://github.com/modelcontextprotocol/python-sdk/blob/main/examples/servers/simple-auth/mcp_simple_auth/server.py
