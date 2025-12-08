# Use official Python lightweight image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLET_WEB=1
ENV FLET_SERVER_PORT=8550

# Set work directory
WORKDIR /app

# Install system dependencies with pinned versions for reproducibility
# ffmpeg: for video merging/processing
# aria2: for download acceleration
# git: often needed for pip installing from git repos
RUN apt-get update && apt-get install -y \
    ffmpeg=7:5.1.6-0+deb12u1 \
    aria2=1.36.0-1+deb12u1 \
    git=1:2.39.5-0+deb12u1 \
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

# Run the application
CMD ["python", "main.py"]
