# Use official Python lightweight image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLET_WEB=1
ENV FLET_SERVER_PORT=8550

# Set work directory
WORKDIR /app

# Install system dependencies
# ffmpeg: for video merging/processing
# aria2: for download acceleration
# git: often needed for pip installing from git repos
# curl: for healthcheck
RUN apt-get update && apt-get install -y \
    ffmpeg \
    aria2 \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r streamcatch && useradd -r -g streamcatch -u 1000 streamcatch

# Install Python dependencies
# All dependencies now have pinned versions for security
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Create necessary directories and set ownership
RUN mkdir -p /app/downloads /home/streamcatch/.streamcatch && \
    chown -R streamcatch:streamcatch /app /home/streamcatch

# Create a volume for downloads and config
VOLUME ["/app/downloads", "/home/streamcatch/.streamcatch"]

# Switch to non-root user
USER streamcatch

# Expose Flet web port
EXPOSE 8550

# Healthcheck
HEALTHCHECK CMD curl -f http://localhost:8550/ || exit 1

# Run the application
CMD ["python", "main.py"]
