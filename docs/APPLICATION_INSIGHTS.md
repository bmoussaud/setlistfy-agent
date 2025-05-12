# Application Insights Configuration

This document describes how Application Insights is configured across all three services in the MySetlistAgent project.

## Overview

Application Insights provides comprehensive monitoring, logging, and telemetry for the MySetlistAgent microservices:

- **setlist-agent**: Main Chainlit application with Semantic Kernel agent
- **spotify-mcp-server**: MCP server for Spotify API integration
- **setlistfm-mcp-server**: MCP server for Setlist.fm API integration

## Infrastructure Configuration (Bicep)

### Application Insights Resource

The Application Insights resource is defined in `infra/modules/app-insights.bicep` and includes:

- Application Insights workspace integration
- Response time monitoring alerts
- Email notification action groups

### Key Vault Secrets

The Application Insights connection string is stored securely in Azure Key Vault:

```bicep
resource secretAppInsightCS 'Microsoft.KeyVault/vaults/secrets@2024-04-01-preview' = {
  parent: kv
  name: 'APPLICATIONINSIGHTS-CONNECTIONSTRING'
  properties: {
    value: applicationInsights.outputs.connectionString
  }
}
```

### Container Apps Configuration

Each container app is configured with the Application Insights connection string:

```bicep
secrets: [
  {
    name: 'applicationinsights-connectionstring'
    keyVaultUrl: '${kv.properties.vaultUri}secrets/APPLICATIONINSIGHTS-CONNECTIONSTRING'
    identity: azrKeyVaultContributor.id
  }
]
```

And the environment variable:

```bicep
env: [
  {
    name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
    secretRef: 'applicationinsights-connectionstring'
  }
]
```

## Python Configuration

### Dependencies

All services include the following Application Insights dependencies in their `pyproject.toml`:

```toml
dependencies = [
    # ... other dependencies ...
    "azure-monitor-opentelemetry",
    "opentelemetry-sdk",
    "opentelemetry-instrumentation-httpx",
    "opentelemetry-instrumentation-fastapi"
]
```

### Service Configuration

#### setlist-agent (main.py)

```python
from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

connection_string = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
if connection_string:
    configure_azure_monitor(connection_string=connection_string)
    HTTPXClientInstrumentor().instrument()
```

#### spotify-mcp-server (spotify.py)

```python
from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

connection_string = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
if connection_string:
    configure_azure_monitor(connection_string=connection_string)
    HTTPXClientInstrumentor().instrument()
```

#### setlistfm-mcp-server (setlistfm.py)

```python
from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

connection_string = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
if connection_string:
    configure_azure_monitor(connection_string=connection_string)
    HTTPXClientInstrumentor().instrument()
```

## What's Monitored

### Automatic Telemetry

- **HTTP Requests**: All incoming and outgoing HTTP requests
- **Dependencies**: External API calls (Spotify, Setlist.fm)
- **Exceptions**: Unhandled exceptions and errors
- **Performance**: Request duration, response times
- **Custom Events**: Application-specific events and metrics

### Manual Logging

All services use the standard Python logging module, which is automatically captured by Application Insights:

```python
import logging
logger = logging.getLogger(__name__)
logger.info("Application Insights configured successfully")
```

## Monitoring and Alerts

### Response Time Alert

An automatic alert is configured for response times > 3 seconds:

```bicep
resource metricAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: responseAlertName
  properties: {
    criteria: {
      allOf: [
        {
          metricName: 'requests/duration'
          operator: 'GreaterThan'
          threshold: responseTimeThreshold
          timeAggregation: 'Average'
        }
      ]
    }
  }
}
```

## Testing

Use the test script to verify configuration:

```bash
python scripts/test_app_insights.py
```

## Troubleshooting

### Common Issues

1. **Missing Connection String**: Verify the `APPLICATIONINSIGHTS_CONNECTION_STRING` environment variable is set
2. **Import Errors**: Ensure all OpenTelemetry packages are installed
3. **No Telemetry**: Check Azure Key Vault access and managed identity permissions

### Logs

Check container logs for Application Insights configuration messages:

```bash
# For Azure Container Apps
az containerapp logs show --name setlist-agent --resource-group <rg-name>
az containerapp logs show --name spotify-mcp --resource-group <rg-name>
az containerapp logs show --name setlistfm-mcp --resource-group <rg-name>
```

### Azure Portal

Navigate to the Application Insights resource in the Azure Portal to view:

- Live metrics
- Application map
- Performance metrics
- Failures and exceptions
- Custom dashboards

## Best Practices

1. **Structured Logging**: Use structured logging with consistent field names
2. **Custom Metrics**: Add custom telemetry for business-specific metrics
3. **Correlation**: Ensure request correlation across microservices
4. **Sampling**: Configure sampling for high-volume applications
5. **Alerting**: Set up meaningful alerts based on SLIs/SLOs

## Security

- Connection strings are stored securely in Azure Key Vault
- Managed identities are used for authentication
- No sensitive data is logged to Application Insights
- RBAC controls access to telemetry data
