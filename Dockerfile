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

# Copy poetry files and README
COPY pyproject.toml poetry.lock* README.md ./

# Install dependencies
RUN poetry install --no-dev

# Copy the application's code to the working directory
COPY ./app /code/app

# Command to run the application
CMD ["poetry", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8090"]