# OpenTelemetry Correlation ID Implementation Summary

## Overview

This implementation adds comprehensive OpenTelemetry support with correlation ID propagation between the setlist-agent and the two MCP servers (setlistfm-mcp-server and spotify-mcp-server).

## Key Features Implemented

### 1. Correlation ID Generation and Propagation

- **setlist-agent** generates a unique correlation ID for each user session
- Correlation IDs are propagated through HTTP headers using W3C standards
- OpenTelemetry baggage is used to carry correlation IDs across service boundaries
- All spans include the correlation ID as an attribute for easy filtering

### 2. Distributed Tracing Context

- Implemented W3C Trace Context propagation
- Composite propagators for maximum compatibility
- Proper context extraction and injection between services
- Graceful fallback when trace context is unavailable

### 3. Enhanced Telemetry Collection

- Azure Application Insights integration across all services
- Structured span attributes including service names and tool parameters
- Error tracking with exception recording
- Performance monitoring with span durations

## Files Modified/Created

### Core Implementation Files

#### setlist-agent (src/setlist-agent/)

- **enhanced_agent.py**: Added correlation ID generation, trace context injection, and propagator setup
- **pyproject.toml**: Added OpenTelemetry dependencies

#### setlistfm-mcp-server (src/setlistfm-mcp-server/)

- **configuration.py**: Enhanced with trace context extraction and propagator setup
- **setlistfm.py**: Updated span decorator to extract and use trace context
- **pyproject.toml**: Added OpenTelemetry dependencies

#### spotify-mcp-server (src/spotify-mcp-server/)

- **configuration.py**: Enhanced with trace context extraction and propagator setup
- **spotify.py**: Updated span decorator to extract and use trace context
- **pyproject.toml**: Added OpenTelemetry dependencies

### New Files Created

#### Common Libraries

- **src/common/telemetry.py**: Shared telemetry utilities for trace context handling

#### Documentation

- **docs/OPENTELEMETRY_SETUP.md**: Comprehensive OpenTelemetry setup and usage guide

#### Testing and Deployment

- **scripts/test_correlation_id.py**: Test script to verify correlation ID propagation
- **scripts/deploy_with_telemetry.sh**: Deployment script with telemetry validation

## Technical Implementation Details

### Propagation Flow

1. **setlist-agent** generates correlation ID and creates root span
2. When calling MCP servers, trace context is injected into HTTP headers
3. **MCP servers** extract trace context from headers and create child spans
4. All spans maintain the same correlation ID through baggage propagation

### Span Hierarchy

```
setlist-agent: enhanced-agent-chat (correlation_id: uuid-123)
├── setlistfm-mcp-server: setlistfm_mcp_search_artist (correlation_id: uuid-123)
│   └── HTTP request to Setlist.fm API
└── spotify-mcp-server: spotify_mcp_search_tracks (correlation_id: uuid-123)
    └── HTTP request to Spotify API
```

### Key Dependencies Added

- `opentelemetry-propagator-b3`
- `opentelemetry-propagator-jaeger`
- `opentelemetry-instrumentation-requests`
- `opentelemetry-instrumentation-httpx`
- `opentelemetry-instrumentation-starlette`

## Configuration Requirements

### Environment Variables

```bash
# Required
APPLICATIONINSIGHTS_CONNECTION_STRING="your-connection-string"

# Optional (for enhanced tracing)
AZURE_MONITOR_OPENTELEMETRY_ENABLED="true"
AZURE_TRACING_GEN_AI_CONTENT_RECORDING_ENABLED="true"
```

## Usage Examples

### Viewing Traces in Azure Application Insights

1. **Filter by Correlation ID**:

   ```kusto
   traces
   | where customDimensions.correlation_id == "your-correlation-id"
   | order by timestamp desc
   ```

2. **View MCP Tool Calls**:

   ```kusto
   traces
   | where customDimensions.["tool.name"] != ""
   | project timestamp, customDimensions.["tool.name"], customDimensions.correlation_id
   ```

3. **Performance Analysis**:
   ```kusto
   dependencies
   | where customDimensions.correlation_id == "your-correlation-id"
   | summarize avg(duration) by name
   ```

## Testing

Run the test script to verify correlation ID propagation:

```bash
python scripts/test_correlation_id.py
```

## Deployment

Use the enhanced deployment script:

```bash
./scripts/deploy_with_telemetry.sh
```

## Benefits

1. **End-to-End Tracing**: Track requests across all microservices
2. **Session Correlation**: Link all operations for a user session
3. **Performance Monitoring**: Identify bottlenecks and optimize performance
4. **Error Tracking**: Quickly identify and debug issues across services
5. **Operational Insights**: Understand usage patterns and system behavior

## Next Steps

1. **Monitor Performance**: Use Azure Application Insights dashboards
2. **Set Up Alerts**: Configure alerts for errors or performance issues
3. **Optimize Bottlenecks**: Use trace data to identify and fix slow operations
4. **Extend Telemetry**: Add custom metrics and additional span attributes as needed

This implementation provides a solid foundation for observability in the MySetlistAgent microservices architecture, enabling effective monitoring, debugging, and performance optimization.
