FROM python:3.13-slim

# Install uv.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy the application into the container.
COPY . /app

# Install the application dependencies.
WORKDIR /app
RUN uv sync --frozen --no-cache

EXPOSE 80
ENV FASTMCP_EXPERIMENTAL_ENABLE_NEW_OPENAPI_PARSER=true
# Run the application.
CMD ["/app/.venv/bin/fastmcp", "run", "/app/spotify.py", "--port", "80", "--host", "0.0.0.0","--transport","http"]
