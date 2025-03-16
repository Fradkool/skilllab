# CLAUDE.md - Agent Guidelines for SkillLab Project

## Build Commands
- Install dependencies: `pip install -e .`
- Run full pipeline: `python -m skilllab.main`
- Run pipeline with human review: `python -m skilllab.main --human-review`
- GPU monitoring: `python -m skilllab.utils.gpu_monitor`

## Test Commands
- Run all tests: `pytest tests/`
- Run specific test: `pytest tests/path/to/test.py::test_function_name`
- Run with coverage: `pytest --cov=skilllab tests/`

## Code Style Guidelines
- **Formatting**: Follow PEP 8 standards
- **Imports**: Group imports: standard lib, third-party, local modules
- **Types**: Use type hints for all function parameters and return values
- **Naming**:
  - Classes: PascalCase
  - Functions/variables: snake_case
  - Constants: UPPER_SNAKE_CASE
- **Error handling**: Use try/except with specific exceptions
- **Documentation**: Docstrings for all modules, classes, and functions (Google style)
- **Logging**: Use utils.logger instead of print statements

## Project Structure
- `extraction/`: OCR and JSON generation modules
- `training/`: Dataset preparation and model training
- `utils/`: Monitoring and logging utilities
- `data/`: Input resumes and processed outputs
- `models/`: Fine-tuned Donut model
- `review/`: Human review interface and tools

## Technical Constraints
- Optimize for RTX 3060 Ti (8GB VRAM)
- Keep processing 100% local (no external APIs)
- Prevent hallucinations in extracted data

## Human Review System
- **Confidence scoring**: Each extraction receives 0-100 confidence score
- **Failure detection**: Auto-flag documents with:
  - <75% extraction confidence
  - Inconsistent/missing critical fields
  - OCR quality issues
  - JSON schema validation failures
- **Review interface**: Web dashboard at http://localhost:8501 (run with `python -m skilllab.review.app`)
- **Batch processing**: Review flagged documents in batches
- **Correction feedback loop**: Human corrections improve future extractions

## Feasibility Issues & Solutions

### Hardware Constraints
- **Issue**: Fine-tuning Donut may exceed 8GB VRAM
- **Solution**: Implement gradient accumulation, freeze early layers

### OCR Reliability
- **Issue**: PaddleOCR struggles with complex resume layouts
- **Solution**: Add PDF preprocessing, use hybrid extraction with regex

### JSON Generation
- **Issue**: Inconsistent structuring from unformatted OCR text
- **Solution**: Field-specific parsers, multi-step extraction

### Training Data
- **Issue**: 1,000 resumes may be insufficient for robust model
- **Solution**: Transfer learning, data augmentation, phased approach

### Implementation Approach
- Start small (50-100 resumes), validate pipeline components
- Implement tiered extraction with fallbacks
- Create objective quality metrics
- Build continuous improvement loop with human feedback