FROM python:3.12-slim

# Install uv.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH /app/src

# Set the working directory
WORKDIR /app

# Copy only the requirements file to leverage Docker cache
COPY pyproject.toml uv.lock ./

# Install dependencies using uv
RUN uv sync --frozen --no-cache

# Copy alembic configuration files
COPY alembic.ini /app/alembic.ini
COPY alembic /app/alembic

# Copy application code to the working directory
COPY ./src /app/src

# Copy and set up the entrypoint script
COPY ./entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Expose the port the app runs on
EXPOSE 8000

# Set the entrypoint script to run on container start
ENTRYPOINT ["/app/entrypoint.sh"]

# Command to run the application, pointing to src/run.py
CMD ["uv", "run", "fastapi", "run", "src/run.py", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
