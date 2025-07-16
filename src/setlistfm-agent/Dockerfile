FROM python:3.11-slim

# Install uv (universal virtualenv and package manager)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Copy project files
COPY . /app

# Install dependencies using uv
#RUN uv sync --frozen
RUN uv sync --frozen --no-cache --prerelease=allow


# Create non-root user
#RUN groupadd -r appuser && useradd -r -g appuser appuser
#RUN chown -R appuser:appuser /app
#USER appuser

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:80/health')" || exit 1

# Run the application
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
