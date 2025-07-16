# MySetlistAgent

A modular microservice project for music and setlist data management, built with Python 3.11+ and integrating AI Foundry SDK, Setlist.fm, Spotify APIs, and Model Context Protocol (MCP) servers.

## Services

This project consists of four main microservices:

1. **setlist-agent** - Chainlit-based conversational agent using Semantic Kernel and MCP plugins for setlist and music data orchestration
2. **setlistfm-agent** - AI Foundry SDK agent with Bing Grounding for enhanced setlist content management and intelligent search
3. **setlistfm-mcp-server** - MCP server providing Setlist.fm API tools and concert data
4. **spotify-mcp-server** - MCP server providing Spotify API tools for music data and playlists

## Quick Start

```
azd env get-value WEATHER_MCP_URL
```

1. Edit `infra/main.parameters.json` and update the values of the following keys:

- `setlistfmApiKey` go to https://www.setlist.fm/settings/apps, create an account and generate an API key
- `spotifyClientId`, `spotifyClientSecret` go https://developer.spotify.com/dashboard create a new app and grab the information.

1. `azd auth login`
1. `azd up`

```
  (✓) Done: Container Registry: BenSetListAgtzuxtumaevhs6w (1.507s)
  (✓) Done: Key Vault: kvset6xdkexhywhcn2 (1.164s)
  (✓) Done: Log Analytics workspace: BenSetListAgt-log-analytics (1.394s)
  (✓) Done: Application Insights: BenSetListAgt-app-insights (1.056s)
  (✓) Done: Container Apps Environment: BenSetListAgt (17.427s)
  (✓) Done: Container App: setlistfm-mcp (17.225s)
  (✓) Done: Container App: weather-mcp (17.21s)
  (✓) Done: Container App: spotify-mcp (33.879s)
  (✓) Done: Container App: setlistfm-agent (17.3s)

Deploying services (azd deploy)

  (✓) Done: Deploying service setlistfm_mcp
  - Endpoint: https://setlistfm-mcp.wittysky-056318b3.francecentral.azurecontainerapps.io/

  (✓) Done: Deploying service spotify_mcp
  - Endpoint: https://spotify-mcp.wittysky-056318b3.francecentral.azurecontainerapps.io/

  (✓) Done: Deploying service setlistfm_agent
  - Endpoint: https://setlistfm-agent.wittysky-056318b3.francecentral.azurecontainerapps.io/
```

1. Update `.vscode/mcp.json` file with output provided

```
 "setlistfm": {
      "type": "sse",
      "url": "https://setlistfm-mcp.wittysky-056318b3.francecentral.azurecontainerapps.io/sse",
      "url_local": "http://localhost:9000/sse",
    },
    "spotify": {
      "type": "sse",
      "url": "https://spotify-mcp.wittysky-056318b3.francecentral.azurecontainerapps.io/sse",
      "url_local": "http://localhost:9001/sse",
    }
```

## What I've Learned

### 🤖 Building Intelligent Agents with Semantic Kernel

- **Agent Architecture**: Created an enhanced agent using Semantic Kernel's `ChatCompletionAgent` with `ChatHistoryAgentThread` for persistent conversation context
- **Function Choice Behavior**: Implemented intelligent tool selection where the agent can dynamically choose between MCP plugins (Setlist.fm, Spotify) based on user queries
- **Agent Lifecycle**: Proper initialization and shutdown handling ensures clean resource management across chat sessions
- **Thread Management**: Each user gets their own thread, enabling isolated, stateful conversations with proper session management

### 🔌 Mastering Model Context Protocol (MCP)

- **Remote MCP Servers**: Successfully deployed and connected to remote MCP servers on Azure Container Apps using SSE (Server-Sent Events) transport
- **MCP Plugin Integration**: Used Semantic Kernel's `MCPSsePlugin` to seamlessly integrate external MCP servers as first-class tools
- **Multi-Transport Support**: Implemented both SSE and Streamable HTTP transports, with automatic endpoint discovery and health checks
- **Tool Orchestration**: Agent intelligently coordinates between multiple MCP servers (Setlist.fm for concert data, Spotify for music data) based on user intent
- **FastMCP Framework**: Leveraged FastMCP for rapid MCP server development with built-in SSE transport and tool registration

### 🔐 OAuth Authentication & Session Management

- **Multi-Provider OAuth**: Implemented Spotify OAuth 2.0 integration with Chainlit's OAuth provider system
- **Token Lifecycle Management**: Built robust token refresh logic, secure storage in user sessions, and expiration handling
- **Authentication Flow**: Created seamless authentication experience with redirect handling and state validation
- **MCP Authentication**: Extended MCP servers to support Bearer token authentication, forwarding user tokens from agent to services
- **Session Security**: Implemented proper session isolation where each user's authentication state is managed independently

### 🏗️ MCP Server Architecture Patterns

- **Authentication Patterns**:
  - **API Key Auth**: Setlist.fm MCP server uses header-based API key authentication
  - **OAuth Bearer**: Spotify MCP server accepts Bearer tokens forwarded from the agent
  - **Client Credentials**: Fallback to Spotify client credentials flow for public data
- **Middleware Design**: Built logging middleware for MCP operations and token extraction utilities
- **Health Endpoints**: Implemented liveness and readiness probes for Azure Container Apps deployment
- **Error Handling**: Comprehensive error handling with user-friendly messages and proper HTTP status codes

### 🌐 Cloud-Native MCP Deployment

- **Container Orchestration**: Deployed multiple MCP servers as independent Azure Container Apps with proper networking
- **Service Discovery**: Automated MCP configuration generation using environment variables and azd tooling
- **Remote vs Local**: Designed for seamless switching between local development and remote production MCP servers
- **Authentication Passthrough**: Implemented secure token forwarding from Chainlit agent to remote MCP services

### 🔄 Integration Lessons

- **Agent-to-MCP Communication**: Learned to properly pass authentication context from conversational agent to backend MCP services
- **Multi-Service Coordination**: Built patterns for agents to intelligently route requests between different specialized MCP servers
- **State Management**: Mastered session management across multiple authentication contexts (Chainlit OAuth + MCP Bearer tokens)
- **Development Workflow**: Created efficient dev-to-prod pipeline with local MCP development and cloud deployment automation

### 🛠️ Technical Insights

- **Async Patterns**: Extensively used Python async/await for all HTTP calls, MCP connections, and agent operations
- **Type Safety**: Leveraged Python 3.11+ type hints throughout for better code reliability and IDE support
- **Configuration Management**: Environment-based configuration with fallbacks and validation for different deployment scenarios
- **Logging Strategy**: Implemented structured logging across agent, MCP servers, and authentication flows for observability

---

## Links

1. https://techcommunity.microsoft.com/blog/appsonazureblog/host-remote-mcp-servers-in-azure-container-apps/4403550, https://github.com/anthonychu/azure-container-apps-mcp-sample

1. https://code.visualstudio.com/docs/copilot/chat/mcp-servers

1. https://learn.microsoft.com/en-us/semantic-kernel/concepts/plugins/adding-mcp-plugins?pivots=programming-language-python
