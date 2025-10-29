# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps (minimal). Uncomment if you hit build/runtime issues with DB drivers.
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     libpq-dev gcc build-essential && \
#     rm -rf /var/lib/apt/lists/*

# Install Python deps first for better layer caching
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt pandas

# Copy project
COPY . /app

# Streamlit config (port overridable via PORT env)
EXPOSE 8501
ENV PORT=8501

# Run the Streamlit app
CMD ["bash", "-lc", "streamlit run app.py --server.port=${PORT} --server.address=0.0.0.0"]