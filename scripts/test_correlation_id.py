#!/usr/bin/env python3
"""
Test script to verify OpenTelemetry correlation ID propagation between services.
"""

import asyncio
import uuid
import httpx
from opentelemetry import trace, context, baggage
from opentelemetry.propagate import get_global_textmap
from opentelemetry.propagators.composite import CompositeHTTPPropagator
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.baggage.propagation import W3CBaggagePropagator
from opentelemetry.propagate import set_global_textmap
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure OpenTelemetry
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

# Set up propagators
propagator = CompositeHTTPPropagator([
    TraceContextTextMapPropagator(),
    W3CBaggagePropagator(),
])
set_global_textmap(propagator)

# Add console exporter for testing
trace.get_tracer_provider().add_span_processor(
    SimpleSpanProcessor(ConsoleSpanExporter())
)


async def test_correlation_id_propagation():
    """Test correlation ID propagation between services."""

    # Generate a correlation ID
    correlation_id = str(uuid.uuid4())
    logger.info(f"Generated correlation ID: {correlation_id}")

    # Create a span with baggage
    with tracer.start_as_current_span("test-main-span") as span:
        span.set_attribute("correlation_id", correlation_id)

        # Set correlation ID in baggage
        baggage_context = baggage.set_baggage("correlation_id", correlation_id)

        # Create headers with trace context
        headers = {}
        propagator.inject(headers, context=baggage_context)

        logger.info(f"Headers with trace context: {headers}")

        # Simulate what happens in the MCP server
        await simulate_mcp_server_processing(headers)


async def simulate_mcp_server_processing(headers: dict):
    """Simulate MCP server processing with trace context extraction."""

    # Extract trace context (what MCP servers do)
    extracted_context = propagator.extract(headers)
    correlation_id = baggage.get_baggage(
        "correlation_id", context=extracted_context)

    logger.info(f"Extracted correlation ID: {correlation_id}")

    # Create child span with extracted context
    with tracer.start_as_current_span("mcp-server-span", context=extracted_context) as span:
        span.set_attribute("service.name", "test-mcp-server")
        if correlation_id:
            span.set_attribute("correlation_id", str(correlation_id))

        # Simulate API call
        await simulate_api_call(str(correlation_id) if correlation_id else "unknown")


async def simulate_api_call(correlation_id: str):
    """Simulate an API call within the MCP server."""

    with tracer.start_as_current_span("api-call") as span:
        span.set_attribute("http.url", "https://api.example.com/test")
        if correlation_id:
            span.set_attribute("correlation_id", correlation_id)

        # Simulate some work
        await asyncio.sleep(0.1)

        logger.info(
            f"API call completed with correlation ID: {correlation_id}")


async def test_http_propagation():
    """Test HTTP propagation with actual HTTP client."""

    correlation_id = str(uuid.uuid4())
    logger.info(
        f"Testing HTTP propagation with correlation ID: {correlation_id}")

    with tracer.start_as_current_span("http-test-span") as span:
        span.set_attribute("correlation_id", correlation_id)

        # Set correlation ID in baggage
        baggage_context = baggage.set_baggage("correlation_id", correlation_id)

        # Create headers with trace context
        headers = {}
        propagator.inject(headers, context=baggage_context)

        # Add custom correlation header
        headers["x-correlation-id"] = correlation_id

        logger.info(f"HTTP headers: {headers}")

        # Would normally make HTTP request here
        # async with httpx.AsyncClient() as client:
        #     response = await client.get("http://localhost:8000/test", headers=headers)

        logger.info("HTTP request would be made with trace context")


if __name__ == "__main__":
    print("Testing OpenTelemetry Correlation ID Propagation")
    print("=" * 50)

    asyncio.run(test_correlation_id_propagation())

    print("\nTesting HTTP Propagation")
    print("=" * 30)

    asyncio.run(test_http_propagation())

    print("\nTest completed. Check console output for span details.")
