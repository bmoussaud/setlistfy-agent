"""
Common telemetry configuration for MCP servers with OpenTelemetry support.
"""
import logging
import os
from typing import Tuple, Optional

from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.composite import CompositeHTTPPropagator
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.baggage.propagation import W3CBaggagePropagator
from opentelemetry.context import attach, detach
from opentelemetry import trace, context, baggage

logger = logging.getLogger(__name__)


def setup_propagators():
    """Set up OpenTelemetry propagators for distributed tracing."""
    # Set up composite propagator with trace context and baggage
    propagator = CompositeHTTPPropagator([
        TraceContextTextMapPropagator(),
        W3CBaggagePropagator(),
    ])
    set_global_textmap(propagator)
    logger.info("OpenTelemetry propagators configured for distributed tracing")


def extract_trace_context(headers: dict) -> Tuple[Optional[context.Context], Optional[str]]:
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
        correlation_id_str = str(
            correlation_id) if correlation_id is not None else None

        logger.debug(f"Extracted trace context from headers: {headers}")
        logger.debug(f"Extracted correlation ID: {correlation_id_str}")

        return extracted_context, correlation_id_str
    except Exception as e:
        logger.warning(f"Failed to extract trace context: {e}")
        return context.get_current(), None


def configure_azure_monitor_telemetry(service_name: str):
    """Configure Azure Monitor OpenTelemetry for a service."""
    # Set up propagators first
    setup_propagators()

    logger.info(f"Configuring OpenTelemetry for {service_name}")
    connection_string = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
    if connection_string is None:
        logger.warning(
            "APPLICATIONINSIGHTS_CONNECTION_STRING not found, Application Insights not configured")
        return

    try:
        logger.info(f"Configuring Application Insights for {service_name}")
        # Configure Azure Monitor with the connection string
        configure_azure_monitor(connection_string=connection_string)
        # Optionally, reduce verbosity of Azure SDK logs
        logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(
            logging.WARNING)
        logger.info(f"Application Insights configured for {service_name}")
    except Exception as e:
        logger.warning(
            f"Failed to configure Application Insights (configure_azure_monitor): {e}", exc_info=True)

    # Instrument HTTP clients
    try:
        logger.info("Instrumenting HTTP clients for OpenTelemetry")
        RequestsInstrumentor().instrument()
        HTTPXClientInstrumentor().instrument()
        logger.info(
            f"OpenTelemetry instrumentation configured for {service_name}")
    except Exception as e:
        logger.warning(
            f"Failed to configure OpenTelemetry instrumentation: {e}")


def create_span_with_context(tracer: trace.Tracer, name: str, headers: Optional[dict] = None):
    """Create a span with extracted trace context."""
    if headers:
        extracted_context, correlation_id = extract_trace_context(headers)
        span_context = extracted_context if extracted_context else context.get_current()
    else:
        span_context = context.get_current()
        correlation_id = None

    span = tracer.start_as_current_span(name, context=span_context)

    # Set correlation ID if available
    if correlation_id and hasattr(span, 'set_attribute'):
        span.set_attribute("correlation_id", correlation_id)

    return span
