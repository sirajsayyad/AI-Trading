FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry==1.8.4

# Copy dependency files first for better layer caching
COPY pyproject.toml ./

# Configure Poetry: no virtualenv in container
RUN poetry config virtualenvs.create false

# Install dependencies (without dev deps for production)
RUN poetry install --no-interaction --no-ansi --no-root --no-dev 2>/dev/null || \
    poetry install --no-interaction --no-ansi --no-root

# Copy application code
COPY . .

# Install the project itself
RUN poetry install --no-interaction --no-ansi

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
