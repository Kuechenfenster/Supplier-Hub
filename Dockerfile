FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install additional dependencies for pipeline
RUN pip install --no-cache-dir pandas openpyxl

# Copy application code
COPY backend/ .
COPY static/ ./static/

# Create data directories for BOM uploads and documents
RUN mkdir -p data/incoming/boms data/documents data/processed data/reports

# Set PYTHONPATH for imports
ENV PYTHONPATH=/app

# Expose port
EXPOSE 9000

# Run the application
CMD ["python", "main.py"]
