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
    POETRY_VENV_IN_PROJECT=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

# Copy Poetry project files (build context is repo root)
COPY ./services/memos.as/pyproject.toml ./pyproject.toml
COPY ./services/memos.as/poetry.lock* ./
# COPY ./services/memos.as/README.md ./README.md

# Copy the shared core library and devenviro dependency
COPY ./libs/apexsigma-core /code/libs/apexsigma-core
COPY ./services/devenviro.as /code/devenviro.as

# Copy dependency files first for better caching
COPY pyproject.toml poetry.lock ./

# Install dependencies without dev packages for production
RUN poetry install --no-root --only=main

# Copy the application's source code
COPY ./services/memos.as/ /code/

# Copy the application's source code
COPY ./services/memos.as/ /code/


# Command to run the application
CMD ["poetry", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8090"]