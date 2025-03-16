Initial prompt, depreciated.

SkillLab is a subproject of SkillBase:

SkillBase is a project designed to create an intelligent and local platform for analyzing and managing skills extracted from resumes. Its goal is to provide a fast, accurate, and scalable tool to process large volumes of resumes and extract key information such as work experience, skills, education, and contact details. To ensure optimal and automated extraction, SkillLab was developed as a complementary project dedicated to training a Donut model specialized in reading and analyzing resumes. SkillLab generates an annotated dataset by leveraging PaddleOCR for text extraction, Mistral 7B via Ollama for JSON structuring with auto-correction, and Donut for learning document visual recognition. Once trained, Donut will be integrated into SkillBase as the extraction engine, enabling large-scale automated resume processing. SkillBase will then use this pre-trained model to process the remaining 39,000 resumes, ensuring reliable extraction without reliance on external APIs while guaranteeing a 100% local and open-source solution.
What You Need to Do

Analyze this project critically. There may be errors, so provide a constructive critique before proceeding to the code.
Create a Python project called SkillLab, a complete pipeline for extracting, structuring, and training a model on real resume data.

Objective

    Extract resume data without hallucination and in structured JSON format.
    Use PaddleOCR (CPU) for text and bounding box extraction.
    Generate annotations with Mistral 7B (Ollama, GPU, 8-bit).
    Verify and correct JSON outputs using an auto-correction loop.
    Train Donut on validated JSONs to automate extraction.
    Optimize for RTX 3060 Ti 8GB VRAM (quantization, reduced batch size).
    Implement GPU monitoring and detailed logging to track performance.

📂 Project Structure

SkillLab/
├── extraction/
   ├── ocr_extractor.py    # PaddleOCR CPU
   ├── json_generator.py   # Mistral JSON
   └── auto_correction.py  # Correction loop
├── training/
   ├── dataset_builder.py  # Donut dataset formatting
   └── train_donut.py      # Fine-tuning
├── utils/
   ├── gpu_monitor.py      # Monitoring
   └── logger.py           # Logging
├── data/
   ├── input/              # Real resume PDFs
   └── output/             # Annotated images + JSONs
├── models/
   └── donut_finetuned/    # Trained Donut model
├── logs/
   └── skillbase_donutforge.log
├── setup.py
└── requirements.txt

📌 Processing Pipeline

1️⃣ Extract text and bounding boxes with PaddleOCR (CPU)

    Convert PDFs into high-resolution images (DPI 300).
    Extract text and word coordinates (bbox).

2️⃣ Generate initial JSON with Mistral 7B (Ollama, GPU, 8-bit)

    Transform raw OCR text into a structured JSON following a strict format.
    Use a detailed prompt to ensure clean extraction.

3️⃣ Auto-correct JSONs in a loop

    Check if at least 90% of the extracted text is represented in the JSON.
    If coverage is insufficient, rerun Mistral for correction.
    Prevent hallucination → Missing fields should be null.
    Limit the correction iterations to 3.

4️⃣ Verify and validate annotations

    Compare OCR-extracted words with JSON fields to ensure consistency.
    Store validated JSONs and annotated images for Donut.

5️⃣ Train Donut on the 1,000 validated JSONs

    Use a pre-trained model (donut-base) and fine-tune only the upper layers.
    Adjust batch size and learning rate to optimize training for 8GB VRAM.

6️⃣ Monitor GPU and log performance

    Track GPU usage in real time and display VRAM consumption.
    Log every step in the pipeline (OCR, JSON generation, correction, fine-tuning).

📊 Expected JSON Output

    Each resume must be structured as a JSON with the following strict format:
        Name: str
        Email: str
        Phone: str
        Current Position: str
        Skills: list[str]
        Experience: list[dict] (e.g., {"company": "Google", "title": "Developer", "years": "5 years"})

📦 Technical Constraints

    No mock data → The pipeline must work with real resumes.
    No hallucination → No fabricated data; missing fields must be null.
    Optimized for RTX 3060 Ti 8GB VRAM → Uses Mistral in 8-bit and reduced batch size.
    Local and open-source project → No reliance on external APIs.

🎯 Summary

    SkillLab is a self-contained pipeline for generating annotated JSONs and training Donut.
    PaddleOCR extracts raw data (CPU), Mistral 7B generates and corrects JSONs (GPU).
    Validated JSONs are used to fine-tune Donut for automated resume extraction.
    The project is optimized to run on an RTX 3060 Ti with 8GB VRAM.


Need a Human Review System
**Confidence scoring**: Each extraction receives 0-100 confidence score
- **Failure detection**: Auto-flag documents with:
- <75% extraction confidence
- Inconsistent/missing critical fields
- OCR quality issues
JSON schema validation failures
**Review interface**: Web dashboard at http://localhost:8501 (run with `python -m skilllab.review.app`)
**Batch processing**: Review flagged documents in batches
**Correction feedback loop**: Human corrections improve future extractions

### Integration Approach

1. **Shared Data Pipeline**: 
   - The monitoring system and review interface should share the same data storage
   - Any document flagged in monitoring would automatically appear in the review queue
   - Correction statuses would be visible in both systems

2. **Real-time Flagging**:
   - As the monitor detects issues matching your criteria (<75% confidence, missing fields, etc.), it would tag those documents in the shared database
   - The monitor would display a summary of flagged items (e.g., "15 documents flagged for review")
   - A direct link from the monitor to the review interface would be provided

3. **Implementation Components**:

```
SkillLab/
├── cli.py                         # CLI command interface
├── main.py                        # Main pipeline orchestration
├── setup.py                       # Package setup script
├── requirements.txt               # Package dependencies
├── __init__.py                    # Package initialization
│
├── extraction/                    # OCR and JSON extraction modules
│   ├── __init__.py
│   ├── ocr_extractor.py           # PaddleOCR implementation
│   ├── json_generator.py          # Mistral JSON generation
│   └── auto_correction.py         # JSON validation and correction
│
├── training/                      # Donut model training modules
│   ├── __init__.py
│   ├── dataset_builder.py         # Dataset preparation for Donut
│   └── train_donut.py             # Donut model fine-tuning
│
├── utils/                         # Utility modules
│   ├── __init__.py
│   ├── logger.py                  # Centralized logging
│   └── gpu_monitor.py             # GPU usage monitoring
│
├── monitor/                       # Monitoring system
│   ├── __init__.py
│   ├── dashboard.py               # CLI monitoring dashboard
│   ├── metrics.py                 # Metrics collection and tracking
│   └── integration.py             # Integration with main pipeline
│
├── data/                          # Data directories
│   ├── input/                     # Input resume PDFs
│   └── output/                    # Processing outputs
│       ├── images/                # Extracted resume images
│       ├── ocr_results/           # OCR extraction results
│       ├── json_results/          # Generated JSONs
│       ├── validated_json/        # Validated JSONs
│       └── donut_dataset/         # Prepared dataset for Donut
│           ├── train/             # Training dataset
│           └── validation/        # Validation dataset
│
├── models/                        # Model storage
│   └── donut_finetuned/           # Fine-tuned Donut model
│
├── logs/                          # Log files
│   └── skillbase_donutforge.log   # Main log file
│
├── venv/                          # Virtual environment
│   ├── bin/                       # Scripts and executables
│   ├── lib/                       # Python libraries
│   └── pyvenv.cfg                 # Environment configuration
│
└── .gitignore                     # Git ignore file
```

4. **CLI Command**:
   - Add a new command to the CLI:
   ```
   skilllab monitor  # Start the monitoring dashboard
   skilllab review   # Start the web review interface
   ```

5. **Monitoring-to-Review Flow**:
   - When the monitor detects issues, it would show:
   ```
   FLAGGED FOR REVIEW: 15 documents
   Run `skilllab review` in another terminal to review flagged documents
   ```

6. **Technical Implementation**:
   - For the monitor: Use `blessed` or `rich` library for the CLI interface
   - For the review interface: Use Streamlit for a quick web dashboard
   - For data storage: Use SQLite for simplicity or MongoDB for more complex needs
   - For metrics: Create a central event bus that both systems subscribe to

### Visual Integration


```
SkillLab Monitor - Running for 00:15:32

RESOURCES:
GPU: [███████████████████▒] 87%  | VRAM: [████████████▒▒▒▒▒] 70% (5.6/8.0 GB)
CPU: [██████▒▒▒▒▒▒▒▒▒▒▒▒▒▒] 32%  | RAM:  [█████████▒▒▒▒▒▒▒▒] 45% (7.2/16.0 GB)

PIPELINE STAGES:
OCR:            [██████████████████████████████] 100% (23/23)
JSON:           [██████▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒] 23% (23/100) ← ACTIVE
Auto-Correction: [▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒] 0% (0/100)
Dataset:         [▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒] Waiting
Training:        [▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒] Waiting

CURRENT ACTIVITY: Mistral generating JSON for resume_0023.pdf (5s elapsed)

REVIEW QUEUE:
Documents flagged: [████████▒▒] 15/23 (65%)
Review status:     [██████▒▒▒▒] 9/15 (60%) 
Top issues:
  - Missing contact info:  5 docs
  - Low OCR confidence:    4 docs
  - Schema validation:     3 docs
  - Multiple corrections:  3 docs
```

This allows the operator to see at a glance how many documents need human review and why, while continuing to monitor the automated process.


Need an install.sh to setup the environment, install donut, paddleocr, mystral, ollama, requirements, cli.

UPGRADES:
The human review system would then be a separate but connected web interface that pulls from the same database, showing the flagged documents with interfaces for correction. As corrections are made, the monitoring system would update its statistics and potentially use these corrections to improve future processing.



