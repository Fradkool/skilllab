FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgl1-mesa-glx \
    poppler-utils \
    gcc \
    g++ \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set up working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Create output directories
RUN mkdir -p /app/data/output/images \
    && mkdir -p /app/data/output/ocr_results

# Copy OCR service code
COPY ocr_service.py /app/

# Create directory for language models
RUN mkdir -p /app/models

# Download English model (can add more languages as needed)
RUN python -c "from paddleocr import PaddleOCR; PaddleOCR(lang='en', use_angle_cls=True, download_models=True)"

# Expose port for API
EXPOSE 8080

# Run the OCR service
CMD ["python", "ocr_service.py"]