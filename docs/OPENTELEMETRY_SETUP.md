# OpenTelemetry Configuration for MySetlistAgent

This document describes the OpenTelemetry configuration for distributed tracing across the MySetlistAgent microservices.

## Overview

The MySetlistAgent project uses OpenTelemetry to provide distributed tracing with correlation IDs between:

- **setlist-agent**: Main orchestrator service (Chainlit + Semantic Kernel)
- **setlistfm-mcp-server**: MCP server for Setlist.fm API
- **spotify-mcp-server**: MCP server for Spotify API

## Key Features

### 1. Correlation ID Propagation

- Each user session generates a unique correlation ID
- Correlation IDs are propagated through HTTP headers and OpenTelemetry baggage
- All spans include the correlation ID as an attribute for easy filtering

### 2. Distributed Tracing Context

- Uses W3C Trace Context propagation standard
- Supports OpenTelemetry baggage for correlation IDs
- Proper context extraction and injection between services

### 3. Azure Application Insights Integration

- All services send telemetry to Azure Application Insights
- Spans include service names, correlation IDs, and tool parameters
- Error tracking and performance monitoring

## Configuration

### Environment Variables

All services require these environment variables:

```bash
# Required for Azure Application Insights
APPLICATIONINSIGHTS_CONNECTION_STRING="your-connection-string"

# Optional - enables detailed tracing
AZURE_MONITOR_OPENTELEMETRY_ENABLED="true"
AZURE_TRACING_GEN_AI_CONTENT_RECORDING_ENABLED="true"
```

### Service-Specific Configuration

#### setlist-agent

The main agent service generates correlation IDs and injects trace context into MCP requests:

```python
# In enhanced_agent.py
self._correlation_id = self._generate_correlation_id()
headers = self._inject_trace_context(headers)
```

#### MCP Servers

Both MCP servers extract trace context from incoming requests:

```python
# In tool decorators
extracted_context, correlation_id = extract_trace_context(headers)
span_context = extracted_context if extracted_context else context.get_current()
```

## Span Structure

### Span Naming Convention

- **setlist-agent**: `enhanced-agent-chat`, `enhanced-agent-{operation}`
- **setlistfm-mcp-server**: `setlistfm_mcp_{tool_name}`
- **spotify-mcp-server**: `spotify_mcp_{tool_name}`

### Span Attributes

- `service.name`: Service identifier
- `correlation_id`: Session correlation ID
- `tool.name`: MCP tool name
- `tool.args.{param}`: Tool parameters

## Trace Flow Example

```
1. User makes request to setlist-agent
   └── Creates span with correlation_id="uuid-123"

2. setlist-agent calls setlistfm-mcp-server
   └── Injects trace context + correlation_id in headers

3. setlistfm-mcp-server processes request
   └── Extracts context + correlation_id from headers
   └── Creates child span with same correlation_id

4. setlistfm-mcp-server makes HTTP request to Setlist.fm API
   └── HTTP instrumentation creates child span

5. All spans linked by trace context with correlation_id
```

## Dependencies

### setlist-agent

```toml
dependencies = [
    "azure-monitor-opentelemetry",
    "opentelemetry-sdk",
    "opentelemetry-instrumentation-requests",
    "opentelemetry-instrumentation-httpx",
    "opentelemetry-instrumentation-openai",
    "opentelemetry-instrumentation-asyncio",
    "opentelemetry-propagator-b3",
    "opentelemetry-propagator-jaeger",
    # ... other dependencies
]
```

### MCP Servers

```toml
dependencies = [
    "azure-monitor-opentelemetry",
    "opentelemetry-sdk",
    "opentelemetry-instrumentation-httpx",
    "opentelemetry-instrumentation-requests",
    "opentelemetry-instrumentation-starlette",
    "opentelemetry-propagator-b3",
    "opentelemetry-propagator-jaeger",
    # ... other dependencies
]
```

## Usage

### Viewing Traces in Azure Application Insights

1. **End-to-End Tracing**: Use the "End-to-end transaction details" view
2. **Filter by Correlation ID**: Search for `correlation_id:"uuid-123"`
3. **Performance Analysis**: View span durations and dependencies
4. **Error Tracking**: See exceptions with full context

### Common Queries

```kusto
// Find all traces for a specific correlation ID
traces
| where customDimensions.correlation_id == "your-correlation-id"
| order by timestamp desc

// Find MCP tool calls
traces
| where customDimensions.["tool.name"] != ""
| project timestamp, customDimensions.["tool.name"], customDimensions.correlation_id

// Performance analysis
dependencies
| where customDimensions.correlation_id == "your-correlation-id"
| summarize avg(duration) by name
```

## Implementation Details

### Propagator Configuration

Both services use composite propagators:

```python
from opentelemetry.propagators.composite import CompositeHTTPPropagator
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.baggage.propagation import W3CBaggagePropagator

propagator = CompositeHTTPPropagator([
    TraceContextTextMapPropagator(),
    W3CBaggagePropagator(),
])
```

### Correlation ID Handling

```python
# Generation (setlist-agent)
self._correlation_id = str(uuid.uuid4())
baggage_context = baggage.set_baggage("correlation_id", self._correlation_id)

# Extraction (MCP servers)
correlation_id = baggage.get_baggage("correlation_id", context=extracted_context)
```

## Troubleshooting

### Common Issues

1. **Missing Correlation IDs**: Check that baggage propagation is working
2. **Disconnected Spans**: Verify trace context injection/extraction
3. **Missing Telemetry**: Confirm `APPLICATIONINSIGHTS_CONNECTION_STRING` is set

### Debug Logging

Enable debug logging to see trace context operations:

```python
import logging
logging.getLogger("opentelemetry").setLevel(logging.DEBUG)
```

## Best Practices

1. **Always use correlation IDs** for user session tracking
2. **Include service names** in span attributes
3. **Handle extraction failures gracefully** with fallback contexts
4. **Use meaningful span names** that describe the operation
5. **Set span status** appropriately (OK/ERROR)
6. **Record exceptions** in spans for better debugging
