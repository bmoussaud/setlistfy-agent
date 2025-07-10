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
from fastmcp.server.middleware import Middleware, MiddlewareContext
from mcp.types import CallToolRequestParams

logger = logging.getLogger(__name__)


def setup_logging():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


class Telemetry(Middleware):
    """Middleware that logs all MCP operations and extracts trace context."""

    def __init__(self):
        # Set up OpenTelemetry propagators for distributed tracing
        self._setup_propagators()

    def _setup_propagators(self):
        """Set up OpenTelemetry propagators for distributed tracing."""
        # Set up composite propagator with trace context and baggage
        propagator = CompositeHTTPPropagator([
            TraceContextTextMapPropagator(),
            W3CBaggagePropagator(),
        ])
        set_global_textmap(propagator)
        logger.info(
            "OpenTelemetry propagators configured for setlistfm-mcp-server")

    def _extract_trace_context(self, headers: dict) -> tuple:
        """Extract trace context from HTTP headers."""
        try:
            # Get the global propagator
            from opentelemetry.propagate import get_global_textmap
            propagator = get_global_textmap()

            # Extract context from headers
            extracted_context = propagator.extract(headers)

            # Extract correlation ID from baggage
            correlation_id = baggage.get_baggage(
                "correlation_id", context=extracted_context)

            logger.debug(f"Extracted trace context from headers: {headers}")
            logger.debug(f"Extracted correlation ID: {correlation_id}")

            return extracted_context, correlation_id
        except Exception as e:
            logger.warning(f"Failed to extract trace context: {e}")
            return context.get_current(), None

    async def on_call_tool(self, context_mw: MiddlewareContext, call_next):
        """Called when a tool is called."""
        message: CallToolRequestParams = context_mw.message
        if message is not None:
            logger.info(f"Tool call message: {message}")
            logger.info(f"Tool call message type: {type(message)}")
            tool_name = message.model_dump().get("name", "UnknownTool")
            tool_args = message.model_dump().get("arguments", {})
        else:
            logger.info("Tool call message is None")
            tool_name = "UnknownTool"
            tool_args = {}

        # Extract trace context from request headers if available
        extracted_context, correlation_id = None, None
        try:
            # Try to get headers from the request (this might vary based on FastMCP version)
            if hasattr(context_mw, 'request') and context_mw.request:
                headers = dict(context_mw.request.headers)
                extracted_context, correlation_id = self._extract_trace_context(
                    headers)
        except Exception as e:
            logger.debug(f"Could not extract trace context from request: {e}")

        # Create span with extracted context
        tracer = trace.get_tracer(__name__)
        span_context = extracted_context if extracted_context else context.get_current()

        with tracer.start_as_current_span(f"setlistfm_mcp_{tool_name}", context=span_context) as span:
            span.set_attribute("tool.name", tool_name)
            span.set_attribute("service.name", "setlistfm-mcp-server")

            # Set correlation ID if available
            if correlation_id:
                span.set_attribute("correlation_id", correlation_id)

            # Set tool arguments as attributes
            for key, value in tool_args.items():
                span.set_attribute(f"tool.args.{key}", str(value))

            logger.info(
                f"Tool call started: {tool_name} (correlation_id: {correlation_id})")
            try:
                # Attach the extracted context for the duration of the call
                token = attach(span_context) if extracted_context else None
                try:
                    result = await call_next(context_mw)
                    logger.info(f"Tool call completed: {tool_name}")
                    span.set_status(trace.Status(trace.StatusCode.OK))
                finally:
                    if token:
                        detach(token)
            except Exception as e:
                logger.error(
                    f"Error during tool call {tool_name}: {e}", exc_info=True)
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise

        return result


def extract_trace_context(headers: dict) -> tuple:
    """Extract trace context from HTTP headers."""
    try:
        # Get the global propagator
        from opentelemetry.propagate import get_global_textmap
        propagator = get_global_textmap()

        # Extract context from headers
        extracted_context = propagator.extract(headers)

        # Extract correlation ID from baggage
        correlation_id = baggage.get_baggage(
            "correlation_id", context=extracted_context)

        logger.debug(f"Extracted trace context from headers: {headers}")
        logger.debug(f"Extracted correlation ID: {correlation_id}")

        return extracted_context, correlation_id
    except Exception as e:
        logger.warning(f"Failed to extract trace context: {e}")
        return context.get_current(), None


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
