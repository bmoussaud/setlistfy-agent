"""
FastAPI main application for SetlistFM Agent
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn


from configuration import settings, validate_required_settings
from setlistfm_agent import setlistfm_agent



# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("setlistfm_agent.main")
# Set Azure SDK HTTP logging policy to ERROR
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.ERROR)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    logger.info("Starting SetlistFM Agent service...")

    try:
        # Validate configuration
        validate_required_settings()

        # Initialize the agent
        await setlistfm_agent.initialize()

        logger.info("SetlistFM Agent service started successfully")
        yield

    except Exception as e:
        logger.error(f"Failed to start service: {e}")
        raise
    finally:
        logger.info("Shutting down SetlistFM Agent service...")
        await setlistfm_agent.shutdown()


# Create FastAPI app
app = FastAPI(
    title="SetlistFM Agent",
    description="AI Foundry SDK agent for setlist content management with Bing Grounding",
    version="0.1.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response models


class ChatRequest(BaseModel):
    """Chat request model."""
    message: str = Field(..., description="User message to process")
    thread_id: Optional[str] = Field(
        None, description="Optional thread ID for conversation continuity")


class ChatResponse(BaseModel):
    """Chat response model."""
    thread_id: str = Field(...,
                           description="Thread ID for conversation continuity")
    response: str = Field(..., description="Agent response")
    citations: List[Dict[str, str]] = Field(
        default_factory=list, description="Source citations")
    status: str = Field(..., description="Response status")


class SetlistSearchRequest(BaseModel):
    """Setlist search request model."""
    artist: str = Field(..., description="Artist name")
    venue: Optional[str] = Field(None, description="Optional venue name")


class VenueInfoRequest(BaseModel):
    """Venue information request model."""
    venue_name: str = Field(..., description="Venue name")
    city: Optional[str] = Field(None, description="Optional city name")


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="Service version")


# Health check endpoints
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(status="healthy", version="0.1.0")


@app.get("/ready", response_model=HealthResponse)
async def readiness_check():
    """Readiness check endpoint."""
    if not setlistfm_agent._initialized:
        raise HTTPException(status_code=503, detail="Service not ready")
    return HealthResponse(status="ready", version="0.1.0")


# Chat endpoints
@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Process a chat message with the SetlistFM agent."""
    try:
        logger.info(f"Processing chat request: {request.message[:100]}...")

        result = await setlistfm_agent.chat(
            message=request.message,
            thread_id=request.thread_id
        )

        return ChatResponse(**result)

    except Exception as e:
        logger.error(f"Error processing chat request: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/chat/history/{thread_id}")
async def get_chat_history(thread_id: str) -> List[Dict[str, Any]]:
    """Get chat history for a specific thread."""
    try:
        history = await setlistfm_agent.get_thread_history(thread_id)
        return history

    except Exception as e:
        logger.error(f"Error getting chat history: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Specialized endpoints
@app.post("/search/setlists", response_model=ChatResponse)
async def search_setlists(request: SetlistSearchRequest) -> ChatResponse:
    """Search for setlists for a specific artist."""
    try:
        logger.info(f"Searching setlists for artist: {request.artist}")

        result = await setlistfm_agent.search_setlists(
            artist=request.artist,
            venue=request.venue
        )

        return ChatResponse(**result)

    except Exception as e:
        logger.error(f"Error searching setlists: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/venues/info", response_model=ChatResponse)
async def get_venue_info(request: VenueInfoRequest) -> ChatResponse:
    """Get information about a venue."""
    try:
        logger.info(f"Getting venue info for: {request.venue_name}")

        result = await setlistfm_agent.get_venue_info(
            venue_name=request.venue_name,
            city=request.city
        )

        return ChatResponse(**result)

    except Exception as e:
        logger.error(f"Error getting venue info: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "SetlistFM Agent",
        "version": "0.1.0",
        "description": "AI Foundry SDK agent for setlist content management with Bing Grounding",
        "endpoints": {
            "chat": "/chat",
            "setlist_search": "/search/setlists",
            "venue_info": "/venues/info",
            "health": "/health",
            "ready": "/ready"
        }
    }


if __name__ == "__main__":
    # Configure uvicorn to instrument FastAPI for telemetry
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

    try:
        FastAPIInstrumentor.instrument_app(app)
        logger.info("FastAPI instrumentation configured")
    except Exception as e:
        logger.warning(f"Failed to instrument FastAPI: {e}")

    # Run the application
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower()
    )
