import logging
import os

from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.starlette import StarletteInstrumentor
from opentelemetry import trace
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
    """Middleware that logs all MCP operations."""

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        """Called when a tool is called."""
        message: CallToolRequestParams = context.message
        if message is not None:
            logger.info(f"Tool call message: {message}")
            logger.info(f"Tool call message type: {type(message)}")
            tool_name = message.model_dump().get("name", "UnknownTool")
            tool_args = message.model_dump().get("arguments", {})
        else:
            logger.info("Tool call message is None")
            tool_name = "UnknownTool"
            tool_args = {}

        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span(f"Setlistfm_MCP_{tool_name}") as span:
            span.set_attribute("tool.name", tool_name)
            for key, value in tool_args.items():
                span.set_attribute(f"tool.args.{key}", value)

            logger.info(f"Tool call started: {tool_name}")
            try:
                result = await call_next(context)
                logger.info(
                    f"Tool call completed: {tool_name}")
                span.set_status(trace.Status(trace.StatusCode.OK))
            except Exception as e:
                logger.error(
                    f"Error during tool call {tool_name}: {e}", exc_info=True)
                span.set_status(trace.Status(
                    trace.StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise

        return result


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
