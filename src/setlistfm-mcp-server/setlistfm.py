from functools import wraps
import asyncio
from opentelemetry import trace, context, baggage
import logging
import os
import json
import httpx
from typing import Any, Optional
from fastmcp import FastMCP
from dotenv import load_dotenv
from starlette.responses import JSONResponse
from starlette.requests import Request

from configuration import configure_telemetry, extract_trace_context
load_dotenv()


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


def my_span(name: str):
    """
    Decorator to create a span for OpenTelemetry tracing with trace context support.
    Works with both sync and async functions.
    """
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                # Extract trace context from request headers
                extracted_context, correlation_id = None, None
                try:
                    # In FastMCP, we need to get the request context differently
                    # This is a simplified approach - in a real implementation,
                    # you might need to pass the request context through the middleware
                    from fastmcp.server.dependencies import get_http_request
                    request: Request = get_http_request()
                    if request:
                        headers = dict(request.headers)
                        extracted_context, correlation_id = extract_trace_context(
                            headers)
                except Exception as e:
                    logger.debug(f"Could not extract trace context: {e}")

                tracer = trace.get_tracer(__name__)
                span_context = extracted_context if extracted_context else context.get_current()

                # Start a new span with the extracted context
                with tracer.start_as_current_span(f"setlistfm_mcp_{name}", context=span_context) as span:
                    span.set_attribute("service.name", "setlistfm-mcp-server")

                    # Set correlation ID if available
                    if correlation_id:
                        span.set_attribute("correlation_id", correlation_id)
                        logger.info(
                            f"Processing {name} with correlation_id: {correlation_id}")

                    try:
                        # Attach the extracted context for the duration of the call
                        token = context.attach(
                            span_context) if extracted_context else None
                        try:
                            result = await func(*args, **kwargs)
                            span.set_status(trace.Status(trace.StatusCode.OK))
                            return result
                        finally:
                            if token:
                                context.detach(token)
                    except Exception as e:
                        span.set_status(trace.Status(
                            trace.StatusCode.ERROR, str(e)))
                        span.record_exception(e)
                        raise
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                # Extract trace context from request headers
                extracted_context, correlation_id = None, None
                try:
                    from fastmcp.server.dependencies import get_http_request
                    request: Request = get_http_request()
                    if request:
                        headers = dict(request.headers)
                        extracted_context, correlation_id = extract_trace_context(
                            headers)
                except Exception as e:
                    logger.debug(f"Could not extract trace context: {e}")

                tracer = trace.get_tracer(__name__)
                span_context = extracted_context if extracted_context else context.get_current()

                with tracer.start_as_current_span(f"setlistfm_mcp_{name}", context=span_context) as span:
                    span.set_attribute("service.name", "setlistfm-mcp-server")

                    # Set correlation ID if available
                    if correlation_id:
                        span.set_attribute("correlation_id", correlation_id)
                        logger.info(
                            f"Processing {name} with correlation_id: {correlation_id}")

                    try:
                        # Attach the extracted context for the duration of the call
                        token = context.attach(
                            span_context) if extracted_context else None
                        try:
                            result = func(*args, **kwargs)
                            span.set_status(trace.Status(trace.StatusCode.OK))
                            return result
                        finally:
                            if token:
                                context.detach(token)
                    except Exception as e:
                        span.set_status(trace.Status(
                            trace.StatusCode.ERROR, str(e)))
                        span.record_exception(e)
                        raise
            return sync_wrapper
    return decorator


mcp = FastMCP("SetlistFM")
configure_telemetry()

# Constants
SETLISTFM_API_BASE = "https://api.setlist.fm/rest/1.0"
USER_AGENT = "setlistfm-mcp/1.0"
SETLISTFM_API_KEY = os.getenv(
    "SETLISTFM_API_KEY", "")


@mcp.custom_route("/", methods=["GET"])
async def root(request: Request) -> JSONResponse:
    return JSONResponse({"mcp": mcp.name, "root": "ok"})


@mcp.custom_route("/startup", methods=["GET"])
async def startup(request: Request) -> JSONResponse:
    return JSONResponse({"mcp": mcp.name, "startup": "ok"})


@mcp.custom_route("/liveness", methods=["GET"])
async def liveness(request: Request) -> JSONResponse:
    return JSONResponse({"mcp": mcp.name, "liveness": "ok"})


@mcp.custom_route("/readiness", methods=["GET"])
async def readiness(request: Request) -> JSONResponse:
    return JSONResponse({"mcp": mcp.name, "readiness": "ok"})


def get_headers() -> dict[str, str]:
    """Return headers for Setlist.fm API requests."""
    return {
        "x-api-key": SETLISTFM_API_KEY,
        "Accept": "application/json",
        "User-Agent": USER_AGENT
    }


async def make_setlistfm_request(url: str, params: dict[str, str | int] | None = None) -> dict[str, Any] | None:
    """Make a request to the Setlist.fm API with error handling."""
    headers = get_headers()
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, params=params, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.info(f"Error fetching from Setlist.fm: {e}")
            return None


@mcp.tool()
@my_span("search_setlists")
async def search_setlists(
    artist_mbid: Optional[str] = None,
    artist_name: Optional[str] = None,
    city_name: Optional[str] = None,
    country_code: Optional[str] = None,
    page: int = 1
) -> str:
    """Search for setlists by artist, city, or country.

    Args:
        artist_mbid: Musicbrainz ID of the artist (optional)
        artist_name: Name of the artist (optional)
        city_name: Name of the city (optional)
        country_code: Country code (optional)
        page: Page number for pagination (default 1)

    Returns:
        A formatted string with setlist information or an error message.
    """

    params: dict[str, str | int] = {"p": page}
    if artist_name:
        params["artistName"] = artist_name
    if artist_mbid:
        params["artistMbid"] = artist_mbid
    if city_name:
        params["cityName"] = city_name
    if country_code:
        params["countryCode"] = country_code

    logger.info(f"Searching setlists with params: {params}")
    current_span = trace.get_current_span()
    current_span.set_attribute("setlist.params", json.dumps(params))
    result = await make_setlistfm_request(f"{SETLISTFM_API_BASE}/search/setlists", params=params)
    return json.dumps(result) if result is not None else json.dumps({"error": "No data found"})


@mcp.tool()
@my_span("get_setlist_by_id")
async def get_setlist_by_id(setlist_id: str) -> str:
    """Get a setlist by its Setlist.fm ID.

    Args:
        setlist_id: The Setlist.fm setlist ID
    """
    logger.info(f"Fetching setlist by ID: {setlist_id}")
    current_span = trace.get_current_span()
    current_span.set_attribute("setlist.id", setlist_id)
    result = await make_setlistfm_request(f"{SETLISTFM_API_BASE}/setlist/{setlist_id}")
    return json.dumps(result) if result is not None else json.dumps({"error": "No data found"})


@mcp.tool()
@my_span("get_artist_by_mbid")
async def get_artist_by_mbid(mbid: str) -> str:
    """Get artist info by Musicbrainz ID (mbid).

    Args:
        mbid: The Musicbrainz ID of the artist
    """
    logger.info(f"Fetching artist by MBID: {mbid}")
    current_span = trace.get_current_span()
    current_span.set_attribute("artist.mbid", mbid)
    result = await make_setlistfm_request(f"{SETLISTFM_API_BASE}/artist/{mbid}")
    return json.dumps(result) if result is not None else json.dumps({"error": "No data found"})


@mcp.tool()
@my_span("get_artist_setlists")
async def get_artist_setlists(mbid: str, page: int = 1) -> str:
    """Get setlists for an artist by Musicbrainz ID (mbid).

    Args:
        mbid: The Musicbrainz ID of the artist
        page: Page number for pagination (default 1)
    """
    logger.info(f"Fetching setlists for artist MBID: {mbid}, page: {page}")
    current_span = trace.get_current_span()
    current_span.set_attribute("artist.mbid", mbid)
    current_span.set_attribute("setlist.page", page)
    result = await make_setlistfm_request(f"{SETLISTFM_API_BASE}/artist/{mbid}/setlists", params={"p": page})
    return json.dumps(result) if result is not None else json.dumps({"error": "No data found"})


@mcp.tool()
@my_span("get_venue_by_id")
async def get_venue_by_id(venue_id: str) -> str:
    """Get venue info by venueId.

    Args:
        venue_id: The Setlist.fm venue ID
    """
    logger.info(f"Fetching venue by ID: {venue_id}")
    current_span = trace.get_current_span()
    current_span.set_attribute("venue.id", venue_id)
    result = await make_setlistfm_request(f"{SETLISTFM_API_BASE}/venue/{venue_id}")
    return json.dumps(result) if result is not None else json.dumps({"error": "No data found"})


@mcp.tool()
@my_span("get_venue_setlists")
async def get_venue_setlists(venue_id: str, page: int = 1) -> str:
    """Get setlists for a venue by venueId.

    Args:
        venue_id: The Setlist.fm venue ID
        page: Page number for pagination (default 1)
    """
    logger.info(f"Fetching setlists for venue ID: {venue_id}, page: {page}")
    current_span = trace.get_current_span()
    current_span.set_attribute("venue.id", venue_id)
    result = await make_setlistfm_request(f"{SETLISTFM_API_BASE}/venue/{venue_id}/setlists", params={"p": page})
    return json.dumps(result) if result is not None else json.dumps({"error": "No data found"})


@mcp.tool()
@my_span("search_venues")
async def search_venues(
    name: Optional[str] = None,
    city_id: Optional[str] = None,
    city_name: Optional[str] = None,
    state: Optional[str] = None,
    state_code: Optional[str] = None,
    country: Optional[str] = None,
    page: int = 1
) -> dict[str, Any] | None:
    """
    Search for venues by venue name, city, state, and country.

    Args:
        name: Name of the venue (optional)
        city_id: The city's geoId (optional)
        city_name: Name of the city where the venue is located (optional)
        state: The city's state (optional)
        state_code: The city's state code (optional)
        country: The city's country (optional)
        page: Page number for pagination (default 1)

    Returns:
        A dictionary with the list of matching venues or None if an error occurs.
    """
    params = {}
    if name:
        params["name"] = name
    if city_id:
        params["cityId"] = city_id
    if city_name:
        params["cityName"] = city_name
    if state:
        params["state"] = state
    if state_code:
        params["stateCode"] = state_code
    if country:
        params["country"] = country
    params["p"] = page
    logger.info(f"Searching venues with params: {params}")
    current_span = trace.get_current_span()
    current_span.set_attribute("venue.search_params", json.dumps(params))
    return await make_setlistfm_request(f"{SETLISTFM_API_BASE}/search/venues", params=params)


@mcp.tool()
@my_span("search_artists")
async def search_artists(artist_name: str, sort: str = "relevance", page: int = 1) -> str:
    """Search for artists by name.

    Args:
        artist_name: Name of the artist
        sort: Sort order (default "relevance")
        page: Page number for pagination (default 1)
    """
    logger.info(
        f"Searching artists with params: {artist_name}, {sort}, {page}")
    current_span = trace.get_current_span()
    current_span.set_attribute("artist.name", artist_name)
    current_span.set_attribute("artist.sort", sort)
    current_span.set_attribute("artist.page", page)
    result = await make_setlistfm_request(
        f"{SETLISTFM_API_BASE}/search/artists",
        params={"artistName": artist_name, "p": page, "sort": sort}
    )
    return json.dumps(result) if result is not None else json.dumps({"error": "No data found"})


if __name__ == "__main__":
    logger.info("Starting FastMCP server for SetlistFM")
    # if opentelemetry is configured, use default logging config should be reduced to None else a slow startup time (30s)
    uvicorn_config = {
        "log_config": None,  # Use default logging configuration
    }
    mcp.run(
        transport="sse",
        host="127.0.0.1",
        port=9000,
        log_level="debug",
        uvicorn_config=uvicorn_config
    )
