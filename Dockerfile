FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# Copy backend requirements
COPY backend/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ ./backend/

# Copy static files
COPY static/ ./static/

# Copy frontend
COPY index.html ./static/

# Copy and run migration script
COPY backend/migrate.py .
RUN python migrate.py

EXPOSE 8080

CMD ["python", "backend/main.py"]
