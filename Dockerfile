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
# NOTE: For production, consider pinning package versions for reproducibility
# ffmpeg: for video merging/processing
# aria2: for download acceleration
# git: often needed for pip installing from git repos
RUN apt-get update && apt-get install -y \
    ffmpeg \
    aria2 \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
# NOTE: Ensure requirements.txt has pinned versions for security
# For enhanced security, consider using: pip install --require-hashes -r requirements.txt
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Create a volume for downloads and config
VOLUME ["/app/downloads", "/root/.streamcatch"]

# Expose Flet web port
EXPOSE 8550

# Run the application
CMD ["python", "main.py"]
