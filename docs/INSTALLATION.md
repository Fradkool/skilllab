# SkillLab Installation Guide

This guide provides comprehensive instructions for installing SkillLab on your system. The installation process includes setting up dependencies, configuring services, and preparing the environment for running the full pipeline.

## System Requirements

- **Operating System**: Linux (Ubuntu 20.04+ recommended), macOS, or Windows with WSL2
- **CPU**: 4+ cores recommended
- **RAM**: 8GB minimum, 16GB+ recommended
- **Storage**: 20GB+ free space
- **GPU**: NVIDIA GPU with 8GB+ VRAM recommended (CPU-only mode available)
- **Software**: Docker, Docker Compose, Python 3.8+

## Quick Installation

For a quick setup with default options, use the provided installation script:

```bash
# Clone the repository
git clone https://github.com/yourorg/skilllab.git
cd skilllab

# Run the installation script
bash install.sh

# Start the services
docker-compose up -d
```

The `install.sh` script will:
1. Check system requirements
2. Install Python dependencies
3. Set up Docker services
4. Configure the CLI
5. Initialize the environment

## Manual Installation

If you prefer to install components manually or need more control over the process, follow these steps:

### 1. Python Environment Setup

```bash
# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate     # Windows

# Install Python dependencies
pip install --upgrade pip
pip install -e .
pip install -r requirements.txt
```

### 2. Docker Setup

```bash
# Install Docker (if not already installed)
# For Ubuntu:
sudo apt-get update
sudo apt-get install -y apt-transport-https ca-certificates curl software-properties-common
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.3/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Add your user to the docker group (to avoid using sudo)
sudo usermod -aG docker $USER
# Log out and back in for this to take effect
```

### 3. Service Setup

```bash
# Start the containerized services
docker-compose up -d

# Wait for services to start, then initialize Ollama with the Mistral model
# (This may take a while the first time)
bash docker/ollama/init-ollama.sh
```

### 4. CLI Setup

```bash
# Make the CLI executable
chmod +x cli.py

# Create command aliases
bash setup_cli.sh
```

### 5. Configuration (Optional)

Edit `config/default.yaml` to customize settings:

```bash
# Copy the example config
cp config/default.yaml config/local.yaml

# Edit the configuration
nano config/local.yaml
```

## Verification

Verify your installation with these commands:

```bash
# Check that the CLI works
skilllab --version

# Check service health
skilllab health check

# Run a simple extraction test
skilllab run extract --input-dir examples/sample_pdfs --limit 1
```

## GPU Support Setup

For NVIDIA GPU support:

```bash
# Install NVIDIA Container Toolkit
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit

# Restart Docker
sudo systemctl restart docker

# Test GPU access in containers
docker run --gpus all nvidia/cuda:11.0-base nvidia-smi
```

## Installation Options

The installation script supports several options:

```bash
# Show installation script help
bash install.sh --help

# Install with specific services
bash install.sh --services paddleocr,ollama

# Install without GPU support
bash install.sh --cpu-only

# Install with custom data directory
bash install.sh --data-dir /path/to/data
```

## Troubleshooting

### Common Issues

1. **Docker permission errors**
   ```
   Got permission denied while trying to connect to the Docker daemon socket
   ```
   **Solution**: Add your user to the docker group and log out/in:
   ```bash
   sudo usermod -aG docker $USER
   # Log out and back in
   ```

2. **Missing models**
   ```
   Error: Model 'mistral:7b-instruct-v0.2-q8_0' not found
   ```
   **Solution**: Pull the model manually:
   ```bash
   curl -X POST http://localhost:11434/api/pull -d '{"name": "mistral:7b-instruct-v0.2-q8_0"}'
   ```

3. **Service not responding**
   ```
   Connection refused when connecting to localhost:8080
   ```
   **Solution**: Check service logs and restart:
   ```bash
   docker-compose logs paddleocr
   docker-compose restart paddleocr
   ```

4. **Out of memory errors**
   ```
   CUDA out of memory
   ```
   **Solution**: Adjust memory limits in `config/local.yaml`:
   ```yaml
   training:
     batch_size: 2  # Reduce batch size
     gradient_accumulation_steps: 4  # Increase gradient accumulation
   ```

### Getting Help

If you encounter issues not covered in this guide:

1. Check the log files in the `logs/` directory
2. Review Docker service logs with `docker-compose logs`
3. Run the health check with `skilllab health check --all`
4. Check for CUDA availability with `python -c "import torch; print(torch.cuda.is_available())"`

## Next Steps

After installation:

1. Place resume PDFs in your input directory
2. Run your first pipeline with `skilllab run pipeline`
3. Check the monitoring dashboard with `skilllab monitor status`
4. Review extraction results with `skilllab ui review`

For more information, refer to the [CLI Reference](CLI_README.md) and [Docker Deployment](DOCKER_DEPLOYMENT.md) guides.