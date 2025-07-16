# setlistfm-agent: AI Foundry SDK Agent

This is a Python agent using the AI Foundry SDK running in Azure Container Apps that manages setlist content using Bing Grounding.

## Features

- **AI Foundry SDK Integration**: Uses Azure AI Foundry agents for intelligent conversation
- **Bing Grounding**: Enhanced search capabilities for setlist and venue information
- **Setlist Content Management**: Processes and enriches setlist data
- **FastAPI Backend**: RESTful API for agent interactions
- **Telemetry**: Full Application Insights integration for monitoring

## Environment Variables

- `PROJECT_ENDPOINT`: Azure AI Foundry project endpoint
- `MODEL_DEPLOYMENT_NAME`: AI model deployment name
- `AZURE_CLIENT_ID`: Managed Identity client ID
- `APPLICATIONINSIGHTS_CONNECTION_STRING`: Application Insights connection string
- `SETLISTFM_API_KEY`: Setlist.fm API key

## Usage

### Local Development

```bash
uv venv
uv sync
uv run uvicorn main:app --host 0.0.0.0 --port 8080
```

### Docker

```bash
docker build -t setlistfm-agent .
docker run --env-file .env -p 8080:80 setlistfm-agent
```

## API Endpoints

- `POST /chat`: Start a conversation with the agent
- `GET /health`: Health check endpoint
- `GET /ready`: Readiness check endpoint

## Azure Deployment

This service is configured for deployment as an Azure Container App with:

- Managed Identity authentication
- Application Insights telemetry
- Auto-scaling capabilities
- Health probes
