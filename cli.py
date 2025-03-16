#!/usr/bin/env python
"""
Command Line Interface for SkillLab
Provides the 'skilllab' and 'sl' commands

This is the modernized CLI implementation using Click and leveraging the API layer.
"""

import os
import sys
import json
import time
import subprocess
import click
from pathlib import Path
from typing import Optional, List, Dict, Any

# Import API functions
from api.extraction import (
    extract_text_from_pdf,
    batch_extract_text,
    generate_json_from_text,
    batch_generate_json,
    validate_and_correct_json,
    run_full_extraction_pipeline
)
from api.training import (
    run_training_pipeline,
    get_available_models,
    get_dataset_metadata,
    build_training_dataset,
    train_donut_model,
    evaluate_model,
    get_training_progress,
    get_training_history,
    export_model,
    delete_model
)
from api.monitoring import (
    initialize_monitoring_system,
    shutdown_monitoring_system,
    get_system_resources,
    start_resource_monitoring,
    stop_resource_monitoring,
    get_pipeline_progress,
    get_performance_metrics,
    get_recent_activity,
    get_document_processing_stats,
    record_custom_metric
)
from api.review import (
    get_review_queue,
    get_document_details,
    update_document_status,
    save_review_feedback,
    get_dashboard_stats,
    get_review_history,
    get_performance_stats,
    get_error_analysis, 
    get_improvement_metrics,
    approve_document,
    reject_document,
    save_document_json,
    load_documents_from_filesystem,
    sync_review_data,
    recycle_for_training
)

from api.health import get_health_api
from config import get_config
from ui.common.factory import UIType
from utils.logger import setup_logger

# Setup logger
logger = setup_logger("cli")

# Version 
__version__ = "0.2.0"

def get_project_root() -> Path:
    """Get the project root directory"""
    return Path(__file__).parent.absolute()

# Command group styling
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])

@click.group(context_settings=CONTEXT_SETTINGS)
@click.version_option(version=__version__, prog_name="SkillLab")
def cli():
    """SkillLab - Extract, structure, and train models on resume data"""
    pass

# -- Run commands --
@cli.group()
def run():
    """Run SkillLab processing pipelines"""
    pass

@run.command("pipeline")
@click.option("--input-dir", type=click.Path(exists=True, file_okay=False, dir_okay=True), 
              help="Directory with input resume PDFs")
@click.option("--output-dir", type=click.Path(file_okay=False, dir_okay=True),
              help="Directory for output files")
@click.option("--model-dir", type=click.Path(file_okay=False, dir_okay=True),
              help="Directory to save fine-tuned model")
@click.option("--start", type=click.Choice(["ocr", "json", "correction", "dataset", "training"]), 
              default="ocr", help="Step to start from")
@click.option("--end", type=click.Choice(["ocr", "json", "correction", "dataset", "training"]), 
              default="training", help="Step to end at")
@click.option("--limit", type=int, help="Limit number of resumes to process")
@click.option("--gpu-monitor/--no-gpu-monitor", default=False, help="Enable GPU monitoring")
@click.option("--epochs", type=int, default=5, help="Training epochs")
@click.option("--batch-size", type=int, default=4, help="Training batch size")
@click.option("--human-review/--no-human-review", default=False, help="Enable human review for flagged documents")
def run_pipeline(input_dir, output_dir, model_dir, start, end, limit, gpu_monitor, epochs, batch_size, human_review):
    """Run the full SkillLab pipeline"""
    try:
        # Map args to the API format
        config = get_config()
        input_dir = input_dir or config.paths.input_dir
        output_dir = output_dir or config.paths.output_dir
        
        # Check if we're running the full pipeline or just the extraction part
        if end in ["dataset", "training"]:
            # Need to run both extraction and training pipelines
            click.echo("Starting extraction pipeline...")
            extraction_result = run_full_extraction_pipeline(
                input_dir=input_dir,
                output_dir=output_dir,
                limit=limit
            )
            
            click.echo("Starting training pipeline...")
            training_result = run_training_pipeline(
                start_with_dataset=True,
                output_dir=output_dir,
                model_dir=model_dir,
                epochs=epochs,
                batch_size=batch_size,
                enable_gpu_monitoring=gpu_monitor
            )
            
            click.echo(click.style("\nPipeline completed successfully!", fg="green"))
        else:
            # Just run the extraction pipeline
            click.echo("Starting extraction pipeline...")
            result = run_full_extraction_pipeline(
                input_dir=input_dir,
                output_dir=output_dir,
                limit=limit
            )
            
            click.echo(click.style("\nExtraction pipeline completed successfully!", fg="green"))
    except Exception as e:
        click.echo(click.style(f"Error running pipeline: {str(e)}", fg="red"))
        return 1

@run.command("extract")
@click.option("--input-dir", type=click.Path(exists=True, file_okay=False, dir_okay=True), required=True,
              help="Directory with input resume PDFs")
@click.option("--output-dir", type=click.Path(file_okay=False, dir_okay=True),
              help="Directory for output files")
@click.option("--limit", type=int, help="Limit number of resumes to process")
def run_extraction(input_dir, output_dir, limit):
    """Run OCR extraction only"""
    try:
        results = batch_extract_text(
            input_dir=input_dir,
            output_dir=output_dir,
            limit=limit
        )
        
        click.echo(click.style(f"Extraction completed successfully! Processed {len(results)} documents.", fg="green"))
    except Exception as e:
        click.echo(click.style(f"Error during extraction: {str(e)}", fg="red"))
        return 1

@run.command("structure")
@click.option("--input-dir", type=click.Path(exists=True, file_okay=False, dir_okay=True),
              help="Directory with OCR results")
@click.option("--output-dir", type=click.Path(file_okay=False, dir_okay=True),
              help="Directory for output files")
@click.option("--gpu-monitor/--no-gpu-monitor", default=False, help="Enable GPU monitoring")
def run_structure(input_dir, output_dir, gpu_monitor):
    """Run JSON generation and correction"""
    try:
        # First get the OCR results from the input directory
        config = get_config()
        input_dir = input_dir or os.path.join(config.paths.output_dir, "ocr_results")
        output_dir = output_dir or config.paths.output_dir
        
        # Check if input directory exists
        if not os.path.exists(input_dir):
            click.echo(click.style(f"Error: Input directory {input_dir} does not exist", fg="red"))
            return 1
        
        # Get all OCR result files
        ocr_files = [f for f in os.listdir(input_dir) if f.endswith("_ocr.json")]
        
        if not ocr_files:
            click.echo(click.style(f"No OCR result files found in {input_dir}", fg="yellow"))
            return 1
        
        # Load OCR results
        click.echo(f"Loading {len(ocr_files)} OCR result files...")
        with click.progressbar(ocr_files, label="Loading OCR files") as bar:
            ocr_results = []
            for file in bar:
                try:
                    with open(os.path.join(input_dir, file), 'r', encoding='utf-8') as f:
                        ocr_results.append(json.load(f))
                except Exception as e:
                    click.echo(f"Error loading {file}: {str(e)}")
        
        # Generate JSON for all OCR results
        click.echo("Generating JSON from OCR results...")
        json_results = batch_generate_json(
            ocr_results=ocr_results,
            output_dir=os.path.join(output_dir, "json_results")
        )
        
        click.echo(click.style(f"JSON generation completed successfully! Generated {len(json_results)} JSONs.", fg="green"))
    except Exception as e:
        click.echo(click.style(f"Error during JSON generation: {str(e)}", fg="red"))
        return 1

@run.command("train")
@click.option("--dataset-dir", type=click.Path(exists=True, file_okay=False, dir_okay=True),
              help="Directory with dataset")
@click.option("--model-dir", type=click.Path(file_okay=False, dir_okay=True),
              help="Directory to save model")
@click.option("--epochs", type=int, default=5, help="Training epochs")
@click.option("--batch-size", type=int, default=4, help="Training batch size")
@click.option("--gpu-monitor/--no-gpu-monitor", default=False, help="Enable GPU monitoring")
def run_training(dataset_dir, model_dir, epochs, batch_size, gpu_monitor):
    """Run model training"""
    try:
        config = get_config()
        dataset_dir = dataset_dir or os.path.join(config.paths.output_dir, "donut_dataset")
        model_dir = model_dir or config.paths.model_dir
        
        click.echo("Starting training pipeline...")
        result = run_training_pipeline(
            start_with_dataset=True,
            output_dir=os.path.dirname(dataset_dir),
            model_dir=model_dir,
            epochs=epochs,
            batch_size=batch_size,
            enable_gpu_monitoring=gpu_monitor
        )
        
        if result["status"] == "completed":
            click.echo(click.style("\nTraining completed successfully!", fg="green"))
            
            # Print training metrics
            if "training" in result and "eval_metrics" in result["training"]:
                eval_loss = result["training"]["eval_metrics"].get("eval_loss", "N/A")
                click.echo(f"Final evaluation loss: {eval_loss}")
            
            return 0
        else:
            click.echo(click.style(f"Training failed: {result.get('training_error', 'Unknown error')}", fg="red"))
            return 1
    except Exception as e:
        click.echo(click.style(f"Error during training: {str(e)}", fg="red"))
        return 1

# -- UI commands --
@cli.group()
def ui():
    """Launch SkillLab user interfaces"""
    pass

@ui.command("dashboard")
@click.option("--ui-type", type=click.Choice(["cli", "web"]), default="web", help="UI type to use")
@click.option("--port", type=int, default=8501, help="Port for web interface")
@click.option("--no-browser", is_flag=True, help="Don't open browser")
def launch_dashboard(ui_type, port, no_browser):
    """Launch main dashboard"""
    _launch_ui("dashboard", ui_type, port, no_browser)

@ui.command("monitor")
@click.option("--ui-type", type=click.Choice(["cli", "web"]), default="cli", help="UI type to use")
@click.option("--log-file", type=click.Path(exists=True), help="Path to log file")
@click.option("--db-file", type=click.Path(exists=True), help="Path to database file")
def launch_monitor(ui_type, log_file, db_file):
    """Launch monitoring dashboard"""
    _launch_ui("monitor", ui_type, 8501, False, log_file, db_file)

@ui.command("review")
@click.option("--ui-type", type=click.Choice(["cli", "web"]), default="web", help="UI type to use")
@click.option("--port", type=int, default=8501, help="Port for web interface")
@click.option("--no-browser", is_flag=True, help="Don't open browser")
@click.option("--sync", is_flag=True, help="Sync databases before launching")
def launch_review(ui_type, port, no_browser, sync):
    """Launch review interface"""
    _launch_ui("review", ui_type, port, no_browser, sync=sync)

@ui.command("training")
@click.option("--ui-type", type=click.Choice(["cli", "web"]), default="web", help="UI type to use")
@click.option("--port", type=int, default=8501, help="Port for web interface")
@click.option("--no-browser", is_flag=True, help="Don't open browser")
def launch_training(ui_type, port, no_browser):
    """Launch training interface"""
    _launch_ui("training", ui_type, port, no_browser)

@ui.command("extraction")
@click.option("--ui-type", type=click.Choice(["cli", "web"]), default="web", help="UI type to use")
@click.option("--port", type=int, default=8501, help="Port for web interface")
@click.option("--no-browser", is_flag=True, help="Don't open browser")
def launch_extraction(ui_type, port, no_browser):
    """Launch extraction interface"""
    _launch_ui("extraction", ui_type, port, no_browser)

def _launch_ui(ui_command, ui_type, port, no_browser, log_file=None, db_file=None, sync=False):
    """Common function to launch UIs"""
    try:
        # Convert underscores to dashes for command line arguments
        ui_command_arg = ui_command.replace("_", "-")
        
        # Build command
        launch_cmd = [
            sys.executable, 
            os.path.join(get_project_root(), "launch_ui.py"),
            ui_command_arg,
            "--ui-type", ui_type
        ]
        
        # Add optional arguments
        if port and port != 8501:
            launch_cmd.extend(["--port", str(port)])
        
        if no_browser:
            launch_cmd.append("--no-browser")
        
        if log_file:
            launch_cmd.extend(["--log-file", log_file])
        
        if db_file:
            launch_cmd.extend(["--db-file", db_file])
        
        if sync:
            launch_cmd.append("--sync")
        
        # Run the launch script
        click.echo(f"Launching {ui_command} interface...")
        subprocess.run(launch_cmd)
        return 0
    
    except Exception as e:
        click.echo(click.style(f"Error launching UI: {str(e)}", fg="red"))
        return 1

# -- Review commands --
@cli.group()
def review():
    """Review operations"""
    pass

@review.command("web")
@click.option("--port", type=int, default=8501, help="Port for web interface")
@click.option("--no-browser", is_flag=True, help="Don't open browser")
def review_web(port, no_browser):
    """Launch web review interface"""
    _launch_ui("review", "web", port, no_browser)

@review.command("status")
def review_status():
    """Show review queue status"""
    try:
        # Get dashboard stats from API
        stats = get_dashboard_stats()
        
        click.echo(click.style("\n=== Review Queue Status ===", fg="cyan", bold=True))
        click.echo(f"Total Documents:     {stats.get('total_documents', 0)}")
        click.echo(f"Flagged for Review:  {stats.get('flagged_documents', 0)}")
        click.echo(f"Reviewed:            {stats.get('reviewed_documents', 0)}")
        
        # Calculate pending
        pending = stats.get('flagged_documents', 0) - stats.get('reviewed_documents', 0)
        click.echo(f"Pending Review:      {pending}")
        
        # Print issue breakdown
        if 'issue_stats' in stats and stats['issue_stats']:
            click.echo(click.style("\n=== Issue Breakdown ===", fg="cyan"))
            for issue_type, count in stats['issue_stats'].items():
                click.echo(f"{issue_type}: {count}")
        
        # Show pending documents
        if pending > 0:
            click.echo(click.style("\n=== Pending Documents ===", fg="cyan"))
            documents = get_review_queue(limit=5)
            
            for i, doc in enumerate(documents[:5], 1):
                click.echo(f"{i}. {click.style(doc['id'], fg='green')} - {doc['filename']}")
                issues = [f"{issue['type']}" for issue in doc.get('issues', [])]
                if issues:
                    click.echo(f"   Issues: {', '.join(issues)}")
            
            if len(documents) > 5:
                click.echo(f"... and {len(documents) - 5} more")
            
            click.echo(click.style("\nTip:", fg="yellow") + " Run 'skilllab review web' to start the web review interface")
    except Exception as e:
        click.echo(click.style(f"Error getting review queue status: {str(e)}", fg="red"))

@review.command("list")
@click.option("--filter", type=str, help="Filter by issue type")
@click.option("--limit", type=int, default=25, help="Limit number of results")
def review_list(filter, limit):
    """List documents in review queue"""
    try:
        # Get documents from API
        documents = get_review_queue(filter or 'All', limit)
        
        if not documents:
            click.echo("No documents in the review queue")
            return
        
        click.echo(click.style(f"\n=== Documents Flagged for Review ({len(documents)}) ===", fg="cyan", bold=True))
        
        if filter and filter != 'All':
            click.echo(f"Filtered by issue: {click.style(filter, fg='yellow')}")
        
        click.echo("\nID                    | Status      | OCR Conf | JSON Conf | Issues")
        click.echo("-" * 80)
        
        for doc in documents:
            # Format confidence scores
            ocr_conf = f"{doc.get('ocr_confidence', 0):.1f}%".ljust(8)
            json_conf = f"{doc.get('json_confidence', 0):.1f}%".ljust(9)
            
            # Format issues
            issues = ", ".join([issue['type'] for issue in doc.get('issues', [])])
            
            # Format status
            status = doc.get('status', 'unknown').ljust(11)
            
            # Print row
            click.echo(f"{doc['id'][:20].ljust(21)} | {status} | {ocr_conf} | {json_conf} | {issues}")
        
        click.echo(click.style("\nTip:", fg="yellow") + " Run 'skilllab review web' to start the web review interface")
    except Exception as e:
        click.echo(click.style(f"Error listing documents: {str(e)}", fg="red"))

@review.command("sync")
def review_sync():
    """Synchronize review databases"""
    try:
        click.echo("Synchronizing databases...")
        docs, issues = sync_review_data()
        click.echo(click.style(f"Sync complete. Synced {docs} documents and {issues} issues.", fg="green"))
    except Exception as e:
        click.echo(click.style(f"Error syncing databases: {str(e)}", fg="red"))

# -- Monitoring commands --
@cli.group()
def monitor():
    """Monitoring operations"""
    pass

@monitor.command("status")
def monitor_status():
    """Show monitoring status"""
    try:
        # Initialize monitoring if needed
        initialize_monitoring_system()
        
        # Get system resources
        resources = get_system_resources()
        
        click.echo(click.style("\n=== System Resources ===", fg="cyan", bold=True))
        click.echo(f"CPU Usage:      {resources['cpu']['percent']}%")
        click.echo(f"Memory Used:    {resources['memory']['used_gb']:.2f} GB / {resources['memory']['total_gb']:.2f} GB ({resources['memory']['percent']}%)")
        click.echo(f"Disk Used:      {resources['disk']['used_gb']:.2f} GB / {resources['disk']['total_gb']:.2f} GB ({resources['disk']['percent']}%)")
        
        # Show GPU info if available
        if "gpu" in resources:
            click.echo(click.style("\n=== GPU Resources ===", fg="cyan"))
            for gpu_id, gpu_data in resources["gpu"].items():
                click.echo(f"GPU {gpu_id} ({gpu_data['name']}):")
                click.echo(f"  Utilization:   {gpu_data['utilization_percent']}%")
                click.echo(f"  Memory Used:   {gpu_data['memory_used_gb']:.2f} GB / {gpu_data['memory_total_gb']:.2f} GB")
                click.echo(f"  Temperature:   {gpu_data['temperature_c']}°C")
        
        # Get pipeline progress
        progress = get_pipeline_progress()
        
        click.echo(click.style("\n=== Pipeline Progress ===", fg="cyan"))
        for step, data in progress.items():
            # Calculate percentage
            if data["total"] > 0:
                percentage = (data["completed"] / data["total"]) * 100
            else:
                percentage = 0
            
            # Format status
            status = f"{data['completed']} / {data['total']} ({percentage:.1f}%)"
            
            # Add indicator for active step
            if data["active"]:
                status += " " + click.style("(ACTIVE)", fg="green")
            
            click.echo(f"{step.capitalize().ljust(12)}: {status}")
        
        # Get recent activity
        activities = get_recent_activity(limit=3)
        
        if activities:
            click.echo(click.style("\n=== Recent Activity ===", fg="cyan"))
            for activity in activities:
                activity_type = activity["type"].capitalize()
                status = activity["status"].capitalize()
                step = activity["step"].capitalize()
                
                # Format time
                start_time = activity.get("start_time", "Unknown")
                if not isinstance(start_time, str):
                    start_time = start_time.strftime("%Y-%m-%d %H:%M:%S")
                
                click.echo(f"{activity_type} - {step}: {status} ({start_time})")
    except Exception as e:
        click.echo(click.style(f"Error getting monitoring status: {str(e)}", fg="red"))

@monitor.command("dashboard")
@click.option("--ui-type", type=click.Choice(["cli", "web"]), default="cli", help="UI type to use")
def monitor_dashboard(ui_type):
    """Launch monitoring dashboard"""
    _launch_ui("monitor", ui_type, 8501, False)

@monitor.command("metrics")
@click.option("--type", type=str, help="Filter by metric type")
@click.option("--range", type=click.Choice(["hour", "day", "week", "month"]), default="day", 
              help="Time range for metrics")
def monitor_metrics(type, range):
    """Show performance metrics"""
    try:
        # Get performance metrics
        metrics = get_performance_metrics(time_range=range, metric_type=type)
        
        if "error" in metrics:
            click.echo(click.style(f"Error: {metrics['error']}", fg="red"))
            return
        
        click.echo(click.style(f"\n=== Performance Metrics ({range}) ===", fg="cyan", bold=True))
        click.echo(f"Time range: {metrics['start_time']} to {metrics['end_time']}")
        
        if "metrics" in metrics:
            for metric_type, metric_data in metrics["metrics"].items():
                click.echo(click.style(f"\n{metric_type.capitalize()} Metrics", fg="cyan"))
                
                for metric_name, data_points in metric_data.items():
                    # Calculate average
                    if data_points:
                        avg_value = sum(p["value"] for p in data_points) / len(data_points)
                        last_value = data_points[-1]["value"]
                        
                        click.echo(f"{metric_name.replace('_', ' ').capitalize()}:")
                        click.echo(f"  Latest: {last_value:.2f}")
                        click.echo(f"  Average: {avg_value:.2f}")
                        click.echo(f"  Data points: {len(data_points)}")
    except Exception as e:
        click.echo(click.style(f"Error getting performance metrics: {str(e)}", fg="red"))

# -- Training commands --
@cli.group()
def training():
    """Training operations"""
    pass

@training.command("list-models")
def training_list_models():
    """List available models"""
    try:
        models = get_available_models()
        
        if not models:
            click.echo("No models available")
            return
        
        click.echo(click.style("\n=== Available Models ===", fg="cyan", bold=True))
        
        for i, model in enumerate(models, 1):
            # Format metadata
            created = model.get("created_at", "Unknown")
            size = model.get("size_mb", 0)
            
            click.echo(f"{i}. {click.style(model['name'], fg='green')}")
            click.echo(f"   Path: {model['path']}")
            click.echo(f"   Created: {created}")
            click.echo(f"   Size: {size:.2f} MB")
            
            # Show metrics if available
            if "metrics" in model and model["metrics"]:
                click.echo(f"   Metrics:")
                for key, value in model["metrics"].items():
                    click.echo(f"     {key}: {value}")
            
            click.echo("")
    except Exception as e:
        click.echo(click.style(f"Error listing models: {str(e)}", fg="red"))

@training.command("dataset-info")
@click.option("--dataset-dir", type=click.Path(exists=True, file_okay=False, dir_okay=True),
              help="Directory with dataset")
def training_dataset_info(dataset_dir):
    """Show dataset information"""
    try:
        config = get_config()
        dataset_dir = dataset_dir or os.path.join(config.paths.output_dir, "donut_dataset")
        
        metadata = get_dataset_metadata(dataset_dir)
        
        if not metadata:
            click.echo("No dataset found or metadata not available")
            return
        
        click.echo(click.style("\n=== Dataset Information ===", fg="cyan", bold=True))
        click.echo(f"Path: {dataset_dir}")
        
        # Print dataset stats
        if "train_samples" in metadata:
            click.echo(f"Training samples: {metadata['train_samples']}")
        if "val_samples" in metadata:
            click.echo(f"Validation samples: {metadata['val_samples']}")
        if "test_samples" in metadata:
            click.echo(f"Test samples: {metadata['test_samples']}")
        
        total_samples = (metadata.get("train_samples", 0) + 
                         metadata.get("val_samples", 0) + 
                         metadata.get("test_samples", 0))
        click.echo(f"Total samples: {total_samples}")
        
        # Print creation date
        if "created_at" in metadata:
            click.echo(f"Created at: {metadata['created_at']}")
        
        # Print sample information if available
        if "sample_info" in metadata and metadata["sample_info"]:
            click.echo(click.style("\n=== Sample Information ===", fg="cyan"))
            for key, value in metadata["sample_info"].items():
                click.echo(f"{key}: {value}")
    except Exception as e:
        click.echo(click.style(f"Error getting dataset info: {str(e)}", fg="red"))

@training.command("web")
def training_web():
    """Launch training web interface"""
    _launch_ui("training", "web", 8501, False)

# -- Health commands --
@cli.group()
def health():
    """Health check operations"""
    pass

@health.command("check")
@click.option("--all", is_flag=True, help="Check all components")
def health_check(all):
    """Run health checks on the system"""
    try:
        click.echo("Running health checks...")
        health_api = get_health_api()
        
        if all:
            # Check all components
            results = health_api.check_all_components()
        else:
            # Check core components only
            results = health_api.check_core_components()
        
        # Print results
        click.echo(click.style("\n=== Health Check Results ===", fg="cyan", bold=True))
        
        overall_status = "Healthy" if results["status"] == "healthy" else "Unhealthy"
        status_color = "green" if results["status"] == "healthy" else "red"
        click.echo(f"Overall Status: {click.style(overall_status, fg=status_color, bold=True)}")
        
        # Print component results
        for component, status in results["components"].items():
            status_text = status["status"].capitalize()
            status_color = "green" if status["status"] == "healthy" else "red"
            
            click.echo(f"\n{component.capitalize()}:")
            click.echo(f"  Status: {click.style(status_text, fg=status_color)}")
            
            if "message" in status:
                click.echo(f"  Message: {status['message']}")
            
            if "details" in status and status["details"]:
                for key, value in status["details"].items():
                    click.echo(f"  {key}: {value}")
    except Exception as e:
        click.echo(click.style(f"Error running health checks: {str(e)}", fg="red"))

def main():
    """Main entry point for the CLI"""
    try:
        cli()
    except Exception as e:
        click.echo(click.style(f"Error: {str(e)}", fg="red"))
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())