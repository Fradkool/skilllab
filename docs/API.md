# SkillLab API Reference

This document provides a comprehensive reference for the SkillLab API, covering all major modules and functions.

## API Overview

SkillLab's API is organized into four main modules:

1. **Extraction API**: Functions for OCR extraction, JSON generation, and validation
2. **Training API**: Functions for dataset creation and model training
3. **Review API**: Functions for document review and feedback
4. **Monitoring API**: Functions for system monitoring and metrics

All API functions follow consistent patterns for error handling, input validation, and return types.

## 1. Extraction API

The Extraction API provides functions for processing resume documents.

### Core Functions

#### `extract_text_from_pdf(pdf_path: str, output_dir: Optional[str] = None) -> Dict[str, Any]`

Extracts text from a PDF document using OCR.

**Parameters:**
- `pdf_path`: Path to the PDF file
- `output_dir`: Optional directory to save results

**Returns:**
- Dictionary containing OCR results, including:
  - `combined_text`: Extracted text
  - `confidence`: Overall confidence score
  - `page_results`: Per-page extraction details

**Example:**
```python
from api.extraction import extract_text_from_pdf

result = extract_text_from_pdf("resume.pdf", "output/ocr_results")
print(f"Extracted {len(result['combined_text'])} characters with {result['confidence']:.2f}% confidence")
```

#### `batch_extract_text(input_dir: str, output_dir: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]`

Extracts text from multiple PDFs in a directory.

**Parameters:**
- `input_dir`: Directory containing PDF files
- `output_dir`: Optional directory to save results
- `limit`: Maximum number of files to process

**Returns:**
- List of dictionaries containing OCR results for each PDF

#### `generate_json_from_text(text: str, template: Optional[str] = None) -> Dict[str, Any]`

Generates structured JSON from extracted text using LLM.

**Parameters:**
- `text`: Extracted text from a document
- `template`: Optional prompt template

**Returns:**
- Structured JSON with resume information

**Example:**
```python
from api.extraction import extract_text_from_pdf, generate_json_from_text

ocr_result = extract_text_from_pdf("resume.pdf")
json_data = generate_json_from_text(ocr_result["combined_text"])
print(f"Extracted {len(json_data['Skills'])} skills")
```

#### `batch_generate_json(ocr_results: List[Dict[str, Any]], output_dir: Optional[str] = None) -> List[Dict[str, Any]]`

Generates JSON for multiple OCR results.

**Parameters:**
- `ocr_results`: List of OCR result dictionaries
- `output_dir`: Optional directory to save results

**Returns:**
- List of JSON data for each document

#### `validate_and_correct_json(json_data: Dict[str, Any], schema_path: Optional[str] = None) -> Tuple[Dict[str, Any], bool, Dict[str, Any]]`

Validates and corrects generated JSON against a schema.

**Parameters:**
- `json_data`: Generated JSON data
- `schema_path`: Optional path to schema file

**Returns:**
- Tuple containing:
  - Corrected JSON data
  - Validation success flag
  - Validation details

#### `run_full_extraction_pipeline(input_dir: str, output_dir: Optional[str] = None, limit: Optional[int] = None) -> Dict[str, Any]`

Runs the complete extraction pipeline on a directory of PDFs.

**Parameters:**
- `input_dir`: Directory containing PDF files
- `output_dir`: Optional directory to save results
- `limit`: Maximum number of files to process

**Returns:**
- Dictionary with pipeline results summary

## 2. Training API

The Training API provides functions for dataset creation and model training.

### Core Functions

#### `build_training_dataset(json_dir: str, image_dir: str, output_dir: str, split_ratio: float = 0.8) -> Dict[str, Any]`

Builds a dataset for training the Donut model.

**Parameters:**
- `json_dir`: Directory containing JSON files
- `image_dir`: Directory containing document images
- `output_dir`: Directory to save the dataset
- `split_ratio`: Train/validation split ratio

**Returns:**
- Dataset statistics including sample counts

#### `train_donut_model(dataset_dir: str, output_dir: str, epochs: int = 5, batch_size: int = 4) -> Dict[str, Any]`

Trains a Donut model on the prepared dataset.

**Parameters:**
- `dataset_dir`: Directory containing the dataset
- `output_dir`: Directory to save the trained model
- `epochs`: Number of training epochs
- `batch_size`: Batch size for training

**Returns:**
- Training results and metrics

#### `evaluate_model(model_dir: str, test_dataset_dir: str) -> Dict[str, Any]`

Evaluates a trained model on a test dataset.

**Parameters:**
- `model_dir`: Directory containing the trained model
- `test_dataset_dir`: Directory containing test dataset

**Returns:**
- Evaluation metrics

#### `get_available_models() -> List[Dict[str, Any]]`

Gets a list of available trained models.

**Returns:**
- List of model metadata dictionaries

#### `export_model(model_name: str, export_dir: str) -> str`

Exports a trained model to a specified directory.

**Parameters:**
- `model_name`: Name of the model to export
- `export_dir`: Directory to export the model to

**Returns:**
- Path to the exported model

## 3. Review API

The Review API provides functions for document review and feedback.

### Core Functions

#### `get_review_queue(issue_filter: str = 'All', limit: int = 100) -> List[Dict[str, Any]]`

Gets documents requiring review.

**Parameters:**
- `issue_filter`: Filter by issue type ('All' for no filter)
- `limit`: Maximum number of documents to return

**Returns:**
- List of document metadata dictionaries

#### `get_document_details(document_id: str) -> Dict[str, Any]`

Gets detailed information for a specific document.

**Parameters:**
- `document_id`: Document identifier

**Returns:**
- Document details including OCR results, JSON data, and issues

#### `save_review_feedback(document_id: str, status: str, **kwargs) -> bool`

Saves review feedback for a document.

**Parameters:**
- `document_id`: Document identifier
- `status`: Review status ('approved', 'rejected', etc.)
- `**kwargs`: Additional feedback data

**Returns:**
- Success flag

#### `approve_document(document_id: str, changes_made: bool = False) -> bool`

Approves a document after review.

**Parameters:**
- `document_id`: Document identifier
- `changes_made`: Flag indicating if changes were made

**Returns:**
- Success flag

#### `reject_document(document_id: str, reason: str = '') -> bool`

Rejects a document after review.

**Parameters:**
- `document_id`: Document identifier
- `reason`: Reason for rejection

**Returns:**
- Success flag

#### `get_dashboard_stats() -> Dict[str, Any]`

Gets statistics for the review dashboard.

**Returns:**
- Review statistics including document counts and issues

## 4. Monitoring API

The Monitoring API provides functions for system monitoring and metrics.

### Core Functions

#### `initialize_monitoring_system(enabled: bool = True) -> bool`

Initializes the monitoring system.

**Parameters:**
- `enabled`: Whether to enable monitoring

**Returns:**
- Success flag

#### `get_system_resources() -> Dict[str, Any]`

Gets current system resource usage.

**Returns:**
- Dictionary with CPU, memory, disk, and GPU usage

#### `get_pipeline_progress() -> Dict[str, Any]`

Gets current pipeline progress information.

**Returns:**
- Progress information for each pipeline stage

#### `get_performance_metrics(time_range: str = "day", metric_type: Optional[str] = None) -> Dict[str, Any]`

Gets performance metrics over time.

**Parameters:**
- `time_range`: Time range ('hour', 'day', 'week', 'month')
- `metric_type`: Optional metric type filter

**Returns:**
- Metrics data for the specified time range

#### `get_recent_activity(limit: int = 20) -> List[Dict[str, Any]]`

Gets recent pipeline activity.

**Parameters:**
- `limit`: Maximum number of records to return

**Returns:**
- List of activity records

#### `get_document_processing_stats() -> Dict[str, Any]`

Gets document processing statistics.

**Returns:**
- Statistics about document processing

#### `record_custom_metric(metric_type: str, metric_name: str, metric_value: float, details: Optional[Dict[str, Any]] = None) -> bool`

Records a custom metric.

**Parameters:**
- `metric_type`: Metric type
- `metric_name`: Metric name
- `metric_value`: Numeric value
- `details`: Optional additional details

**Returns:**
- Success flag

## 5. Health API

The Health API provides functions for checking service health.

### Core Functions

#### `get_health_api() -> HealthAPI`

Gets the health API instance.

**Returns:**
- HealthAPI instance

#### `check_core_components() -> Dict[str, Any]`

Checks health of core components.

**Returns:**
- Health status for each component

#### `check_all_components() -> Dict[str, Any]`

Checks health of all components including services.

**Returns:**
- Comprehensive health status report

## Error Handling

All API functions use consistent error handling:

1. **Expected Errors**: Returned as part of the result object with error details
2. **Unexpected Errors**: Logged and re-raised with contextual information
3. **Resource Errors**: Special handling for resource unavailability

Error details include:
- Error type
- Error message
- Error location (file and line number)
- Timestamp

## Usage Examples

### Complete Pipeline Example

```python
from api.extraction import run_full_extraction_pipeline
from api.training import build_training_dataset, train_donut_model

# Run extraction pipeline
results = run_full_extraction_pipeline(
    input_dir="data/input",
    output_dir="data/output",
    limit=100
)

# Build training dataset
dataset_stats = build_training_dataset(
    json_dir="data/output/validated_json",
    image_dir="data/output/images",
    output_dir="data/output/donut_dataset"
)

# Train model
training_results = train_donut_model(
    dataset_dir="data/output/donut_dataset",
    output_dir="models/donut_finetuned",
    epochs=10,
    batch_size=4
)

print(f"Processed {results['document_count']} documents")
print(f"Created dataset with {dataset_stats['train_samples']} training samples")
print(f"Training completed with loss: {training_results['final_loss']}")
```

### Monitoring Example

```python
from api.monitoring import initialize_monitoring_system, get_system_resources, get_pipeline_progress

# Initialize monitoring
initialize_monitoring_system()

# Get resource usage
resources = get_system_resources()
print(f"CPU: {resources['cpu']['percent']}%, RAM: {resources['memory']['used_gb']:.2f}GB")

# Get pipeline progress
progress = get_pipeline_progress()
for step, data in progress.items():
    print(f"{step}: {data['completed']}/{data['total']} ({data['completed']/data['total']*100:.1f}%)")
```

## Database Integration

The API interacts with the database layer through repositories:

```python
from database import get_metrics_repository, get_review_repository

# Get metrics repository
metrics_repo = get_metrics_repository()

# Record a metric
metrics_repo.record_metric(
    metric_type="performance",
    metric_name="extraction_time",
    metric_value=1.25,
    details={"document_id": "doc123"}
)

# Get review repository
review_repo = get_review_repository()

# Update review status
review_repo.update_review_status("doc123", "approved")
```

## API Evolution

The API follows semantic versioning principles. Breaking changes will only be introduced in major version increments.

To ensure backward compatibility:
- Deprecated functions are marked with warnings
- New parameters have sensible defaults
- Return types remain consistent

## Security Considerations

The API implements these security practices:

- Input validation for all external inputs
- Proper handling of file paths to prevent path traversal
- No execution of user-provided code
- Sanitization of data from external sources

## Performance Considerations

For optimal performance:

- Use batch functions for processing multiple items
- Reuse API instances when making multiple calls
- Process large datasets incrementally
- Use the monitoring API to track resource usage