import logging
import os

from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.starlette import StarletteInstrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.composite import CompositeHTTPPropagator
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.baggage.propagation import W3CBaggagePropagator
from opentelemetry.context import attach, detach
from opentelemetry import trace, context, baggage
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


def setup_propagators():
    """Set up OpenTelemetry propagators for distributed tracing."""
    # Set up composite propagator with trace context and baggage
    propagator = CompositeHTTPPropagator([
        TraceContextTextMapPropagator(),
        W3CBaggagePropagator(),
    ])
    set_global_textmap(propagator)
    logger = get_logger()
    logger.info("OpenTelemetry propagators configured for spotify-mcp-server")


def extract_trace_context(headers: dict) -> tuple:
    """Extract trace context from HTTP headers."""
    logger = get_logger()
    logger.setLevel(logging.DEBUG)
    logger.debug(f"Extracting trace context from headers: {headers}")
    try:
        # Get the global propagator
        from opentelemetry.propagate import get_global_textmap
        propagator = get_global_textmap()

        # Extract context from headers - this creates a proper parent-child relationship
        extracted_context = propagator.extract(headers)

        # Extract correlation ID from baggage
        correlation_id = baggage.get_baggage(
            "correlation_id", context=extracted_context)

        logger.debug(f"Extracted trace context from headers: {headers}")
        logger.debug(f"Extracted correlation ID: {correlation_id}")
        logger.debug(f"Extracted context: {extracted_context}")
        logger.debug(f"Extracted context type: {type(extracted_context)}")

        # Validate that we have a valid trace context
        if extracted_context:
            span_context = trace.get_current_span(
                extracted_context).get_span_context()
            if span_context.is_valid:
                logger.debug(
                    f"Valid trace context found - trace_id: {span_context.trace_id}, span_id: {span_context.span_id}")
            else:
                logger.debug("Invalid trace context found !!!")
                logger.debug("span_context.is_valid: %s",
                             span_context.is_valid)
                logger.debug("span_context: %s", span_context)

        return extracted_context, correlation_id
    except Exception as e:
        logger.warning(f"Failed to extract trace context: {e}")
        return context.get_current(), None


def configure_telemetry(mcp: FastMCP):
    """Configure OpenTelemetry for the application."""
    # Set up propagators first
    setup_propagators()

    # Configure Application Insights if connection string is available
    logger = get_logger()
    logger.info("Configuring OpenTelemetry for Spotify MCP Server")
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
