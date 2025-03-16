"""
Training UI module for SkillLab
Implements UI for model training operations using the UI component system
"""

import os
import sys
import json
import time
from typing import Dict, List, Any, Optional, Union, Tuple
import threading

from utils.logger import setup_logger
from utils.gpu_monitor import GPUMonitor
from api.training import run_training_pipeline, get_training_progress
from config import get_config

from ui.common.factory import UIComponentFactory, UIType
from ui.common.adapter import TrainingAdapter

# Setup logger
logger = setup_logger("training_ui")

class TrainingUI:
    """UI for model training operations"""
    
    def __init__(self, ui_type: UIType = UIType.CLI):
        """
        Initialize training UI
        
        Args:
            ui_type: Type of UI to use (CLI or Web)
        """
        self.ui_type = ui_type
        self.config = get_config()
        
        # Initialize UI components using adapter
        self.training_adapter = TrainingAdapter(ui_type)
        
        # Monitoring
        self.gpu_monitor = None
        if self.config.training.gpu_monitoring:
            self.gpu_monitor = GPUMonitor()
        
        # State tracking
        self.is_training = False
        self.training_thread = None
        self.current_progress = None
    
    def _create_alert(self, alert_type: str, message: str) -> None:
        """
        Create an alert component and display it
        
        Args:
            alert_type: Type of alert (info, success, warning, error)
            message: Alert message
        """
        self.training_adapter.add_alert(alert_type, message)
    
    def _create_dataset_stats_display(self, dataset_info: Dict[str, Any]) -> None:
        """
        Create dataset statistics display
        
        Args:
            dataset_info: Dataset information
        """
        self.training_adapter.update_dataset_stats(dataset_info)
    
    def _update_training_progress(self, progress_data: Dict[str, Any]) -> None:
        """
        Update training progress display
        
        Args:
            progress_data: Training progress data
        """
        self.training_adapter.update_progress(progress_data)
        self.current_progress = progress_data
    
    def _update_training_metrics(self, metrics_data: Dict[str, Any]) -> None:
        """
        Update training metrics display
        
        Args:
            metrics_data: Training metrics data
        """
        self.training_adapter.update_metrics(metrics_data)
    
    def initialize_ui(self) -> None:
        """Initialize the training UI"""
        logger.info("Initializing training UI")
        
        # Initialize training form
        self.training_adapter.init_training_form()
        
        # Get dataset statistics
        dataset_stats = self._get_dataset_stats()
        if dataset_stats:
            self._create_dataset_stats_display(dataset_stats)
        
        # Check for in-progress training
        progress = get_training_progress()
        if progress:
            self._update_training_progress(progress)
            if "metrics" in progress:
                self._update_training_metrics(progress["metrics"])
    
    def _get_dataset_stats(self) -> Dict[str, Any]:
        """
        Get dataset statistics
        
        Returns:
            Dataset statistics
        """
        dataset_dir = self.config.training.dataset_dir
        train_dir = os.path.join(dataset_dir, "train")
        val_dir = os.path.join(dataset_dir, "validation")
        
        if not os.path.exists(train_dir) or not os.path.exists(val_dir):
            self._create_alert("warning", f"Dataset not found at {dataset_dir}")
            return {}
        
        # Count samples
        train_samples = 0
        val_samples = 0
        single_page = 0
        multi_page = 0
        
        # Check train samples
        train_index = os.path.join(os.path.dirname(train_dir), f"{os.path.basename(train_dir)}_index.txt")
        if os.path.exists(train_index):
            with open(train_index, 'r', encoding='utf-8') as f:
                train_files = [line.strip() for line in f.readlines()]
                train_samples = len(train_files)
        
        # Check validation samples
        val_index = os.path.join(os.path.dirname(val_dir), f"{os.path.basename(val_dir)}_index.txt")
        if os.path.exists(val_index):
            with open(val_index, 'r', encoding='utf-8') as f:
                val_files = [line.strip() for line in f.readlines()]
                val_samples = len(val_files)
        
        # Check page counts
        for json_file in train_files[:100]:  # Sample the first 100 files
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
        
        # Calculate percentages
        if train_samples > 0 and val_samples > 0:
            split_ratio = train_samples / (train_samples + val_samples)
        else:
            split_ratio = 0.8  # Default
        
        # Extrapolate counts
        if single_page + multi_page > 0:
            ratio_single = single_page / (single_page + multi_page)
            ratio_multi = multi_page / (single_page + multi_page)
            
            single_page_estimated = int((train_samples + val_samples) * ratio_single)
            multi_page_estimated = int((train_samples + val_samples) * ratio_multi)
        else:
            single_page_estimated = 0
            multi_page_estimated = 0
        
        return {
            "total_samples": train_samples + val_samples,
            "train_samples": train_samples,
            "val_samples": val_samples,
            "train_val_split": split_ratio,
            "single_page_samples": single_page_estimated,
            "multi_page_samples": multi_page_estimated
        }
    
    def start_training(self, form_values: Dict[str, Any]) -> bool:
        """
        Start model training
        
        Args:
            form_values: Training form values
            
        Returns:
            True if training started successfully, False otherwise
        """
        if self.is_training:
            self._create_alert("warning", "Training is already in progress")
            return False
        
        try:
            # Extract form values
            epochs = int(form_values.get("epochs", 5))
            batch_size = int(form_values.get("batch_size", 4))
            learning_rate = float(form_values.get("learning_rate", 0.00005))
            pretrained_model = form_values.get("pretrained_model", "naver-clova-ix/donut-base")
            use_gpu_monitor = bool(form_values.get("gpu_monitor", True))
            
            # Create alert
            self._create_alert("info", "Starting training pipeline...")
            
            # Start training in a separate thread
            self.is_training = True
            
            def training_thread():
                try:
                    # Run training
                    result = run_training_pipeline(
                        start_with_dataset=True,
                        epochs=epochs,
                        batch_size=batch_size,
                        learning_rate=learning_rate,
                        pretrained_model=pretrained_model,
                        enable_gpu_monitoring=use_gpu_monitor
                    )
                    
                    # Check result
                    if result.get("status") == "completed":
                        self._create_alert("success", "Training completed successfully!")
                        
                        # Get metrics
                        training_results = result.get("training", {})
                        eval_metrics = training_results.get("eval_metrics", {})
                        eval_loss = eval_metrics.get("eval_loss", "N/A")
                        
                        self._create_alert("info", f"Final evaluation loss: {eval_loss}")
                    else:
                        error_msg = result.get("error", "Unknown error")
                        self._create_alert("error", f"Training failed: {error_msg}")
                
                except Exception as e:
                    logger.error(f"Error during training: {str(e)}")
                    self._create_alert("error", f"Error during training: {str(e)}")
                
                finally:
                    # Update state
                    self.is_training = False
            
            # Start thread
            self.training_thread = threading.Thread(target=training_thread)
            self.training_thread.daemon = True
            self.training_thread.start()
            
            return True
        
        except Exception as e:
            logger.error(f"Error starting training: {str(e)}")
            self._create_alert("error", f"Error starting training: {str(e)}")
            self.is_training = False
            return False
    
    def refresh_ui(self) -> None:
        """Refresh training UI"""
        # Get latest progress
        progress = get_training_progress()
        
        if progress:
            # Update progress
            self._update_training_progress(progress)
            
            # Update metrics if available
            if "metrics" in progress:
                self._update_training_metrics(progress["metrics"])
            
            # Update dataset stats if available
            if "dataset" in progress:
                self._create_dataset_stats_display(progress["dataset"])
    
    def render(self) -> None:
        """Render the training UI"""
        # Get dashboard from adapter
        dashboard = self.training_adapter.get_dashboard()
        
        # Refresh data
        self.training_adapter.refresh()
        
        # Render dashboard
        if dashboard:
            dashboard.render()

def main():
    """Main entry point for training UI"""
    import argparse
    
    parser = argparse.ArgumentParser(description="SkillLab Training UI")
    parser.add_argument("--ui-type", type=str, choices=["cli", "web"], default="cli", help="UI type to use")
    args = parser.parse_args()
    
    # Determine UI type
    ui_type = UIType.WEB if args.ui_type.lower() == "web" else UIType.CLI
    
    # Create and run training UI
    training_ui = TrainingUI(ui_type=ui_type)
    training_ui.initialize_ui()
    training_ui.render()

if __name__ == "__main__":
    main()