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

# Copy Poetry project files (build context is repo root)
COPY ./services/memos.as/pyproject.toml ./services/memos.as/poetry.lock* ./

# Copy the shared core library
COPY ./libs/apexsigma-core ./libs/apexsigma-core

# Install dependencies without dev packages for production
RUN poetry install --no-root --only=main

# Copy the application's source code
COPY ./services/memos.as/ ./