# SkillLab

SkillLab is a comprehensive pipeline for extracting structured data from resumes using OCR and AI techniques. It processes resumes through OCR extraction, JSON generation, auto-correction, and model training, with human review capabilities.

## 🌟 Features

- **OCR Extraction**: Convert PDFs to text using PaddleOCR
- **JSON Generation**: Transform extracted text to structured JSON using Mistral 7B
- **Auto-Correction**: Validate and improve extracted data quality
- **Human Review**: Web interface for reviewing and correcting extractions
- **Model Training**: Fine-tune Donut model for improved document understanding
- **Containerization**: Docker-based deployment for reliable, scalable processing
- **Monitoring**: Real-time performance and resource usage tracking

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourorg/skilllab.git
cd skilllab

# Run the installation script
bash install.sh

# Start required services
docker-compose up -d
```

### Basic Usage

```bash
# Activate virtual environment (if not already active)
source venv/bin/activate

# Run the full pipeline
skilllab run pipeline --input-dir data/input --output-dir data/output

# Launch the review interface
skilllab ui review --ui-type web

# Check system status
skilllab monitor status
```

## 📚 Documentation

- [Installation Guide](docs/INSTALLATION.md) - Detailed setup instructions
- [CLI Reference](docs/CLI_README.md) - Complete command-line interface reference
- [Architecture Overview](docs/ARCHITECTURE.md) - System design and components
- [Docker Deployment](docs/DOCKER_DEPLOYMENT.md) - Container setup and management
- [API Documentation](docs/API.md) - Programmatic interface reference

## 🏗️ Architecture

SkillLab follows a modular, layered architecture:

```
            ┌─────────────┐     ┌─────────────┐
            │    CLI UI   │     │    Web UI   │
            └──────┬──────┘     └──────┬──────┘
                   │                   │
                   ▼                   ▼
            ┌─────────────────────────────────┐
            │           API Layer             │
            └─┬─────────────┬────────────────┬┘
              │             │                │
    ┌─────────▼──────┐ ┌────▼─────┐  ┌───────▼───────┐
    │ Database Layer │ │ Pipeline │  │ Training Layer │
    └─┬──────────────┘ └────┬─────┘  └───────────────┘
      │                     │
┌─────▼─────┐      ┌───────┼───────┬───────────┐
│ Metrics DB │      │       │       │           │
└───────────┘      ▼       ▼       ▼           ▼
              ┌─────────┐ ┌─────┐ ┌─────┐ ┌──────────┐
              │   OCR   │ │ LLM │ │Auto │ │  Review  │
              │Extraction│ │ JSON│ │Corr.│ │ Interface│
              └────┬────┘ └──┬──┘ └─────┘ └──────────┘
                   │        │
                   ▼        ▼
              ┌─────────┐ ┌─────────┐
              │PaddleOCR│ │ Ollama  │
              │Container│ │Container│
              └─────────┘ └─────────┘
```

### Core Components

- **API Layer**: Clean interfaces to all functionality
- **Database Layer**: Repository pattern for data access
- **Pipeline System**: Modular processing steps
- **UI Components**: Web and CLI interfaces
- **Monitoring**: Performance and resource tracking
- **Containerized Services**: OCR and LLM processing

## 📋 Requirements

- Python 3.8+
- Docker and Docker Compose
- NVIDIA GPU (recommended for performance)
- 8GB+ RAM
- 20GB+ storage space

## 🛠️ Development

### Project Structure

```
skilllab/
├── api/                    # API layer
│   ├── extraction.py       # Resume extraction operations
│   ├── training.py         # Model training operations
│   ├── review.py           # Review system operations
│   └── monitoring.py       # System monitoring operations
│
├── config/                 # Configuration management
│   ├── default.yaml        # Default configuration values
│   ├── loader.py           # Configuration loading utilities
│   └── schema.py           # Configuration validation schemas
│
├── database/               # Database layer with repositories
│   ├── core.py             # Core database functionality
│   ├── metrics_db.py       # Metrics database operations
│   ├── review_db.py        # Review database operations
│   └── sync.py             # Database synchronization
│
├── extraction/             # OCR and JSON extraction
│   ├── ocr_extractor.py    # PDF to text extraction using OCR
│   ├── json_generator.py   # Text to JSON using LLM
│   └── auto_correction.py  # JSON validation and correction
│
├── pipeline/               # Pipeline architecture
│   ├── base.py             # Pipeline interfaces
│   ├── executor.py         # Pipeline execution logic
│   └── steps/              # Individual pipeline steps
│
├── schemas/                # Data schema definitions
│   ├── resume.json         # Resume JSON schema
│   ├── metrics.json        # Metrics tracking schema
│   └── validation.py       # Schema validation utilities
│
├── tests/                  # Testing infrastructure
│   ├── conftest.py         # Test configuration
│   ├── unit/               # Unit tests
│   └── integration/        # Integration tests
│
├── training/               # Model training components
│   ├── dataset_builder.py  # Dataset creation
│   └── train_donut.py      # Model training
│
├── ui/                     # User interfaces
│   ├── base.py             # UI base components
│   ├── cli/                # CLI interface components
│   ├── web/                # Web interface components
│   └── common/             # Shared UI utilities
│
├── monitor/                # System monitoring
│   ├── dashboard.py        # Monitoring dashboard
│   ├── metrics.py          # Metrics collection
│   └── integration.py      # Pipeline integration
│
├── review/                 # Review system
│   ├── app.py              # Review application
│   └── db_manager.py       # Review database manager
│
├── docker/                 # Docker service definitions
│   ├── paddleocr/          # OCR service
│   └── ollama/             # LLM service
│
├── cli.py                  # Main CLI entrypoint
├── main.py                 # Application entrypoint
├── install.sh              # Installation script
├── setup_cli.sh            # CLI setup script
└── requirements.txt        # Dependencies
```

## 🔄 Pipeline Workflow

The SkillLab pipeline consists of five main steps:

1. **OCR Extraction**: Convert PDFs to text using PaddleOCR
2. **JSON Generation**: Generate structured JSON using Mistral 7B
3. **Auto-Correction**: Validate and improve JSON quality
4. **Dataset Building**: Prepare datasets for fine-tuning
5. **Model Training**: Fine-tune Donut for document understanding

## 📊 Monitoring & Review

SkillLab includes a comprehensive monitoring and review system:

- **Real-time metrics**: Resource usage, pipeline progress, document statistics
- **Quality assessment**: Automatic confidence scoring and issue flagging
- **Review interface**: Web-based UI for reviewing and correcting extractions
- **Performance tracking**: Historical data and trend analysis

## 📄 License

[MIT License](LICENSE)