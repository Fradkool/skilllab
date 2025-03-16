"""
Training API for SkillLab
Provides high-level functions for dataset building and model training
"""

import os
import time
import json
import glob
import logging
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime, timedelta

from config import get_config, AppConfig
from pipeline import get_executor, PipelineContext
from database import get_metrics_repository
from database.metrics_db import MetricsRepository
from training.dataset_builder import DonutDatasetBuilder
from training.train_donut import DonutTrainer
from utils.gpu_monitor import GPUMonitor

# Setup logger
logger = logging.getLogger(__name__)

def build_training_dataset(
    input_dir: Optional[str] = None, 
    output_dir: Optional[str] = None,
    train_val_split: Optional[float] = None,
    task_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Build training dataset from validated JSONs
    
    Args:
        input_dir: Input directory with validated JSONs (None to use configured directory)
        output_dir: Output directory for dataset (None to use configured directory)
        train_val_split: Train/validation split ratio (None to use configured value)
        task_name: Task name for dataset (None to use configured task name)
        
    Returns:
        Dictionary with dataset statistics
        
    Raises:
        FileNotFoundError: If input directory doesn't exist
    """
    # Get configuration
    config = get_config()
    
    # Set default values if not provided
    input_dir = input_dir or os.path.join(config.paths.output_dir, "validated_json")
    output_dir = output_dir or os.path.join(config.paths.output_dir, "donut_dataset")
    train_val_split = train_val_split or config.dataset.train_val_split
    task_name = task_name or config.dataset.task_name
    
    # Check if input directory exists
    if not os.path.exists(input_dir):
        raise FileNotFoundError(f"Input directory not found: {input_dir}")
    
    # Initialize dataset builder
    dataset_builder = DonutDatasetBuilder(
        validated_json_dir=input_dir,
        donut_dataset_dir=output_dir,
        train_val_split=train_val_split,
        task_name=task_name
    )
    
    # Build dataset
    start_time = time.time()
    stats = dataset_builder.build_dataset()
    
    # Add timing information
    stats["time"] = time.time() - start_time
    
    # Update metrics repository
    metrics_repo = get_metrics_repository()
    if metrics_repo:
        metrics_repo.record_metric(
            "dataset", 
            "build_time", 
            stats["time"], 
            details={
                "train_samples": stats.get("train_samples", 0),
                "val_samples": stats.get("val_samples", 0)
            }
        )
    
    return stats

def train_donut_model(
    dataset_dir: Optional[str] = None,
    output_dir: Optional[str] = None,
    pretrained_model: Optional[str] = None,
    epochs: Optional[int] = None,
    batch_size: Optional[int] = None,
    learning_rate: Optional[float] = None,
    enable_gpu_monitoring: bool = False
) -> Dict[str, Any]:
    """
    Train Donut model on resume dataset
    
    Args:
        dataset_dir: Directory with dataset (None to use configured directory)
        output_dir: Output directory for model (None to use configured directory)
        pretrained_model: Pre-trained model to use (None to use configured model)
        epochs: Number of epochs (None to use configured value)
        batch_size: Batch size (None to use configured value)
        learning_rate: Learning rate (None to use configured value)
        enable_gpu_monitoring: Whether to enable GPU monitoring
        
    Returns:
        Dictionary with training results
        
    Raises:
        FileNotFoundError: If dataset directory doesn't exist
    """
    # Get configuration
    config = get_config()
    
    # Set default values if not provided
    dataset_dir = dataset_dir or os.path.join(config.paths.output_dir, "donut_dataset")
    output_dir = output_dir or config.paths.model_dir
    pretrained_model = pretrained_model or config.training.pretrained_model
    epochs = epochs or config.training.epochs
    batch_size = batch_size or config.training.batch_size
    learning_rate = learning_rate or config.training.learning_rate
    
    # Check if dataset directory exists
    if not os.path.exists(dataset_dir):
        raise FileNotFoundError(f"Dataset directory not found: {dataset_dir}")
    
    # Initialize GPU monitor if requested
    gpu_monitor = None
    if enable_gpu_monitoring:
        gpu_monitor = GPUMonitor()
    
    # Initialize Donut trainer
    trainer = DonutTrainer(
        dataset_dir=dataset_dir,
        output_dir=output_dir,
        pretrained_model=pretrained_model,
        max_epochs=epochs,
        batch_size=batch_size,
        learning_rate=learning_rate,
        gpu_monitor=gpu_monitor
    )
    
    # Train the model
    start_time = time.time()
    training_results = trainer.train()
    
    # Add timing information if not already present
    if "training_time" not in training_results:
        training_results["training_time"] = time.time() - start_time
    
    # Add GPU statistics if available
    if gpu_monitor:
        training_results["gpu_stats"] = gpu_monitor.get_summary("training")
    
    # Update metrics repository
    metrics_repo = get_metrics_repository()
    if metrics_repo:
        metrics_repo.record_metric(
            "training", 
            "total_time", 
            training_results.get("training_time", 0), 
            details={
                "eval_loss": training_results.get("eval_metrics", {}).get("eval_loss", 0),
                "epochs": epochs,
                "batch_size": batch_size
            }
        )
    
    return training_results

def evaluate_model(
    model_dir: Optional[str] = None,
    test_dataset_dir: Optional[str] = None,
    batch_size: Optional[int] = None
) -> Dict[str, Any]:
    """
    Evaluate a trained Donut model
    
    Args:
        model_dir: Directory with trained model (None to use configured directory)
        test_dataset_dir: Directory with test dataset (None to use validation split)
        batch_size: Batch size for evaluation (None to use configured value)
        
    Returns:
        Dictionary with evaluation results
        
    Raises:
        FileNotFoundError: If model directory doesn't exist
    """
    # Get configuration
    config = get_config()
    
    # Set default values if not provided
    model_dir = model_dir or config.paths.model_dir
    batch_size = batch_size or config.training.batch_size
    
    if test_dataset_dir is None:
        # Use validation set by default
        test_dataset_dir = os.path.join(config.paths.output_dir, "donut_dataset", "validation")
    
    # Check if model directory exists
    if not os.path.exists(model_dir):
        raise FileNotFoundError(f"Model directory not found: {model_dir}")
    
    # Check if test dataset directory exists
    if not os.path.exists(test_dataset_dir):
        raise FileNotFoundError(f"Test dataset directory not found: {test_dataset_dir}")
    
    # Initialize Donut trainer for evaluation
    trainer = DonutTrainer(
        dataset_dir=os.path.dirname(test_dataset_dir),  # Parent directory
        output_dir=model_dir,
        pretrained_model=model_dir,  # Use the trained model
        batch_size=batch_size
    )
    
    # Load model and processor
    start_time = time.time()
    model, processor = trainer.setup_model_and_processor()
    
    # Evaluate model
    from transformers import Seq2SeqTrainingArguments, Seq2SeqTrainer
    
    # Create dataset
    test_dataset = trainer.ResumeDonutDataset(
        dataset_dir=test_dataset_dir,
        processor=processor
    )
    
    # Configure training arguments for evaluation
    training_args = Seq2SeqTrainingArguments(
        output_dir=os.path.join(model_dir, "eval"),
        per_device_eval_batch_size=batch_size,
        predict_with_generate=True,
        generation_max_length=processor.tokenizer.model_max_length,
        generation_num_beams=1,
        fp16=True
    )
    
    # Initialize trainer
    seq2seq_trainer = Seq2SeqTrainer(
        model=model,
        args=training_args,
        tokenizer=processor.tokenizer
    )
    
    # Evaluate
    eval_metrics = seq2seq_trainer.evaluate(
        eval_dataset=test_dataset,
        max_length=processor.tokenizer.model_max_length,
        num_beams=1
    )
    
    # Add timing information
    eval_metrics["eval_time"] = time.time() - start_time
    
    # Update metrics repository
    metrics_repo = get_metrics_repository()
    if metrics_repo:
        metrics_repo.record_metric(
            "evaluation", 
            "eval_loss", 
            eval_metrics.get("eval_loss", 0), 
            details={
                "eval_time": eval_metrics["eval_time"],
                "model_dir": model_dir
            }
        )
    
    return eval_metrics

def run_training_pipeline(
    start_with_dataset: bool = True,
    input_dir: Optional[str] = None,
    output_dir: Optional[str] = None,
    model_dir: Optional[str] = None,
    epochs: Optional[int] = None,
    batch_size: Optional[int] = None,
    enable_gpu_monitoring: bool = False
) -> Dict[str, Any]:
    """
    Run the complete training pipeline (dataset building and model training)
    
    Args:
        start_with_dataset: Whether to start with dataset building
        input_dir: Input directory (None to use configured directory)
        output_dir: Output directory (None to use configured directory)
        model_dir: Model directory (None to use configured directory)
        epochs: Number of epochs (None to use configured value)
        batch_size: Batch size (None to use configured value)
        enable_gpu_monitoring: Whether to enable GPU monitoring
        
    Returns:
        Dictionary with pipeline results
        
    Raises:
        FileNotFoundError: If required directories don't exist
    """
    # Get configuration
    config = get_config()
    
    # Set default values if not provided
    output_dir = output_dir or config.paths.output_dir
    model_dir = model_dir or config.paths.model_dir
    
    # Define dataset directories
    dataset_dir = os.path.join(output_dir, "donut_dataset")
    validated_json_dir = os.path.join(output_dir, "validated_json")
    
    # Create output directories if they don't exist
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(model_dir, exist_ok=True)
    os.makedirs(dataset_dir, exist_ok=True)
    
    # Initialize results
    results = {
        "start_time": time.time(),
        "dataset": None,
        "training": None
    }
    
    # Use pipeline executor for proper tracking
    executor = get_executor()
    context = PipelineContext(config=config)
    
    if start_with_dataset:
        # Build dataset
        try:
            dataset_stats = build_training_dataset(
                input_dir=validated_json_dir,
                output_dir=dataset_dir
            )
            results["dataset"] = dataset_stats
            
            # Store in context
            context.set_result("dataset", dataset_stats)
        except Exception as e:
            results["dataset_error"] = str(e)
            results["status"] = "failed"
            results["elapsed_time"] = time.time() - results["start_time"]
            return results
    
    # Train model
    try:
        training_results = train_donut_model(
            dataset_dir=dataset_dir,
            output_dir=model_dir,
            epochs=epochs,
            batch_size=batch_size,
            enable_gpu_monitoring=enable_gpu_monitoring
        )
        results["training"] = training_results
        
        # Store in context
        context.set_result("training", training_results)
    except Exception as e:
        results["training_error"] = str(e)
        results["status"] = "failed"
        results["elapsed_time"] = time.time() - results["start_time"]
        return results
    
    # Add total time
    results["elapsed_time"] = time.time() - results["start_time"]
    results["status"] = "completed"
    
    return results

def get_training_progress() -> Optional[Dict[str, Any]]:
    """
    Get information about ongoing or recent training
    
    Returns:
        Dictionary with training progress or None if no training is in progress/available
    """
    # Get configuration
    config = get_config()
    
    # Check if model directory exists
    model_dir = config.paths.model_dir
    if not os.path.exists(model_dir):
        return None
    
    # Check for training summary
    summary_files = glob.glob(os.path.join(model_dir, "training_summary.json"))
    summary_files.extend(glob.glob(os.path.join(model_dir, "checkpoints_*", "trainer_state.json")))
    
    if not summary_files:
        # No training in progress or completed
        return None
    
    # Find the most recent file
    most_recent = max(summary_files, key=os.path.getmtime)
    
    # Read file
    try:
        with open(most_recent, 'r', encoding='utf-8') as f:
            if most_recent.endswith("training_summary.json"):
                # Completed training
                summary = json.load(f)
                
                # Extract metrics
                train_metrics = summary.get("train_metrics", {})
                eval_metrics = summary.get("eval_metrics", {})
                
                # Format epochs
                total_epochs = config.training.epochs
                
                # Determine progress
                progress = 100.0  # Complete
                
                return {
                    "status": "completed",
                    "current_epoch": total_epochs,
                    "total_epochs": total_epochs,
                    "progress": progress,
                    "metrics": {
                        "epochs": list(range(1, total_epochs + 1)),
                        "train_loss": [train_metrics.get("train_loss", 0.0)],
                        "val_loss": [eval_metrics.get("eval_loss", 0.0)]
                    },
                    "dataset": _get_dataset_stats()
                }
            else:
                # In-progress training
                state = json.load(f)
                
                # Extract metrics
                log_history = state.get("log_history", [])
                if not log_history:
                    return None
                
                # Format epochs
                current_epoch = state.get("epoch", 0)
                total_epochs = config.training.epochs
                
                # Determine progress
                progress = min(100.0, (current_epoch / total_epochs) * 100.0 if total_epochs > 0 else 0)
                
                # Extract metrics for plotting
                epochs = []
                train_losses = []
                val_losses = []
                
                for entry in log_history:
                    if "epoch" in entry:
                        epochs.append(entry["epoch"])
                        if "loss" in entry:
                            train_losses.append(entry["loss"])
                        if "eval_loss" in entry:
                            val_losses.append(entry["eval_loss"])
                
                return {
                    "status": "in_progress",
                    "current_epoch": current_epoch,
                    "total_epochs": total_epochs,
                    "progress": progress,
                    "metrics": {
                        "epochs": epochs,
                        "train_loss": train_losses,
                        "val_loss": val_losses
                    },
                    "dataset": _get_dataset_stats()
                }
    except Exception as e:
        # Error reading file
        return None

def get_available_models() -> List[Dict[str, Any]]:
    """
    Get a list of available models, both trained and pre-trained
    
    Returns:
        List of model information dictionaries
    """
    # Get configuration
    config = get_config()
    
    # Define model directory
    model_dir = config.paths.model_dir
    
    # List of available models
    models = []
    
    # Check pre-trained models
    pre_trained_models = [
        {
            "id": "naver-clova-ix/donut-base",
            "name": "Donut Base (Pretrained)",
            "type": "pretrained",
            "description": "Naver Clova baseline Donut model",
            "size": "1.3GB"
        },
        {
            "id": "naver-clova-ix/donut-base-finetuned-cord-v2",
            "name": "Donut Base (CORD v2)",
            "type": "pretrained",
            "description": "Donut model fine-tuned on CORD dataset",
            "size": "1.3GB"
        }
    ]
    
    # Add pre-trained models
    models.extend(pre_trained_models)
    
    # Check local models
    if os.path.exists(model_dir):
        # Find all potential model directories
        model_dirs = [d for d in os.listdir(model_dir) 
                     if os.path.isdir(os.path.join(model_dir, d))]
        
        for dir_name in model_dirs:
            model_path = os.path.join(model_dir, dir_name)
            
            # Check if the directory contains a model config
            config_file = os.path.join(model_path, "config.json")
            if os.path.exists(config_file):
                # Determine model size
                model_size = _get_directory_size(model_path)
                
                # Try to get training info
                summary_file = os.path.join(model_path, "training_summary.json")
                training_date = None
                metrics = {}
                
                if os.path.exists(summary_file):
                    try:
                        with open(summary_file, 'r', encoding='utf-8') as f:
                            summary = json.load(f)
                        
                        # Extract metrics
                        metrics = {
                            "train_loss": summary.get("train_metrics", {}).get("train_loss", "N/A"),
                            "eval_loss": summary.get("eval_metrics", {}).get("eval_loss", "N/A")
                        }
                        
                        # Extract date
                        if "training_time" in summary:
                            training_date = datetime.fromtimestamp(
                                os.path.getmtime(summary_file)
                            ).strftime("%Y-%m-%d %H:%M:%S")
                    except Exception as e:
                        logger.error(f"Error reading training summary: {e}")
                
                # Add model to list
                models.append({
                    "id": dir_name,
                    "name": f"Local Model: {dir_name}",
                    "type": "local",
                    "description": f"Locally trained model {dir_name}",
                    "path": model_path,
                    "size": _format_size(model_size),
                    "training_date": training_date,
                    "metrics": metrics
                })
    
    return models

def get_dataset_metadata() -> Dict[str, Any]:
    """
    Get metadata about the available datasets
    
    Returns:
        Dictionary with dataset metadata
    """
    # Get configuration
    config = get_config()
    
    # Check dataset directory
    dataset_dir = os.path.join(config.paths.output_dir, "donut_dataset")
    
    # Prepare response
    metadata = {
        "datasets": [],
        "stats": _get_dataset_stats()
    }
    
    # Check if validation JSON directory exists
    validated_dir = os.path.join(config.paths.output_dir, "validated_json")
    if os.path.exists(validated_dir):
        metadata["available_json"] = len([f for f in os.listdir(validated_dir) 
                                         if f.endswith("_validated.json")])
    else:
        metadata["available_json"] = 0
    
    # Find all dataset splits
    if os.path.exists(dataset_dir):
        dataset_splits = []
        for split_name in ["train", "validation", "test"]:
            split_dir = os.path.join(dataset_dir, split_name)
            if os.path.exists(split_dir):
                # Count samples
                sample_count = 0
                index_file = os.path.join(dataset_dir, f"{split_name}_index.txt")
                
                if os.path.exists(index_file):
                    with open(index_file, 'r', encoding='utf-8') as f:
                        sample_count = len([line.strip() for line in f.readlines()])
                
                # Determine when the dataset was created
                creation_time = datetime.fromtimestamp(
                    os.path.getctime(split_dir)
                ).strftime("%Y-%m-%d %H:%M:%S")
                
                # Add to list
                dataset_splits.append({
                    "name": split_name,
                    "samples": sample_count,
                    "created": creation_time,
                    "path": split_dir
                })
        
        metadata["datasets"] = dataset_splits
    
    return metadata

def export_model(model_name: str, export_dir: Optional[str] = None) -> bool:
    """
    Export a trained model to a specific directory
    
    Args:
        model_name: Name of the model to export
        export_dir: Directory to export to (None for default exports directory)
        
    Returns:
        True if export successful, False otherwise
    """
    import shutil
    
    # Get configuration
    config = get_config()
    
    # Set default export directory if not provided
    if export_dir is None:
        export_dir = os.path.join(config.paths.output_dir, "exports")
    
    # Ensure export directory exists
    os.makedirs(export_dir, exist_ok=True)
    
    # Define model directory
    model_dir = os.path.join(config.paths.model_dir, model_name)
    
    # Check if model exists
    if not os.path.exists(model_dir):
        logger.error(f"Model directory not found: {model_dir}")
        return False
    
    try:
        # Create export package directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_package_dir = os.path.join(export_dir, f"{model_name}_{timestamp}")
        os.makedirs(export_package_dir, exist_ok=True)
        
        # Copy model files
        for file_name in ["config.json", "pytorch_model.bin", "training_args.bin", "vocab.json"]:
            src_path = os.path.join(model_dir, file_name)
            if os.path.exists(src_path):
                shutil.copy2(src_path, os.path.join(export_package_dir, file_name))
        
        # Add metadata
        metadata = {
            "model_name": model_name,
            "export_date": datetime.now().isoformat(),
            "model_type": "donut"
        }
        
        # Try to add training summary
        summary_path = os.path.join(model_dir, "training_summary.json")
        if os.path.exists(summary_path):
            try:
                with open(summary_path, 'r', encoding='utf-8') as f:
                    training_summary = json.load(f)
                metadata["training_summary"] = training_summary
            except Exception as e:
                logger.error(f"Error reading training summary: {e}")
        
        # Write metadata
        with open(os.path.join(export_package_dir, "metadata.json"), 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        # Create zip archive
        archive_path = f"{export_package_dir}.zip"
        shutil.make_archive(
            export_package_dir, 
            'zip', 
            export_package_dir
        )
        
        # Remove the temporary directory
        shutil.rmtree(export_package_dir)
        
        logger.info(f"Model exported to {archive_path}")
        return True
    
    except Exception as e:
        logger.error(f"Error exporting model: {e}")
        return False

def delete_model(model_name: str) -> bool:
    """
    Delete a trained model
    
    Args:
        model_name: Name of the model to delete
        
    Returns:
        True if deletion successful, False otherwise
    """
    import shutil
    
    # Get configuration
    config = get_config()
    
    # Define model directory
    model_dir = os.path.join(config.paths.model_dir, model_name)
    
    # Check if model exists
    if not os.path.exists(model_dir):
        logger.error(f"Model directory not found: {model_dir}")
        return False
    
    try:
        # Delete the model directory
        shutil.rmtree(model_dir)
        logger.info(f"Model {model_name} deleted")
        return True
    except Exception as e:
        logger.error(f"Error deleting model: {e}")
        return False

def get_training_history() -> List[Dict[str, Any]]:
    """
    Get history of model training runs
    
    Returns:
        List of training run information
    """
    # Get metrics repository
    metrics_repo = get_metrics_repository()
    if not metrics_repo:
        return []
    
    try:
        # Query training metrics
        training_metrics = metrics_repo.get_metrics_by_category("training")
        
        # Format metrics for display
        history = []
        
        for metric in training_metrics:
            # Extract basic information
            timestamp = metric.get("timestamp", "")
            value = metric.get("value", 0)
            name = metric.get("name", "")
            details = metric.get("details", {})
            
            # Format time
            try:
                if isinstance(timestamp, str):
                    dt = datetime.fromisoformat(timestamp)
                else:
                    dt = datetime.fromtimestamp(timestamp)
                formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S")
            except:
                formatted_time = str(timestamp)
            
            # Add to history
            history.append({
                "id": metric.get("id", ""),
                "timestamp": formatted_time,
                "raw_timestamp": timestamp,
                "name": name,
                "value": value,
                "eval_loss": details.get("eval_loss", "N/A"),
                "epochs": details.get("epochs", 0),
                "batch_size": details.get("batch_size", 0)
            })
        
        # Sort by timestamp (descending)
        history.sort(key=lambda x: x.get("raw_timestamp", 0), reverse=True)
        
        return history
    
    except Exception as e:
        logger.error(f"Error getting training history: {e}")
        return []

def _get_directory_size(directory: str) -> int:
    """
    Get the size of a directory in bytes
    
    Args:
        directory: Directory path
        
    Returns:
        Size in bytes
    """
    total_size = 0
    
    for dirpath, dirnames, filenames in os.walk(directory):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if os.path.exists(fp):
                total_size += os.path.getsize(fp)
    
    return total_size

def _format_size(size_bytes: int) -> str:
    """
    Format size in bytes to human-readable form
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string
    """
    if size_bytes < 1024:
        return f"{size_bytes} bytes"
    
    size_kb = size_bytes / 1024
    if size_kb < 1024:
        return f"{size_kb:.2f} KB"
    
    size_mb = size_kb / 1024
    if size_mb < 1024:
        return f"{size_mb:.2f} MB"
    
    size_gb = size_mb / 1024
    return f"{size_gb:.2f} GB"

def _get_dataset_stats() -> Dict[str, Any]:
    """
    Get dataset statistics for reporting
    
    Returns:
        Dataset statistics
    """
    # Get configuration
    config = get_config()
    
    # Define dataset directories
    dataset_dir = os.path.join(config.paths.output_dir, "donut_dataset")
    train_dir = os.path.join(dataset_dir, "train")
    val_dir = os.path.join(dataset_dir, "validation")
    
    if not os.path.exists(train_dir) or not os.path.exists(val_dir):
        return {}
    
    # Count samples
    train_samples = 0
    val_samples = 0
    single_page = 0
    multi_page = 0
    
    # Check train samples
    train_index = os.path.join(dataset_dir, f"train_index.txt")
    if os.path.exists(train_index):
        try:
            with open(train_index, 'r', encoding='utf-8') as f:
                train_files = [line.strip() for line in f.readlines()]
                train_samples = len(train_files)
        except Exception as e:
            logger.error(f"Error reading train index: {e}")
    
    # Check validation samples
    val_index = os.path.join(dataset_dir, f"validation_index.txt")
    if os.path.exists(val_index):
        try:
            with open(val_index, 'r', encoding='utf-8') as f:
                val_files = [line.strip() for line in f.readlines()]
                val_samples = len(val_files)
        except Exception as e:
            logger.error(f"Error reading validation index: {e}")
    
    # Calculate percentages
    if train_samples > 0 and val_samples > 0:
        split_ratio = train_samples / (train_samples + val_samples)
    else:
        split_ratio = 0.8  # Default
    
    # Estimate multi-page documents
    # This is a very rough estimation without loading all files
    if os.path.exists(train_dir) and os.path.exists(train_index):
        try:
            with open(train_index, 'r', encoding='utf-8') as f:
                train_files = [line.strip() for line in f.readlines()]
            
            # Sample the first 100 files
            for json_file in train_files[:100]:
                json_path = os.path.join(train_dir, json_file)
                if os.path.exists(json_path):
                    try:
                        with open(json_path, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                        
                        # Check if multi-page
                        if "multi_page" in metadata and metadata["multi_page"]:
                            multi_page += 1
                        else:
                            single_page += 1
                    except Exception:
                        pass
        except Exception as e:
            logger.error(f"Error checking page counts: {e}")
    
    # Extrapolate counts
    if single_page + multi_page > 0:
        ratio_single = single_page / (single_page + multi_page)
        ratio_multi = multi_page / (single_page + multi_page)
        
        single_page_estimated = int((train_samples + val_samples) * ratio_single)
        multi_page_estimated = int((train_samples + val_samples) * ratio_multi)
    else:
        single_page_estimated = train_samples + val_samples  # Assume all single page
        multi_page_estimated = 0
    
    return {
        "total_samples": train_samples + val_samples,
        "train_samples": train_samples,
        "val_samples": val_samples,
        "train_val_split": split_ratio,
        "single_page_samples": single_page_estimated,
        "multi_page_samples": multi_page_estimated
    }