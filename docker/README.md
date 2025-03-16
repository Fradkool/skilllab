# SkillLab Docker Setup

This directory contains Docker setup for containerizing SkillLab's external dependencies:

1. **Ollama** - For LLM inference to generate structured JSON from OCR text
2. **PaddleOCR** - For OCR extraction from resume documents

## Prerequisites

- Docker and Docker Compose
- NVIDIA Container Toolkit (for GPU support)

## Getting Started

### 1. Build and Run Containers

```bash
# From the project root directory
docker-compose up -d
```

This will start both the Ollama and PaddleOCR services.

### 2. Initialize Ollama with Required Models

After the containers are up and running, initialize Ollama with the required models:

```bash
chmod +x docker/ollama/init-ollama.sh
./docker/ollama/init-ollama.sh
```

This script will pull the Mistral 7B Instruct model that is used for JSON generation.

### 3. Verify Services

Check that both services are running correctly:

```bash
# Check Ollama health
curl http://localhost:11434/api/tags

# Check PaddleOCR health
curl http://localhost:8080/health
```

## Service Details

### Ollama Service

- **Port**: 11434
- **API Endpoint**: http://localhost:11434/api/generate
- **Volume**: `./data/ollama` - Stores downloaded models

### PaddleOCR Service

- **Port**: 8080
- **API Endpoints**:
  - PDF Processing: http://localhost:8080/v1/ocr/process_pdf
  - Image Processing: http://localhost:8080/v1/ocr/process_image
  - Health Check: http://localhost:8080/health
- **Volume**: `./data` - Shared with the main application for input/output

## Configuration

Update your `config/default.yaml` to use the containerized services:

```yaml
# OCR settings
ocr:
  language: "en"
  dpi: 300
  min_confidence: 0.5
  service_url: "http://localhost:8080/v1/ocr/process_pdf"
  use_service: true  # Enable to use containerized PaddleOCR service

# JSON generation settings
json_generation:
  ollama_url: "http://localhost:11434/api/generate"
  model_name: "mistral:7b-instruct-v0.2-q8_0"
```

Alternatively, you can enable the services via command line arguments:

```bash
# Enable OCR service with default URL
python main.py --use_ocr_service

# Specify custom OCR service URL
python main.py --ocr_service_url "http://localhost:8080/v1/ocr/process_pdf"

# Enable Ollama with custom URL
python main.py --ollama_url "http://localhost:11434/api/generate"
```

## How It Works

### Overview

1. The PaddleOCR service provides a REST API that accepts PDF/image files and returns OCR results
2. The Ollama service provides an API for LLM inference
3. Both services can use GPU acceleration for better performance
4. Data is shared through mounted volumes, allowing the main application to access the results

### PaddleOCR Integration

When the OCR service is enabled, the application:

1. Checks the health of the OCR service before processing
2. Sends PDF files to the service via a multipart form POST request
3. Receives OCR results as JSON with extracted text and bounding boxes
4. Translates container paths to local paths for seamless integration
5. Has automatic fallback to direct PaddleOCR if the service is unavailable

### Ollama Integration

The JSON generation step:

1. Sends extracted text to Ollama's API with our enhanced client:
   - Performs health checks to ensure Ollama is available
   - Verifies the required model is loaded
   - Includes automatic retries with exponential backoff
   - Has proper error handling and fallback mechanisms
2. Uses a specialized prompt to structure the text into a JSON format
3. Validates the JSON against a schema to ensure correctness
4. Provides detailed metrics about the generation process

### Benefits of Containerization

1. **Isolation**: Dependencies are isolated from the main application
2. **Consistency**: Ensures the same environment across different machines
3. **Scaling**: Easier to deploy on multiple machines or in the cloud
4. **Resource Management**: Better control over GPU and memory usage
5. **Parallel Processing**: Both services can run on different GPUs or machines

## GPU Support

The Docker Compose file is configured to use NVIDIA GPUs if available. If you don't have a GPU or don't want to use it:

1. Remove the `deploy` sections from both services in the `docker-compose.yml` file
2. Set `use_gpu: false` when calling the PaddleOCR API

## Troubleshooting

### Ollama

If you encounter issues with Ollama:

```bash
# Check Ollama logs
docker logs skilllab_ollama

# Restart the Ollama service
docker restart skilllab_ollama
```

### PaddleOCR

If you encounter issues with PaddleOCR:

```bash
# Check PaddleOCR logs
docker logs skilllab_paddleocr

# Rebuild the PaddleOCR image
docker-compose build --no-cache paddleocr
docker-compose up -d paddleocr
```