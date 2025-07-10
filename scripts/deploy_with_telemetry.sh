#!/bin/bash
# Deploy script with OpenTelemetry configuration validation

set -e

echo "🚀 MySetlistAgent Deployment with OpenTelemetry Setup"
echo "=================================================="

# Check required environment variables
echo "✅ Checking required environment variables..."

required_vars=(
    "APPLICATIONINSIGHTS_CONNECTION_STRING"
    "AZURE_AI_INFERENCE_API_KEY"
    "AZURE_AI_INFERENCE_ENDPOINT"
    "MODEL_DEPLOYMENT_NAME"
    "SETLISTFM_MCP_URL"
    "SPOTIFY_MCP_URL"
)

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ Required environment variable $var is not set"
        exit 1
    else
        echo "✅ $var is set"
    fi
done

# Optional variables for enhanced tracing
echo "📊 Checking optional telemetry configuration..."
echo "AZURE_MONITOR_OPENTELEMETRY_ENABLED=${AZURE_MONITOR_OPENTELEMETRY_ENABLED:-false}"
echo "AZURE_TRACING_GEN_AI_CONTENT_RECORDING_ENABLED=${AZURE_TRACING_GEN_AI_CONTENT_RECORDING_ENABLED:-false}"

# Install dependencies
echo "📦 Installing Python dependencies..."

cd src/setlist-agent
pip install -e .
cd ../..

cd src/setlistfm-mcp-server
pip install -e .
cd ../..

cd src/spotify-mcp-server
pip install -e .
cd ../..

echo "✅ Dependencies installed successfully"

# Test OpenTelemetry configuration
echo "🔍 Testing OpenTelemetry configuration..."

python scripts/test_correlation_id.py

echo "✅ OpenTelemetry configuration validated"

# Build Docker images
echo "🐳 Building Docker images..."

docker build -t setlist-agent:latest src/setlist-agent/
docker build -t setlistfm-mcp-server:latest src/setlistfm-mcp-server/
docker build -t spotify-mcp-server:latest src/spotify-mcp-server/

echo "✅ Docker images built successfully"

# Deploy to Azure (using azd)
echo "🌐 Deploying to Azure..."

if command -v azd &> /dev/null; then
    azd up
    echo "✅ Deployment to Azure completed"
else
    echo "⚠️  Azure Developer CLI (azd) not found. Please install azd to deploy to Azure."
    echo "   Install: https://docs.microsoft.com/en-us/azure/developer/azure-developer-cli/install-azd"
fi

echo "🎉 Deployment completed successfully!"
echo ""
echo "📚 OpenTelemetry Documentation: docs/OPENTELEMETRY_SETUP.md"
echo "🔧 To view traces, check Azure Application Insights in the Azure Portal"
echo "🧪 To test correlation ID propagation, run: python scripts/test_correlation_id.py"
