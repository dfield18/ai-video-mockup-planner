FROM python:3.10-slim

WORKDIR /app

# Copy backend requirements and install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ .

# Expose port
EXPOSE 8000

# Start command (Railway sets PORT env var)
CMD ["sh", "-c", "uvicorn ai_video_mockup_planner.api:app --host 0.0.0.0 --port ${PORT:-8000}"]
