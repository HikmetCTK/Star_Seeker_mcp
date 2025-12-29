# Use a slim Python base image
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies (frozen to ensure consistency)
RUN uv sync --frozen --no-dev

# Copy application code
COPY config.py github_client.py search_engine.py server.py mcp_server.py ./
COPY README.md ./

# Expose port 8000 for potential HTTP MCP transport
EXPOSE 8000

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the MCP server
CMD ["uv", "run", "mcp_server.py"]
