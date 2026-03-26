FROM python:3.12-slim

WORKDIR /app

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml ./
RUN uv pip install --system --no-cache ".[dev]" 2>/dev/null || uv pip install --system --no-cache .

COPY . .

EXPOSE 8001

CMD ["uvicorn", "odgg.app:app", "--host", "0.0.0.0", "--port", "8001"]
