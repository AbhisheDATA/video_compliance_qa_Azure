# --- STAGE 1: BUILDER ---
# Use a temporary image to compile dependencies and build wheels
FROM python:3.12-slim as builder

# Prevent Python from writing pyc files and buffering stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system build dependencies (if strictly needed for some packages)
# For now, we install basic build tools ensuring we can compile source distributions if needed
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create a virtual environment to isolate dependencies
RUN python -m venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Install python dependencies into the virtual environment
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# --- STAGE 2: RUNNER ---
# Use a clean, slim image for the final runtime
FROM python:3.12-slim as runner

WORKDIR /app

# Install runtime dependencies (ffmpeg is required for yt-dlp)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy the virtual environment from the builder stage
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy application source code
COPY . .

# Create a non-root user for security (Defense in Depth)
RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose the application port
EXPOSE 8000

# Run the application
# We use the python executable from the venv environment
CMD ["uvicorn", "backend.src.api.server:app", "--host", "0.0.0.0", "--port", "8000"]
