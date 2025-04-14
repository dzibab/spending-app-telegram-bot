# Use an official Python runtime as a parent image
FROM python:3.13-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install dependencies using uv and pyproject.toml
RUN pip install uv && \
    uv sync

# Run the bot when the container starts
CMD ["uv", "run", "bot.py"]
