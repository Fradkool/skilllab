"""
Extraction API for SkillLab
Provides high-level functions for OCR and JSON extraction
"""

import os
import glob
import time
from typing import Dict, List, Any, Optional, Union, Tuple

from config import get_config, AppConfig
from pipeline import get_executor, PipelineContext
from database import get_metrics_repository
from extraction.ocr_extractor import OCRExtractor
from extraction.json_generator import JSONGenerator
from extraction.auto_correction import JSONAutoCorrector

def extract_text_from_pdf(
    pdf_path: str,
    output_dir: Optional[str] = None,
    use_gpu: Optional[bool] = None,
    language: Optional[str] = None
) -> Dict[str, Any]:
    """
    Extract text from a PDF using OCR
    
    Args:
        pdf_path: Path to PDF file
        output_dir: Output directory (None to use configured directory)
        use_gpu: Whether to use GPU for OCR (None to use configured setting)
        language: OCR language (None to use configured language)
        
    Returns:
        Dictionary with extraction results
        
    Raises:
        FileNotFoundError: If PDF file doesn't exist
    """
    # Validate input
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    # Get configuration
    config = get_config()
    output_dir = output_dir or config.paths.output_dir
    use_gpu = use_gpu if use_gpu is not None else config.gpu.use_gpu_ocr
    language = language or config.ocr.language
    
    # Initialize OCR extractor
    extractor = OCRExtractor(
        use_gpu=use_gpu,
        lang=language,
        output_dir=output_dir
    )
    
    # Process PDF
    result = extractor.process_resume(pdf_path)
    
    # Update metrics if document ID is provided
    file_name = os.path.basename(pdf_path)
    doc_id = os.path.splitext(file_name)[0]
    metrics_repo = get_metrics_repository()
    
    if metrics_repo:
        metrics_repo.register_document(doc_id, file_name)
        
        # Calculate OCR confidence
        ocr_result = result.get("result", {})
        confidences = []
        for page_result in ocr_result.get("page_results", []):
            for element in page_result.get("text_elements", []):
                if "confidence" in element:
                    confidences.append(element["confidence"])
        
        if confidences:
            ocr_confidence = sum(confidences) / len(confidences) * 100
            metrics_repo.update_document_confidence(doc_id, ocr_confidence=ocr_confidence)
            metrics_repo.update_document_status(doc_id, "ocr_complete")
    
    return result

def batch_extract_text(
    input_dir: str,
    output_dir: Optional[str] = None,
    limit: Optional[int] = None,
    use_gpu: Optional[bool] = None,
    language: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Extract text from multiple PDFs using OCR
    
    Args:
        input_dir: Directory containing PDF files
        output_dir: Output directory (None to use configured directory)
        limit: Maximum number of files to process
        use_gpu: Whether to use GPU for OCR
        language: OCR language
        
    Returns:
        List of extraction results
        
    Raises:
        FileNotFoundError: If input directory doesn't exist
    """
    # Run OCR extraction pipeline step
    config = get_config()
    
    # Validate input directory
    if not os.path.exists(input_dir):
        raise FileNotFoundError(f"Input directory not found: {input_dir}")
    
    # Create executor and context
    executor = get_executor()
    context = PipelineContext()
    
    # Override configuration
    if output_dir or limit is not None or use_gpu is not None or language:
        custom_config = config.copy()
        
        if output_dir:
            custom_config.paths.output_dir = output_dir
        
        if limit is not None:
            custom_config.pipeline.limit = limit
        
        if use_gpu is not None:
            custom_config.gpu.use_gpu_ocr = use_gpu
        
        if language:
            custom_config.ocr.language = language
        
        context.config = custom_config
    else:
        context.config = config
    
    # Configure context for input directory
    context.config.paths.input_dir = input_dir
    
    # Run extraction step
    executor.run_pipeline(
        name="extract",
        context=context
    )
    
    # Get results
    ocr_results = context.get_result("ocr")
    
    if not ocr_results or "results" not in ocr_results:
        return []
    
    return ocr_results["results"]

def generate_json_from_text(
    ocr_result: Dict[str, Any],
    output_dir: Optional[str] = None,
    ollama_url: Optional[str] = None,
    model_name: Optional[str] = None,
    temperature: Optional[float] = None
) -> Dict[str, Any]:
    """
    Generate structured JSON from OCR text
    
    Args:
        ocr_result: OCR extraction result
        output_dir: Output directory (None to use configured directory)
        ollama_url: URL for Ollama API (None to use configured URL)
        model_name: Model name for JSON generation (None to use configured model)
        temperature: Temperature for generation (None to use configured temperature)
        
    Returns:
        Dictionary with JSON generation results
    """
    # Get configuration
    config = get_config()
    output_dir = output_dir or os.path.join(config.paths.output_dir, "json_results")
    ollama_url = ollama_url or config.json_generation.ollama_url
    model_name = model_name or config.json_generation.model_name
    temperature = temperature if temperature is not None else config.json_generation.temperature
    
    # Initialize JSON generator
    generator = JSONGenerator(
        ollama_url=ollama_url,
        model_name=model_name,
        output_dir=output_dir
    )
    
    # Process OCR result
    result = generator.process_ocr_result(ocr_result)
    
    # Update metrics
    document_id = ocr_result.get("file_id", "")
    metrics_repo = get_metrics_repository()
    
    if metrics_repo and document_id:
        # Calculate JSON confidence (simplified)
        json_data = result.get("json_data", {})
        fields_missing = sum(1 for field in ["Name", "Email", "Phone"] if not json_data.get(field))
        skills_count = len(json_data.get("Skills", []))
        experience_count = len(json_data.get("Experience", []))
        
        # Simple heuristic: 100% - (missing critical fields × 20%) + (skills+experience boost)
        json_confidence = 100 - (fields_missing * 20)
        json_confidence += min(20, skills_count * 2 + experience_count * 5)
        json_confidence = max(0, min(100, json_confidence))
        
        metrics_repo.update_document_confidence(document_id, json_confidence=json_confidence)
        metrics_repo.update_document_status(document_id, "json_complete")
        
        # Flag for review if critical fields are missing
        if fields_missing > 0:
            missing_field_names = [field for field in ["Name", "Email", "Phone"] if not json_data.get(field)]
            metrics_repo.flag_for_review(
                document_id,
                "missing_contact",
                f"Missing critical fields: {', '.join(missing_field_names)}"
            )
    
    return result

def batch_generate_json(
    ocr_results: List[Dict[str, Any]],
    output_dir: Optional[str] = None,
    ollama_url: Optional[str] = None,
    model_name: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Generate structured JSON from multiple OCR results
    
    Args:
        ocr_results: List of OCR extraction results
        output_dir: Output directory (None to use configured directory)
        ollama_url: URL for Ollama API (None to use configured URL)
        model_name: Model name for JSON generation (None to use configured model)
        
    Returns:
        List of JSON generation results
    """
    # Get configuration
    config = get_config()
    output_dir = output_dir or os.path.join(config.paths.output_dir, "json_results")
    ollama_url = ollama_url or config.json_generation.ollama_url
    model_name = model_name or config.json_generation.model_name
    
    # Create executor and context
    executor = get_executor()
    context = PipelineContext()
    
    # Configure context
    context.config = config
    
    if output_dir:
        context.config.paths.output_dir = output_dir
    
    if ollama_url:
        context.config.json_generation.ollama_url = ollama_url
    
    if model_name:
        context.config.json_generation.model_name = model_name
    
    # Store OCR results in context
    context.set_result("ocr", {"results": ocr_results, "count": len(ocr_results)})
    
    # Run JSON generation step
    executor.run_pipeline(
        name="structure",
        start_step="json",
        end_step="json",
        context=context
    )
    
    # Get results
    json_results = context.get_result("json")
    
    if not json_results or "results" not in json_results:
        return []
    
    return json_results["results"]

def validate_and_correct_json(
    ocr_result: Dict[str, Any],
    json_result: Dict[str, Any],
    output_dir: Optional[str] = None,
    min_coverage_threshold: Optional[float] = None,
    max_correction_attempts: Optional[int] = None
) -> Dict[str, Any]:
    """
    Validate and correct JSON structure
    
    Args:
        ocr_result: OCR extraction result
        json_result: JSON generation result
        output_dir: Output directory (None to use configured directory)
        min_coverage_threshold: Minimum coverage threshold (None to use configured threshold)
        max_correction_attempts: Maximum correction attempts (None to use configured value)
        
    Returns:
        Dictionary with validation results
    """
    # Get configuration
    config = get_config()
    output_dir = output_dir or os.path.join(config.paths.output_dir, "validated_json")
    min_coverage_threshold = min_coverage_threshold if min_coverage_threshold is not None else config.correction.min_coverage_threshold
    max_correction_attempts = max_correction_attempts if max_correction_attempts is not None else config.correction.max_correction_attempts
    
    # Initialize JSON generator for corrections
    generator = JSONGenerator(
        ollama_url=config.json_generation.ollama_url,
        model_name=config.json_generation.model_name,
        output_dir=os.path.join(config.paths.output_dir, "json_results")
    )
    
    # Initialize auto-corrector
    corrector = JSONAutoCorrector(
        json_generator=generator,
        output_dir=output_dir,
        min_coverage_threshold=min_coverage_threshold,
        max_correction_attempts=max_correction_attempts
    )
    
    # Process resume
    result = corrector.process_resume(ocr_result, json_result)
    
    # Update metrics
    document_id = ocr_result.get("file_id", "")
    metrics_repo = get_metrics_repository()
    
    if metrics_repo and document_id:
        # Increment correction count
        metrics_repo.increment_correction_count(document_id)
        
        # Update status based on validation result
        is_valid = result.get("is_valid", False)
        
        if is_valid:
            metrics_repo.update_document_status(document_id, "validated")
        else:
            # Flag for review if validation failed
            metrics_repo.flag_for_review(
                document_id,
                "validation_failure",
                f"Validation failed with coverage {result.get('coverage', 0)*100:.1f}%"
            )
        
        # Flag for review if too many correction attempts
        if result.get("correction_attempts", 0) >= max_correction_attempts:
            metrics_repo.flag_for_review(
                document_id,
                "multiple_corrections",
                f"Required {result.get('correction_attempts', 0)} correction attempts"
            )
    
    return result

def run_full_extraction_pipeline(
    input_dir: str,
    output_dir: Optional[str] = None,
    limit: Optional[int] = None
) -> Dict[str, Any]:
    """
    Run the full extraction pipeline (OCR, JSON generation, and correction)
    
    Args:
        input_dir: Directory containing PDF files
        output_dir: Output directory (None to use configured directory)
        limit: Maximum number of files to process
        
    Returns:
        Dictionary with pipeline results
        
    Raises:
        FileNotFoundError: If input directory doesn't exist
    """
    # Validate input directory
    if not os.path.exists(input_dir):
        raise FileNotFoundError(f"Input directory not found: {input_dir}")
    
    # Get configuration
    config = get_config()
    output_dir = output_dir or config.paths.output_dir
    
    # Create executor and context
    executor = get_executor()
    context = PipelineContext()
    
    # Configure context
    context.config = config
    context.config.paths.input_dir = input_dir
    
    if output_dir:
        context.config.paths.output_dir = output_dir
    
    if limit is not None:
        context.config.pipeline.limit = limit
    
    # Run pipeline
    executor.run_pipeline(
        name="full",
        start_step="ocr",
        end_step="correction",
        context=context
    )
    
    # Collect results
    ocr_results = context.get_result("ocr")
    json_results = context.get_result("json")
    correction_results = context.get_result("correction")
    
    return {
        "ocr": ocr_results,
        "json": json_results,
        "correction": correction_results,
        "elapsed_time": context.elapsed_time(),
        "documents_processed": context.documents_processed,
        "errors": context.errors
    }