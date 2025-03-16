"""
Main script for SkillLab
Orchestrates the entire pipeline from extraction to training
"""

import os
import sys
import json
import time
import argparse
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

# Import from refactored modules
from config import get_config, AppConfig
from pipeline import get_executor, PipelineContext
from database import get_metrics_repository

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="SkillLab - Resume Data Extraction and Model Training")
    
    # Input data
    parser.add_argument("--input_dir", type=str, default=None,
                        help="Directory containing input resume PDFs")
    parser.add_argument("--limit", type=int, default=None,
                        help="Maximum number of resumes to process (None for all)")
    
    # Output directories
    parser.add_argument("--output_dir", type=str, default=None,
                        help="Directory for output files")
    parser.add_argument("--model_dir", type=str, default=None,
                        help="Directory to save fine-tuned Donut model")
    
    # Pipeline control
    parser.add_argument("--start_step", type=str, choices=["ocr", "json", "correction", "dataset", "training"], default=None,
                        help="Step to start the pipeline from")
    parser.add_argument("--end_step", type=str, choices=["ocr", "json", "correction", "dataset", "training"], default=None,
                        help="Step to end the pipeline at")
    
    # GPU usage
    parser.add_argument("--gpu_monitor", action="store_true",
                        help="Enable GPU monitoring")
    parser.add_argument("--use_gpu_ocr", action="store_true",
                        help="Use GPU for OCR (not recommended for pipeline)")
    
    # OCR service options
    parser.add_argument("--use_ocr_service", action="store_true",
                        help="Use containerized PaddleOCR service instead of direct PaddleOCR")
    parser.add_argument("--ocr_service_url", type=str, default=None,
                        help="URL for PaddleOCR service API (e.g., http://localhost:8080/v1/ocr/process_pdf)")
    
    # Training parameters
    parser.add_argument("--epochs", type=int, default=None,
                        help="Number of epochs for Donut training")
    parser.add_argument("--batch_size", type=int, default=None,
                        help="Batch size for training (adjust based on GPU memory)")
    parser.add_argument("--pretrained_model", type=str, default=None,
                        help="Pre-trained Donut model to use")
    
    # Mistral parameters
    parser.add_argument("--ollama_url", type=str, default=None,
                        help="URL for Ollama API")
    parser.add_argument("--mistral_model", type=str, default=None,
                        help="Mistral model name in Ollama")
    
    # Monitoring
    parser.add_argument("--enable_monitoring", action="store_true",
                        help="Enable metrics collection and monitoring integration")
    parser.add_argument("--metrics_db", type=str, default=None,
                        help="Path to metrics database")
    
    # Human review
    parser.add_argument("--human_review", action="store_true",
                        help="Enable human review for flagged documents")
    parser.add_argument("--review_db", type=str, default=None,
                        help="Path to review database")
    
    # Configuration file
    parser.add_argument("--config", type=str, default=None,
                        help="Path to configuration file")
    
    return parser.parse_args()

def override_config_from_args(config: AppConfig, args) -> AppConfig:
    """
    Override configuration with command line arguments
    
    Args:
        config: Configuration object
        args: Command line arguments
        
    Returns:
        Updated configuration object
    """
    # Input/output paths
    if args.input_dir:
        config.paths.input_dir = args.input_dir
    
    if args.output_dir:
        config.paths.output_dir = args.output_dir
    
    if args.model_dir:
        config.paths.model_dir = args.model_dir
    
    # Pipeline control
    if args.start_step:
        config.pipeline.start_step = args.start_step
    
    if args.end_step:
        config.pipeline.end_step = args.end_step
    
    if args.limit is not None:
        config.pipeline.limit = args.limit
    
    # GPU settings
    if args.gpu_monitor:
        config.gpu.monitor = True
    
    if args.use_gpu_ocr:
        config.gpu.use_gpu_ocr = True
        
    # OCR service settings
    if args.use_ocr_service:
        config.ocr.use_service = True
        
    if args.ocr_service_url:
        config.ocr.service_url = args.ocr_service_url
        # If service URL is provided, enable service by default
        if not args.use_ocr_service:
            config.ocr.use_service = True
    
    # Training parameters
    if args.epochs is not None:
        config.training.epochs = args.epochs
    
    if args.batch_size is not None:
        config.training.batch_size = args.batch_size
    
    if args.pretrained_model:
        config.training.pretrained_model = args.pretrained_model
    
    # Mistral parameters
    if args.ollama_url:
        config.json_generation.ollama_url = args.ollama_url
    
    if args.mistral_model:
        config.json_generation.model_name = args.mistral_model
    
    # Monitoring
    if args.enable_monitoring:
        config.monitoring.enabled = True
    
    if args.metrics_db:
        config.monitoring.metrics_db = args.metrics_db
    
    # Human review
    if args.human_review:
        config.review.enabled = True
    
    if args.review_db:
        config.review.db_path = args.review_db
    
    return config

def setup_logging(config: AppConfig):
    """
    Setup logging based on configuration
    
    Args:
        config: Configuration object
    """
    import logging.handlers
    
    # Create logs directory if it doesn't exist
    os.makedirs(config.paths.logs_dir, exist_ok=True)
    
    # Get root logger
    root_logger = logging.getLogger()
    
    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Set level
    level = getattr(logging, config.logging.level, logging.INFO)
    root_logger.setLevel(level)
    
    # Add console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # Add file handler
    log_path = config.logging.file
    file_handler = logging.handlers.RotatingFileHandler(
        log_path,
        maxBytes=config.logging.max_size_mb * 1024 * 1024,
        backupCount=config.logging.backup_count
    )
    file_handler.setLevel(level)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    # Log configuration
    logging.info(f"Logging initialized at level {config.logging.level}")
    logging.info(f"Log file: {log_path}")

def setup_output_dirs(config: AppConfig):
    """
    Create output directories
    
    Args:
        config: Configuration object
    """
    # Main directories
    os.makedirs(config.paths.input_dir, exist_ok=True)
    os.makedirs(config.paths.output_dir, exist_ok=True)
    os.makedirs(config.paths.model_dir, exist_ok=True)
    
    # Subdirectories for output
    os.makedirs(os.path.join(config.paths.output_dir, "ocr_results"), exist_ok=True)
    os.makedirs(os.path.join(config.paths.output_dir, "json_results"), exist_ok=True)
    os.makedirs(os.path.join(config.paths.output_dir, "validated_json"), exist_ok=True)
    os.makedirs(os.path.join(config.paths.output_dir, "donut_dataset"), exist_ok=True)
    os.makedirs(os.path.join(config.paths.output_dir, "images"), exist_ok=True)
    
    # Review system directories
    if config.review.enabled:
        review_dir = os.path.dirname(config.review.db_path)
        os.makedirs(review_dir, exist_ok=True)

def run_pipeline(config: AppConfig) -> Dict[str, Any]:
    """
    Run the SkillLab pipeline
    
    Args:
        config: Configuration object
        
    Returns:
        Dictionary with pipeline results
    """
    # Get pipeline executor
    executor = get_executor()
    
    # Create pipeline context
    context = PipelineContext(config=config)
    
    # Run pipeline
    logging.info(f"Starting SkillLab pipeline from {config.pipeline.start_step} to {config.pipeline.end_step}")
    pipeline_start = time.time()
    
    try:
        # Run pipeline
        context = executor.run_pipeline(
            name="full",
            start_step=config.pipeline.start_step,
            end_step=config.pipeline.end_step,
            context=context
        )
        
        # Calculate total time
        pipeline_time = time.time() - pipeline_start
        
        # Build summary
        summary = {
            "pipeline": {
                "start_step": config.pipeline.start_step,
                "end_step": config.pipeline.end_step,
                "total_time": pipeline_time,
                "timestamp": datetime.now().isoformat()
            },
            "steps": {}
        }
        
        # Add step results to summary
        for step_name in ["ocr", "json", "correction", "dataset", "training"]:
            step_result = context.get_result(step_name)
            if step_result:
                if step_name == "ocr":
                    summary["steps"][step_name] = {
                        "time": step_result.get("time", 0),
                        "resumes_processed": step_result.get("count", 0)
                    }
                elif step_name == "json":
                    summary["steps"][step_name] = {
                        "time": step_result.get("time", 0),
                        "jsons_generated": step_result.get("count", 0)
                    }
                elif step_name == "correction":
                    count = step_result.get("count", 0)
                    valid_count = step_result.get("valid_count", 0)
                    summary["steps"][step_name] = {
                        "time": step_result.get("time", 0),
                        "jsons_validated": count,
                        "valid_jsons": valid_count,
                        "validation_rate": valid_count / count if count > 0 else 0
                    }
                elif step_name == "dataset":
                    summary["steps"][step_name] = {
                        "time": step_result.get("time", 0),
                        "train_samples": step_result.get("train_samples", 0),
                        "val_samples": step_result.get("val_samples", 0)
                    }
                elif step_name == "training":
                    summary["steps"][step_name] = {
                        "time": step_result.get("time", 0),
                        "final_loss": step_result.get("eval_metrics", {}).get("eval_loss", "N/A"),
                        "model_path": config.paths.model_dir
                    }
        
        # Add review summary if enabled
        if config.review.enabled:
            metrics_repo = get_metrics_repository()
            if metrics_repo:
                stats = metrics_repo.get_dashboard_stats()
                summary["review"] = {
                    "flagged_documents": stats.get("flagged_documents", 0),
                    "reviewed_documents": stats.get("reviewed_documents", 0),
                    "issues": stats.get("issue_stats", {})
                }
        
        # Save summary
        summary_path = os.path.join(config.paths.logs_dir, f"pipeline_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        logging.info(f"Pipeline completed in {pipeline_time:.2f}s - Summary saved to {summary_path}")
        
        return summary
    except Exception as e:
        pipeline_time = time.time() - pipeline_start
        logging.error(f"Pipeline failed after {pipeline_time:.2f}s: {e}", exc_info=True)
        
        # Build error summary
        error_summary = {
            "pipeline": {
                "start_step": config.pipeline.start_step,
                "end_step": config.pipeline.end_step,
                "total_time": pipeline_time,
                "timestamp": datetime.now().isoformat(),
                "status": "failed",
                "error": str(e)
            },
            "steps": {}
        }
        
        # Save error summary
        error_path = os.path.join(config.paths.logs_dir, f"pipeline_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(error_path, 'w', encoding='utf-8') as f:
            json.dump(error_summary, f, ensure_ascii=False, indent=2)
        
        return error_summary

def main():
    """Main entry point"""
    # Parse arguments
    args = parse_args()
    
    # Load configuration
    if args.config:
        from config.loader import ConfigLoader
        loader = ConfigLoader(args.config)
        config = loader.load()
    else:
        config = get_config()
    
    # Override configuration with command line arguments
    config = override_config_from_args(config, args)
    
    # Setup logging
    setup_logging(config)
    
    # Setup directories
    setup_output_dirs(config)
    
    # Log configuration
    logging.info(f"SkillLab pipeline configuration:")
    logging.info(f"  Input directory: {config.paths.input_dir}")
    logging.info(f"  Output directory: {config.paths.output_dir}")
    logging.info(f"  Model directory: {config.paths.model_dir}")
    logging.info(f"  Pipeline: {config.pipeline.start_step} -> {config.pipeline.end_step}")
    logging.info(f"  GPU monitoring: {'Enabled' if config.gpu.monitor else 'Disabled'}")
    logging.info(f"  Human review: {'Enabled' if config.review.enabled else 'Disabled'}")
    logging.info(f"  Training: {config.training.epochs} epochs, batch size {config.training.batch_size}")
    
    # Log OCR service info if enabled
    if config.ocr.use_service:
        logging.info(f"  OCR Mode: Containerized service at {config.ocr.service_url}")
    else:
        logging.info(f"  OCR Mode: Direct PaddleOCR (GPU: {'Enabled' if config.gpu.use_gpu_ocr else 'Disabled'})")
    
    # Run pipeline
    summary = run_pipeline(config)
    
    # Print final summary
    print("\nPipeline Summary:")
    print(f"  Total time: {summary['pipeline']['total_time']:.2f}s")
    
    for step, data in summary.get("steps", {}).items():
        print(f"  {step.capitalize()} step: {data.get('time', 0):.2f}s")
        
        if step == "ocr":
            print(f"    Resumes processed: {data.get('resumes_processed', 0)}")
        elif step == "json":
            print(f"    JSONs generated: {data.get('jsons_generated', 0)}")
        elif step == "correction":
            print(f"    JSONs validated: {data.get('valid_jsons', 0)}/{data.get('jsons_validated', 0)} "
                  f"({data.get('validation_rate', 0)*100:.1f}%)")
        elif step == "dataset":
            print(f"    Dataset: {data.get('train_samples', 0)} train, {data.get('val_samples', 0)} validation samples")
        elif step == "training":
            print(f"    Final loss: {data.get('final_loss', 'N/A')}")
            print(f"    Model saved to: {data.get('model_path', 'N/A')}")
    
    # Print review summary if enabled
    if "review" in summary:
        print("\nReview System Summary:")
        print(f"  Documents flagged: {summary['review'].get('flagged_documents', 0)}")
        
        if summary['review'].get('issues'):
            print("  Issue breakdown:")
            for issue, count in summary['review'].get('issues', {}).items():
                print(f"    {issue}: {count}")
        
        print("\nTo start the review interface:")
        print("  skilllab review")

if __name__ == "__main__":
    main()