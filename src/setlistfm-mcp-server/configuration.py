import logging
import os

from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.starlette import StarletteInstrumentor

logger = logging.getLogger(__name__)


def configure_telemetry():
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
            "Instrumenting HTTP clients for OpenTelemetry StarletteInstrumentor")
        StarletteInstrumentor().instrument(skip_dep_check=True)
        logger.info(
            "OpenTelemetry instrumentation configured for SetlistFM MCP Server")
    except Exception as e:
        logger.warning(
            f"Failed to configure OpenTelemetry instrumentation: {e}")
