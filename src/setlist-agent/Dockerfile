# Dockerfile for setlist-agent ACA microservice
FROM python:3.13-slim

# Install uv (universal virtualenv and package manager)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy project files
COPY . /app

# Install dependencies using uv
RUN uv sync --frozen --no-cache --prerelease=allow

EXPOSE 80

CMD ["/app/.venv/bin/chainlit", "run", "main.py", "--port", "80","--host", "0.0.0.0"]
