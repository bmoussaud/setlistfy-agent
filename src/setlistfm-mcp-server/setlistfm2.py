
from dotenv import load_dotenv
import httpx
from fastmcp import FastMCP
import json
import logging
import os

from configuration import configure_telemetry, Telemetry, setup_logging
load_dotenv()

# Setup logging first
setup_logging()
logger = logging.getLogger(__name__)


# Create an HTTP client for your API
headers = {
    "x-api-key": os.getenv("SETLISTFM_API_KEY", ""),
    "Accept": "application/json",
    "User-Agent": "setlistfm-mcp/1.0"
}
client = httpx.AsyncClient(base_url="https://api.setlist.fm/rest",
                           headers=headers)
# Load your OpenAPI spec from a file
with open("openapi-setlistfm.json", "r", encoding="utf-8") as f:
    openapi_spec = json.load(f)

# Create the MCP server
mcp = FastMCP.from_openapi(
    openapi_spec=openapi_spec,
    client=client,
    name="Setlist.fm MCP Server",
    version="1.0.0",
    mcp_names={
        "resource__1.0_artist__mbid__getArtist_GET": "getArtist",
        "resource__1.0_artist__mbid__setlists_getArtistSetlists_GET": "getArtistSetlists",
        "resource__1.0_city__geoId__getCity_GET": "getCity",
        "resource__1.0_search_artists_getArtists_GET": "getArtists",
        "resource__1.0_search_cities_getCities_GET": "getCities",
        "resource__1.0_search_countries_getCountries_GET": "getCountries",
        "resource__1.0_search_setlists_getSetlists_GET": "getSetlists",
        "resource__1.0_search_venues_getVenues_GET": "getVenues",
        "resource__1.0_setlist_version__versionId__getSetlistVersion_GET": "getSetlistVersion",
        "resource__1.0_setlist__setlistId__getSetlist_GET": "getSetlist",
        "resource__1.0_user__userId__getUser_GET": "getUser",
        "resource__1.0_user__userId__attended_getUserAttendedSetlists_GET": "getUserAttendedSetlists",
        "resource__1.0_user__userId__edited_getUserEditedSetlists_GET": "getUserEditedSetlists",
        "resource__1.0_venue__venueId__getVenue_GET": "getVenue",
        "resource__1.0_venue__venueId__setlists_getVenueSetlists_GET": "getVenueSetlists",
    }
)
configure_telemetry()
mcp.add_middleware(Telemetry())

if __name__ == "__main__":
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
