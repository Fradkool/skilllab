"""
UI Manager for SkillLab
Provides a central manager for all UI operations
"""

import os
import sys
from typing import Dict, Any, Optional, Callable, List
from enum import Enum

from ui.factory import UIComponentFactory, UIType
from ui.adapters import MonitoringAdapter, ReviewAdapter, TrainingAdapter

class UIMode(Enum):
    """UI mode enum (mode to display)"""
    DASHBOARD = "dashboard"
    MONITOR = "monitor"
    REVIEW = "review"
    TRAINING = "training"
    EXTRACTION = "extraction"

class UIManager:
    """Central manager for UI components and interactions"""
    
    def __init__(self, ui_type: UIType = UIType.CLI):
        """
        Initialize UI manager
        
        Args:
            ui_type: Type of UI (CLI or Web)
        """
        self.ui_type = ui_type
        self.current_mode = UIMode.DASHBOARD
        
        # Create adapters
        self.monitoring_adapter = MonitoringAdapter(ui_type)
        self.review_adapter = ReviewAdapter(ui_type)
        self.training_adapter = TrainingAdapter(ui_type)
        
        # Create navigation component
        self.main_nav = UIComponentFactory.create_component(
            "navigation", ui_type, "main_navigation", "SkillLab Navigation"
        )
        
        # Configure navigation
        self._configure_navigation()
    
    def _configure_navigation(self) -> None:
        """Configure main navigation"""
        if not self.main_nav:
            return
        
        # Add navigation items
        self.main_nav.add_item("dashboard", "Dashboard")
        self.main_nav.add_item("monitor", "Monitoring")
        self.main_nav.add_item("review", "Document Review")
        self.main_nav.add_item("training", "Model Training")
        self.main_nav.add_item("extraction", "Extraction")
        
        # Set active item
        self.main_nav.set_active("dashboard")
    
    def set_mode(self, mode: UIMode) -> None:
        """
        Set UI mode
        
        Args:
            mode: UI mode to set
        """
        self.current_mode = mode
        
        # Update navigation
        if self.main_nav:
            self.main_nav.set_active(mode.value)
    
    def render_ui(self) -> None:
        """Render the UI based on current mode"""
        # First render navigation
        if self.main_nav:
            self.main_nav.render()
        
        # Render content based on mode
        if self.current_mode == UIMode.DASHBOARD:
            self._render_dashboard()
        elif self.current_mode == UIMode.MONITOR:
            self._render_monitoring()
        elif self.current_mode == UIMode.REVIEW:
            self._render_review()
        elif self.current_mode == UIMode.TRAINING:
            self._render_training()
        elif self.current_mode == UIMode.EXTRACTION:
            self._render_extraction()
    
    def _render_dashboard(self) -> None:
        """Render dashboard"""
        # Create dashboard component if needed
        dashboard = UIComponentFactory.create_component(
            "dashboard", self.ui_type, "main_dashboard", "SkillLab Dashboard"
        )
        
        if not dashboard:
            return
        
        # Get widgets from other adapters
        system_stats = UIComponentFactory.create_component(
            "table", self.ui_type, "system_stats", "System Statistics"
        )
        
        review_stats = UIComponentFactory.create_component(
            "table", self.ui_type, "review_stats", "Review Statistics"
        )
        
        training_progress = UIComponentFactory.create_component(
            "progress", self.ui_type, "training_progress", "Training Progress"
        )
        
        # Add widgets to dashboard
        dashboard.add_widget("system_stats", system_stats, {"row": 0, "col": 0})
        dashboard.add_widget("review_stats", review_stats, {"row": 0, "col": 1})
        dashboard.add_widget("training_progress", training_progress, {"row": 1, "col": 0, "colspan": 2})
        
        # Get system statistics
        from api.monitoring import get_document_processing_stats
        
        try:
            doc_stats = get_document_processing_stats()
            
            # Update system stats widget
            headers = ["Metric", "Value"]
            rows = [
                ["Total Documents", doc_stats.get("total_documents", 0)],
                ["Processed Documents", doc_stats.get("processed_documents", 0)],
                ["Average OCR Confidence", f"{doc_stats.get('average_ocr_confidence', 0):.1f}%"],
                ["Average JSON Confidence", f"{doc_stats.get('average_json_confidence', 0):.1f}%"]
            ]
            
            for step, time in doc_stats.get("average_processing_times", {}).items():
                rows.append([f"{step.capitalize()} Processing Time", f"{time:.2f}s"])
            
            system_stats_data = {
                "headers": headers,
                "rows": rows
            }
            
            dashboard.update_widget("system_stats", system_stats_data)
        except Exception:
            # API might not be available
            pass
        
        # Get review statistics
        from api.review import get_dashboard_stats
        
        try:
            review_stats_data = get_dashboard_stats()
            
            # Update review stats widget
            headers = ["Metric", "Value"]
            rows = [
                ["Total Documents", review_stats_data.get("total_documents", 0)],
                ["Flagged for Review", review_stats_data.get("flagged_documents", 0)],
                ["Reviewed Documents", review_stats_data.get("reviewed_documents", 0)],
                ["Pending Review", review_stats_data.get("flagged_documents", 0) - review_stats_data.get("reviewed_documents", 0)]
            ]
            
            # Add issue stats
            for issue_type, count in review_stats_data.get("issue_stats", {}).items():
                rows.append([f"Issue: {issue_type}", count])
            
            review_stats_table = {
                "headers": headers,
                "rows": rows
            }
            
            dashboard.update_widget("review_stats", review_stats_table)
        except Exception:
            # API might not be available
            pass
        
        # Get training progress
        try:
            from api.training import get_training_progress
            
            training_data = get_training_progress()
            
            if training_data:
                # Update training progress widget
                current_epoch = training_data.get("current_epoch", 0)
                total_epochs = training_data.get("total_epochs", 1)
                progress_pct = training_data.get("progress", 0)
                
                progress_info = {
                    "current": current_epoch,
                    "total": total_epochs,
                    "message": f"Training: Epoch {current_epoch}/{total_epochs} ({progress_pct:.1f}%)"
                }
                
                dashboard.update_widget("training_progress", progress_info)
        except (ImportError, Exception):
            # Training API might not be available yet
            pass
        
        # Render dashboard
        dashboard.render()
    
    def _render_monitoring(self) -> None:
        """Render monitoring dashboard"""
        # Refresh monitoring data
        self.monitoring_adapter.refresh()
        
        # Get and render dashboard
        monitoring_dashboard = self.monitoring_adapter.get_dashboard()
        if monitoring_dashboard:
            monitoring_dashboard.render()
    
    def _render_review(self) -> None:
        """Render review dashboard"""
        # Refresh review data
        self.review_adapter.refresh()
        
        # Get and render dashboard
        review_dashboard = self.review_adapter.get_dashboard()
        if review_dashboard:
            review_dashboard.render()
    
    def _render_training(self) -> None:
        """Render training dashboard"""
        # Refresh training data
        self.training_adapter.refresh()
        
        # Get and render dashboard
        training_dashboard = self.training_adapter.get_dashboard()
        if training_dashboard:
            training_dashboard.render()
    
    def _render_extraction(self) -> None:
        """Render extraction interface (minimal implementation)"""
        # Create a form for extraction configuration
        extraction_form = UIComponentFactory.create_component(
            "form", self.ui_type, "extraction_form", "Extraction Configuration"
        )
        
        if not extraction_form:
            return
        
        # Create form fields
        fields = {
            "input_dir": {
                "type": "text",
                "label": "Input Directory",
                "required": True,
                "default": "data/input"
            },
            "output_dir": {
                "type": "text",
                "label": "Output Directory",
                "required": True,
                "default": "data/output"
            },
            "limit": {
                "type": "number",
                "label": "Document Limit",
                "required": False,
                "default": 0
            },
            "start_step": {
                "type": "select",
                "label": "Start Step",
                "required": True,
                "default": "ocr",
                "options": ["ocr", "json", "correction"]
            },
            "end_step": {
                "type": "select",
                "label": "End Step",
                "required": True,
                "default": "correction",
                "options": ["ocr", "json", "correction"]
            },
            "gpu_monitor": {
                "type": "boolean",
                "label": "Enable GPU Monitoring",
                "required": False,
                "default": True
            }
        }
        
        form_data = {
            "fields": fields,
            "submit_label": "Start Extraction",
            "show_reset": True
        }
        
        # Render form
        extraction_form.render(form_data)
        
        # Check if form is submitted
        if hasattr(extraction_form, 'is_submitted') and extraction_form.is_submitted():
            # Get form values
            form_values = extraction_form.get_values()
            
            # Start extraction in a separate thread
            import threading
            
            def extraction_thread():
                try:
                    from api.extraction import run_full_extraction_pipeline
                    
                    # Run extraction pipeline
                    result = run_full_extraction_pipeline(
                        input_dir=form_values.get("input_dir", "data/input"),
                        output_dir=form_values.get("output_dir", "data/output"),
                        limit=form_values.get("limit", None)
                    )
                    
                    # Check result
                    if result:
                        # Create success alert
                        alert = UIComponentFactory.create_component(
                            "alert", self.ui_type, "extraction_alert", "Extraction Alert"
                        )
                        
                        if alert:
                            alert.success(f"Extraction completed successfully! Processed {result.get('documents_processed', 0)} documents.")
                except Exception as e:
                    # Create error alert
                    alert = UIComponentFactory.create_component(
                        "alert", self.ui_type, "extraction_alert", "Extraction Alert"
                    )
                    
                    if alert:
                        alert.error(f"Error during extraction: {str(e)}")
            
            # Start thread
            thread = threading.Thread(target=extraction_thread)
            thread.daemon = True
            thread.start()
            
            # Create info alert
            alert = UIComponentFactory.create_component(
                "alert", self.ui_type, "extraction_alert", "Extraction Alert"
            )
            
            if alert:
                alert.info("Extraction started in the background. Check the monitoring dashboard for progress.")

# Create singletons
_cli_manager = None
_web_manager = None

def get_ui_manager(ui_type: UIType = UIType.CLI) -> UIManager:
    """
    Get UI manager singleton
    
    Args:
        ui_type: Type of UI (CLI or Web)
        
    Returns:
        UI manager instance
    """
    global _cli_manager, _web_manager
    
    if ui_type == UIType.CLI:
        if _cli_manager is None:
            _cli_manager = UIManager(ui_type)
        return _cli_manager
    else:
        if _web_manager is None:
            _web_manager = UIManager(ui_type)
        return _web_manager