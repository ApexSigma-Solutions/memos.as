# Use an official Python runtime as a parent image
FROM python:3.13-slim

# Set the working directory in the container
WORKDIR /code

# Add the app directory to the PYTHONPATH
ENV PYTHONPATH=/code

# Install curl
RUN apt-get update && apt-get install -y curl

# Install Poetry
RUN pip install poetry

# Configure Poetry
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_CACHE_DIR=/tmp/poetry_cache

# Copy Poetry project files (build context is ROOT, not service dir)
COPY services/memos.as/pyproject.toml services/memos.as/poetry.lock* ./

# Copy the shared core library from root
COPY libs/apexsigma-core ./libs/apexsigma-core

# Install dependencies including main packages
RUN poetry install --no-root

# Copy the application's source code from service dir
COPY services/memos.as/app ./app

# Run the application
CMD ["poetry", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8090"]