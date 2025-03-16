# SkillLab Docker Deployment Guide

This guide provides step-by-step instructions for deploying SkillLab with containerized services for OCR extraction and LLM-based JSON generation.

## Prerequisites

- Docker and Docker Compose
- NVIDIA Container Toolkit (for GPU support)
- Git (to clone the repository)
- 8GB+ RAM
- 20GB+ free disk space
- NVIDIA GPU with 8GB+ VRAM (recommended for performance)

## Quick Start

For a quick start with default settings:

```bash
# Clone the repository (if you haven't already)
git clone https://github.com/your-org/skilllab.git
cd skilllab

# Build and start containers
docker-compose up -d

# Initialize Ollama with required models
chmod +x docker/ollama/init-ollama.sh
./docker/ollama/init-ollama.sh

# Verify services are running
curl http://localhost:11434/api/tags    # Ollama
curl http://localhost:8080/health       # PaddleOCR
```

## Detailed Setup

### 1. System Requirements

Ensure your system meets these requirements:
- Docker Engine 20.10+
- Docker Compose 2.0+
- NVIDIA Container Toolkit (for GPU acceleration)
- NVIDIA Driver 470+ (for GPU acceleration)

### 2. Configuration

1. **Environment Setup**

Create an `.env` file in the project root to override default settings:

```
# Docker service ports
OLLAMA_PORT=11434
PADDLEOCR_PORT=8080

# Resource limits
OLLAMA_MEMORY=8g
PADDLEOCR_MEMORY=4g

# GPU settings
NVIDIA_VISIBLE_DEVICES=all
```

2. **Application Configuration**

Update the `config/default.yaml` file to use the containerized services:

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
  temperature: 0.1
  max_tokens: 2048
  max_retries: 3
  timeout: 300
```

### 3. Container Management

1. **Starting Services**

```bash
# Start both services
docker-compose up -d

# Start only specific service
docker-compose up -d ollama
docker-compose up -d paddleocr
```

2. **Stopping Services**

```bash
# Stop all services
docker-compose down

# Stop specific service
docker-compose stop ollama
docker-compose stop paddleocr
```

3. **Viewing Logs**

```bash
# View logs for all services
docker-compose logs

# View logs for specific service with follow
docker-compose logs -f ollama
docker-compose logs -f paddleocr
```

4. **Rebuilding Services**

```bash
# Rebuild a specific service
docker-compose build --no-cache paddleocr
docker-compose up -d paddleocr
```

### 4. Service Initialization

1. **Ollama Model Setup**

After starting the Ollama container, initialize it with the required models:

```bash
chmod +x docker/ollama/init-ollama.sh
./docker/ollama/init-ollama.sh
```

This script will download the Mistral 7B Instruct model needed for JSON generation.

2. **Verifying Service Health**

```bash
# Check Ollama health and available models
curl http://localhost:11434/api/tags

# Check PaddleOCR service health
curl http://localhost:8080/health
```

### 5. Volumes and Data Management

The Docker Compose setup uses the following volumes:

- `./data/ollama` - Persists Ollama models
- `./data` - Shared between containers and host for input/output files

Data flow:
1. Put PDF files in `./data/input`
2. OCR service processes PDFs and saves results to `./data/output`
3. Main application reads from and writes to these directories

### 6. Customizing Models

To use a different LLM model with Ollama:

1. Pull the model using the Ollama API:
```bash
curl -X POST http://localhost:11434/api/pull -d '{"name": "YOUR_MODEL_NAME"}'
```

2. Update the `config/default.yaml` to use the new model:
```yaml
json_generation:
  model_name: "YOUR_MODEL_NAME"
```

## Production Deployment

For production environments, consider these additional steps:

### 1. Security Considerations

- Configure firewall rules to restrict access to Docker service ports
- Use a reverse proxy (like Nginx) with HTTPS for external access
- Set custom passwords for services if applicable

### 2. Resource Optimization

Adjust memory and CPU limits in docker-compose.yml:

```yaml
services:
  ollama:
    deploy:
      resources:
        limits:
          memory: 8G
          cpus: '4'
  paddleocr:
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: '2'
```

### 3. Health Monitoring

- Set up container monitoring using tools like Prometheus and Grafana
- Configure alert notifications for service failures
- Implement automatic restarts for failed services

### 4. Backup Strategy

Regularly backup these important directories:
- `./data/ollama` - Contains downloaded models
- `./data` - Contains input files and processing results

```bash
# Example backup script
tar -czf skilllab_data_backup_$(date +%Y%m%d).tar.gz ./data
```

## Troubleshooting

### Common Issues

1. **Service Won't Start**

Check logs for errors:
```bash
docker-compose logs ollama
docker-compose logs paddleocr
```

2. **Out of Memory Errors**

Increase memory limits in docker-compose.yml:
```yaml
deploy:
  resources:
    limits:
      memory: 12G
```

3. **Ollama Model Download Failures**

If model download fails:
```bash
# Check Ollama logs
docker logs skilllab_ollama

# Retry model download manually
curl -X POST http://localhost:11434/api/pull -d '{"name": "mistral:7b-instruct-v0.2-q8_0"}'
```

4. **PaddleOCR Service Errors**

If OCR service fails:
```bash
# Check PaddleOCR logs
docker logs skilllab_paddleocr

# Rebuild the service
docker-compose build --no-cache paddleocr
docker-compose up -d paddleocr
```

### Getting Help

If you encounter issues not covered here:

1. Check the container logs for detailed error messages
2. Visit the project GitHub repository for known issues
3. Reach out to the development team via the project's support channels

## Maintenance

### Updating Services

To update to newer versions:

```bash
# Pull latest images
docker-compose pull

# Rebuild and restart services
docker-compose up -d --build
```

### Cleaning Up

To remove unused containers and images:

```bash
# Remove stopped containers
docker container prune

# Remove unused images
docker image prune

# Remove volumes (caution - data loss!)
docker volume prune
```

## Performance Tuning

For optimal performance:

1. **GPU Configuration**
   - Ensure NVIDIA drivers are up to date
   - Configure GPU memory split if using multiple services

2. **IO Optimization**
   - Use SSD storage for the data volume
   - Consider mounting volumes with `cached` or `delegated` options on macOS

3. **Network Performance**
   - Use host network mode for better performance if security permits
   - Configure Docker networking with jumbo frames for large transfers

## Conclusion

This deployment guide covers the basics of running SkillLab with containerized services. By following these instructions, you'll have a robust environment for OCR extraction and LLM-based JSON generation, with improved scalability and resource isolation.

For questions or contributions to this guide, please contact the SkillLab development team.