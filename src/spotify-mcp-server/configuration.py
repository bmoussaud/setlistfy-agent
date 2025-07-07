import logging
import os

from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.starlette import StarletteInstrumentor
from fastmcp import FastMCP


def get_logger():
    return logging.getLogger("spotify_mcp_server")


def setup_logging():
    logger = get_logger()
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    handler.setFormatter(formatter)
    # Always add our handler (Gunicorn may pre-configure handlers, so forcibly add ours)
    logger.handlers = []
    logger.addHandler(handler)
    logger.propagate = False


def configure_telemetry(mcp: FastMCP):
    """Configure OpenTelemetry for the application."""
    # Configure Application Insights if connection string is available
    logger = get_logger()
    logger.info("Configuring OpenTelemetry for SetlistFM MCP Server")
    connection_string = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
    if connection_string is None:
        logger.warning(
            "APPLICATIONINSIGHTS_CONNECTION_STRING not found, Application Insights not configured")
        return
    try:
        logging.info(
            "Configuring Application Insights with connection string %s", connection_string)
        # Configure Azure Monitor with the connection string
        configure_azure_monitor(connection_string=connection_string)
        # Optionally, reduce verbosity of Azure SDK logs
        logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(
            logging.WARNING)
        logger.info("Application Insights configured for Spotify MCP Server")
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
            "Instrumenting HTTP clients for OpenTelemetry StarletteInstrumentor streaming")
        # Instrument the Starlette app for OpenTelemetry
        StarletteInstrumentor().instrument_app(mcp.http_app())
        logger.info(
            "Instrumenting HTTP clients for OpenTelemetry StarletteInstrumentor sse")
        StarletteInstrumentor().instrument_app(mcp.http_app(transport="sse"))
        logger.info(
            "OpenTelemetry instrumentation configured for Spotify MCP Server")
    except Exception as e:
        logger.warning(
            f"Failed to configure OpenTelemetry instrumentation: {e}")
