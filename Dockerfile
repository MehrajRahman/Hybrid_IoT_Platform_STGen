# Use a slim Python image for performance and lower overhead
FROM python:3.11-slim

# Install system dependencies for Passive Mode binaries and NetEm
RUN apt-get update && apt-get install -y \
    build-essential \
    iproute2 \
    mosquitto-clients \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first to leverage Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project, including C source for binaries
COPY . .

# Compile Passive Mode binaries if they don't exist
RUN make -C protocols/custom_udp || true

# Set environment variables for non-buffered logging
ENV PYTHONUNBUFFERED=1

# The CMD is overridden by the orchestrator or Docker Compose
CMD ["python3", "-m", "stgen.main"]
