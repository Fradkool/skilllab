# SkillLab

SkillLab is a comprehensive pipeline for extracting structured data from resumes using OCR and AI techniques. It processes resumes through OCR extraction, JSON generation, auto-correction, and model training.

## Project Structure

```
skilllab/
├── api/                    # API layer for programmatic access
│   ├── extraction.py       # Resume extraction operations
│   ├── training.py         # Model training operations [planned]
│   ├── review.py           # Review system operations [planned]
│   └── monitoring.py       # System monitoring operations [planned]
│
├── config/                 # Configuration management
│   ├── default.yaml        # Default configuration values
│   ├── loader.py           # Configuration loading utilities
│   └── schema.py           # Configuration validation schemas
│
├── database/               # Database management
│   ├── core.py             # Core database functionality
│   ├── metrics_db.py       # Metrics database operations
│   ├── review_db.py        # Review database operations [planned]
│   └── sync.py             # Database synchronization [planned]
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
│       ├── ocr_step.py     # OCR extraction step
│       └── [other steps]   # Additional pipeline steps [planned]
│
├── schemas/                # Data schemas
│   ├── resume.json         # Resume JSON schema
│   ├── metrics.json        # Metrics tracking schema
│   └── validation.py       # Schema validation utilities
│
├── tests/                  # Testing infrastructure
│   ├── conftest.py         # Test configuration
│   ├── unit/               # Unit tests
│   │   ├── test_api/       # API tests
│   │   ├── test_pipeline/  # Pipeline tests [planned]
│   │   └── test_database/  # Database tests [planned]
│   └── integration/        # Integration tests [planned]
│
├── training/               # Model training
│   ├── dataset_builder.py  # Build training datasets
│   └── train_donut.py      # Fine-tune Donut model
│
├── ui/                     # User interfaces [planned]
│   ├── cli/                # CLI dashboard [planned]
│   ├── web/                # Web dashboard [planned]
│   └── common/             # Shared UI components [planned]
│
├── monitor/                # Monitoring system (to be migrated to api/ui)
│   ├── dashboard.py        # CLI monitoring dashboard
│   ├── metrics.py          # Metrics collection and tracking
│   └── integration.py      # Integration with main pipeline
│
├── review/                 # Review system (to be migrated to api/ui)
│   ├── app.py              # Streamlit web application
│   └── db_manager.py       # Review database management
│
├── utils/                  # Utility functions
│   ├── logger.py           # Logging utilities
│   ├── gpu_monitor.py      # GPU monitoring utilities
│   └── db_sync.py          # Database sync (to be migrated)
│
├── data/                   # Data directories
│   ├── input/              # Input resume PDFs
│   └── output/             # Processing outputs
│       ├── images/         # Extracted resume images
│       ├── ocr_results/    # OCR extraction results
│       ├── json_results/   # Generated JSONs
│       ├── validated_json/ # Validated JSONs
│       └── donut_dataset/  # Prepared dataset for Donut
│
├── docs/                   # Documentation
│   ├── REFACTORING.md      # Refactoring plan
│   └── REFACTORING_STATUS.md # Current refactoring status
│
├── models/                 # Trained models
│   └── donut_finetuned/    # Fine-tuned Donut model
│
├── cli.py                  # Command-line interface
├── main.py                 # Main application entry point
└── requirements.txt        # Project dependencies
```

## Core Components

### 1. Resume Processing Pipeline

- **OCR Extraction**: Convert PDFs to text using PaddleOCR
- **JSON Generation**: Transform OCR text to structured JSON using Mistral 7B
- **Auto-Correction**: Validate and improve extracted data quality
- **Dataset Building**: Prepare annotated datasets for model training
- **Model Training**: Fine-tune Donut model for document understanding

### 2. API Layer

The API layer provides a clean programmatic interface to core functionality:

- **Extraction API**: Resume processing operations
- **Training API**: Model training operations [planned]
- **Review API**: Review system operations [planned]
- **Monitoring API**: System monitoring operations [planned]

### 3. Database Management

- **Core DB**: Common database functionality
- **Metrics DB**: Track pipeline metrics and performance
- **Review DB**: Store review status and human feedback [planned]

### 4. Human Review System

- **Web Interface**: Streamlit-based review dashboard
- **Confidence Scoring**: Automatic quality assessment
- **Issue Detection**: Flag documents requiring human attention
- **Correction Interface**: Edit and validate extractions

### 5. Monitoring System

- **CLI Dashboard**: Real-time pipeline monitoring
- **Metrics Collection**: Resource usage and performance tracking
- **Integration**: Connect monitoring to pipeline stages

## Current Development Status

The project is undergoing a refactoring process to improve code organization and maintainability. Refer to `docs/REFACTORING_STATUS.md` for detailed progress information.

Completed components:
- Configuration system (100%)
- Pipeline architecture (100%)
- Schema definitions (100%)

In progress:
- Database management (50%)
- API layer (40%)
- Testing structure (30%)

Not started:
- UI component separation (0%)

## Installation

```bash
# Clone repository
git clone https://github.com/yourorg/skilllab.git
cd skilllab

# Install dependencies
pip install -e .

# Install Ollama and pull Mistral model
ollama pull mistral:7b-instruct-v0.2-q8_0
```

## Usage

### Command-line Interface

```bash
# Run the full pipeline
skilllab run --input-dir data/input --output-dir data/output

# Run only OCR extraction
skilllab extract --input-dir data/input

# Run with human review enabled
skilllab run --human-review

# Launch review interface
skilllab review

# Launch monitoring dashboard
skilllab monitor
```

### API Usage

```python
from skilllab.api.extraction import extract_text_from_pdf, generate_json_from_text

# Extract text from PDF
ocr_result = extract_text_from_pdf("resume.pdf")

# Generate JSON from OCR result
json_result = generate_json_from_text(ocr_result)
```

## Configuration

The system uses a YAML-based configuration system. Default configuration is in `config/default.yaml` and can be overridden with environment variables or command-line arguments.

## Technical Constraints

- Optimized for RTX 3060 Ti (8GB VRAM)
- 100% local processing (no external APIs)
- Prevents hallucinations in extracted data

## License

[MIT License](LICENSE)