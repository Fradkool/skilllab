"""
UI Adapters for SkillLab
Provides adapters for integrating UI components with API functionality
"""

from typing import Dict, List, Any, Optional, Callable, Union
import time

from ui.base import UIComponent, DashboardComponent
from ui.common.factory import UIComponentFactory, UIType

class MonitoringAdapter:
    """Adapter for monitoring APIs to UI components"""
    
    def __init__(self, ui_type: UIType):
        """
        Initialize monitoring adapter
        
        Args:
            ui_type: Type of UI (CLI or Web)
        """
        self.ui_type = ui_type
        
        # Create UI components
        self.dashboard = UIComponentFactory.create_component(
            "dashboard", ui_type, "monitoring", "System Monitoring"
        )
        
        # Initialize widgets
        self._init_dashboard()
    
    def _init_dashboard(self) -> None:
        """Initialize dashboard widgets"""
        # Create resource usage widget
        resource_chart = UIComponentFactory.create_component(
            "chart", self.ui_type, "resources", "System Resources"
        )
        
        # Create progress widget
        pipeline_progress = UIComponentFactory.create_component(
            "progress", self.ui_type, "pipeline", "Pipeline Progress"
        )
        
        # Create document stats widget
        doc_stats_table = UIComponentFactory.create_component(
            "table", self.ui_type, "doc_stats", "Document Statistics"
        )
        
        # Create alerts widget
        alerts = UIComponentFactory.create_component(
            "alert", self.ui_type, "alerts", "System Alerts"
        )
        
        # Add widgets to dashboard
        if self.dashboard:
            self.dashboard.add_widget("resources", resource_chart, {"row": 0, "col": 0})
            self.dashboard.add_widget("pipeline", pipeline_progress, {"row": 0, "col": 1})
            self.dashboard.add_widget("doc_stats", doc_stats_table, {"row": 1, "col": 0})
            self.dashboard.add_widget("alerts", alerts, {"row": 1, "col": 1})
    
    def update_resources(self, resource_data: Dict[str, Any]) -> None:
        """
        Update resource usage widget
        
        Args:
            resource_data: Resource usage data from API
        """
        if not self.dashboard:
            return
        
        # Extract data for chart
        labels = ["CPU", "Memory", "GPU Memory", "GPU Util"]
        values = [
            resource_data.get("cpu", {}).get("percent", 0),
            resource_data.get("memory", {}).get("percent", 0),
            0,
            0
        ]
        
        # Add GPU data if available
        if "gpu" in resource_data:
            # Use first GPU device
            gpu_id = next(iter(resource_data["gpu"].keys()), None)
            if gpu_id:
                gpu_data = resource_data["gpu"][gpu_id]
                values[2] = gpu_data.get("memory_used_gb", 0) / gpu_data.get("memory_total_gb", 1) * 100
                values[3] = gpu_data.get("utilization_percent", 0)
        
        # Update chart
        chart_data = {
            "type": "bar",
            "labels": labels,
            "values": values
        }
        
        self.dashboard.update_widget("resources", chart_data)
    
    def update_pipeline_progress(self, progress_data: Dict[str, Any]) -> None:
        """
        Update pipeline progress widget
        
        Args:
            progress_data: Pipeline progress data from API
        """
        if not self.dashboard:
            return
        
        # Calculate overall progress
        total_steps = 0
        completed_steps = 0
        
        for step, data in progress_data.items():
            total = data.get("total", 0)
            completed = data.get("completed", 0)
            
            if total > 0:
                total_steps += total
                completed_steps += completed
            
            # Check for active step
            if data.get("active", False):
                current_step = step
        
        # Calculate percentage
        progress_pct = (completed_steps / total_steps * 100) if total_steps > 0 else 0
        
        # Update progress component
        progress_info = {
            "current": completed_steps,
            "total": total_steps,
            "message": f"Processing: {current_step if 'current_step' in locals() else 'None'}"
        }
        
        self.dashboard.update_widget("pipeline", progress_info)
    
    def update_document_stats(self, stats_data: Dict[str, Any]) -> None:
        """
        Update document statistics widget
        
        Args:
            stats_data: Document statistics from API
        """
        if not self.dashboard:
            return
        
        # Create table data
        headers = ["Metric", "Value"]
        rows = [
            ["Total Documents", stats_data.get("total_documents", 0)],
            ["Processed Documents", stats_data.get("processed_documents", 0)],
            ["Flagged for Review", stats_data.get("flagged_documents", 0)],
            ["Reviewed Documents", stats_data.get("reviewed_documents", 0)],
            ["Average OCR Confidence", f"{stats_data.get('average_ocr_confidence', 0):.1f}%"],
            ["Average JSON Confidence", f"{stats_data.get('average_json_confidence', 0):.1f}%"]
        ]
        
        table_data = {
            "headers": headers,
            "rows": rows
        }
        
        self.dashboard.update_widget("doc_stats", table_data)
    
    def add_alert(self, alert_type: str, message: str) -> None:
        """
        Add an alert to the dashboard
        
        Args:
            alert_type: Type of alert (info, success, warning, error)
            message: Alert message
        """
        if not self.dashboard:
            return
        
        alert_data = {
            "type": alert_type,
            "message": message
        }
        
        self.dashboard.update_widget("alerts", alert_data)
    
    def get_dashboard(self) -> Optional[DashboardComponent]:
        """
        Get the monitoring dashboard
        
        Returns:
            Dashboard component
        """
        return self.dashboard
    
    def refresh(self) -> None:
        """Refresh the dashboard with latest API data"""
        from api.monitoring import (
            get_system_resources,
            get_pipeline_progress,
            get_document_processing_stats
        )
        
        # Get data from APIs
        resources = get_system_resources()
        pipeline = get_pipeline_progress()
        doc_stats = get_document_processing_stats()
        
        # Update dashboard
        self.update_resources(resources)
        self.update_pipeline_progress(pipeline)
        self.update_document_stats(doc_stats)

class ReviewAdapter:
    """Adapter for review APIs to UI components"""
    
    def __init__(self, ui_type: UIType):
        """
        Initialize review adapter
        
        Args:
            ui_type: Type of UI (CLI or Web)
        """
        self.ui_type = ui_type
        
        # Create UI components
        self.dashboard = UIComponentFactory.create_component(
            "dashboard", ui_type, "review", "Document Review"
        )
        
        self.document_form = UIComponentFactory.create_component(
            "form", ui_type, "document_form", "Document Details"
        )
        
        self.document_nav = UIComponentFactory.create_component(
            "navigation", ui_type, "document_nav", "Document Navigation"
        )
        
        # Initialize widgets
        self._init_dashboard()
    
    def _init_dashboard(self) -> None:
        """Initialize dashboard widgets"""
        # Create queue table widget
        queue_table = UIComponentFactory.create_component(
            "table", self.ui_type, "queue", "Review Queue"
        )
        
        # Create statistics widget
        stats_chart = UIComponentFactory.create_component(
            "chart", self.ui_type, "stats", "Review Statistics"
        )
        
        # Add document form to dashboard
        # Add widgets to dashboard
        if self.dashboard:
            self.dashboard.add_widget("queue", queue_table, {"row": 0, "col": 0, "colspan": 2})
            self.dashboard.add_widget("stats", stats_chart, {"row": 1, "col": 0})
            self.dashboard.add_widget("document_form", self.document_form, {"row": 1, "col": 1})
            self.dashboard.add_widget("document_nav", self.document_nav, {"row": 2, "col": 0, "colspan": 2})
    
    def update_queue(self, queue_data: List[Dict[str, Any]]) -> None:
        """
        Update review queue widget
        
        Args:
            queue_data: Review queue data from API
        """
        if not self.dashboard:
            return
        
        # Create table headers
        headers = ["ID", "Filename", "OCR Conf.", "JSON Conf.", "Issue Type", "Status"]
        
        # Create table rows
        rows = []
        for doc in queue_data:
            issue_types = ", ".join([issue["type"] for issue in doc.get("issues", [])])
            
            rows.append([
                doc.get("id", ""),
                doc.get("filename", ""),
                f"{doc.get('ocr_confidence', 0):.1f}%",
                f"{doc.get('json_confidence', 0):.1f}%",
                issue_types,
                doc.get("review_status", "pending")
            ])
        
        table_data = {
            "headers": headers,
            "rows": rows
        }
        
        self.dashboard.update_widget("queue", table_data)
    
    def update_stats(self, stats_data: Dict[str, Any]) -> None:
        """
        Update review statistics widget
        
        Args:
            stats_data: Review statistics from API
        """
        if not self.dashboard:
            return
        
        # Extract issue statistics
        issue_types = []
        issue_counts = []
        
        for issue_type, count in stats_data.get("issue_stats", {}).items():
            issue_types.append(issue_type)
            issue_counts.append(count)
        
        # Create chart data
        chart_data = {
            "type": "pie",
            "labels": issue_types,
            "values": issue_counts,
            "title": "Issues by Type"
        }
        
        self.dashboard.update_widget("stats", chart_data)
    
    def update_document_form(self, document_data: Dict[str, Any]) -> None:
        """
        Update document form widget
        
        Args:
            document_data: Document data from API
        """
        if not self.document_form:
            return
        
        # Create form fields based on document data
        fields = {
            "id": {
                "type": "text",
                "label": "Document ID",
                "required": False,
                "default": document_data.get("id", "")
            },
            "filename": {
                "type": "text",
                "label": "Filename",
                "required": False,
                "default": document_data.get("filename", "")
            },
            "name": {
                "type": "text",
                "label": "Name",
                "required": True,
                "default": document_data.get("json_data", {}).get("Name", "")
            },
            "email": {
                "type": "text",
                "label": "Email",
                "required": True,
                "default": document_data.get("json_data", {}).get("Email", "")
            },
            "phone": {
                "type": "text",
                "label": "Phone",
                "required": True,
                "default": document_data.get("json_data", {}).get("Phone", "")
            },
            "position": {
                "type": "text",
                "label": "Current Position",
                "required": False,
                "default": document_data.get("json_data", {}).get("Current_Position", "")
            },
            "skills": {
                "type": "textarea",
                "label": "Skills (comma separated)",
                "required": False,
                "default": ", ".join(document_data.get("json_data", {}).get("Skills", []))
            }
        }
        
        # Add any issues as read-only fields
        issues = document_data.get("issues", [])
        if issues:
            for i, issue in enumerate(issues):
                fields[f"issue_{i}"] = {
                    "type": "text",
                    "label": f"Issue: {issue.get('type', '')}",
                    "required": False,
                    "default": issue.get("details", "")
                }
        
        form_data = {
            "fields": fields,
            "submit_label": "Save Changes",
            "show_reset": True
        }
        
        # Update form
        self.document_form.render(form_data)
    
    def update_document_nav(self, document_id: str, queue_data: List[Dict[str, Any]]) -> None:
        """
        Update document navigation widget
        
        Args:
            document_id: Current document ID
            queue_data: Review queue data from API
        """
        if not self.document_nav:
            return
        
        # Create navigation items
        items = []
        for i, doc in enumerate(queue_data):
            doc_id = doc.get("id", "")
            filename = doc.get("filename", "")
            
            items.append({
                "id": doc_id,
                "label": f"{i+1}. {filename}",
                "url": None,
                "action": lambda: self.load_document(doc_id),
                "parent": None
            })
        
        nav_data = {
            "items": items,
            "active_id": document_id
        }
        
        # Update navigation
        self.document_nav.render(nav_data)
    
    def load_document(self, document_id: str) -> Dict[str, Any]:
        """
        Load document details
        
        Args:
            document_id: Document ID
            
        Returns:
            Document data
        """
        from api.review import get_document_details
        
        # Get document details from API
        document = get_document_details(document_id)
        
        # Update UI
        self.update_document_form(document)
        
        return document
    
    def save_document(self, document_id: str, form_values: Dict[str, Any]) -> bool:
        """
        Save document changes
        
        Args:
            document_id: Document ID
            form_values: Form values
            
        Returns:
            True if saved successfully, False otherwise
        """
        from api.review import save_review_feedback
        
        # Convert form values to document JSON format
        name = form_values.get("name", "")
        email = form_values.get("email", "")
        phone = form_values.get("phone", "")
        position = form_values.get("position", "")
        
        # Parse skills
        skills_str = form_values.get("skills", "")
        skills = [skill.strip() for skill in skills_str.split(",") if skill.strip()]
        
        # Create JSON data
        json_data = {
            "Name": name,
            "Email": email,
            "Phone": phone,
            "Current_Position": position,
            "Skills": skills,
            "Experience": []  # Experience is not editable in this form
        }
        
        # Save to API
        return save_review_feedback(
            document_id=document_id,
            status="approved",
            json_data=json_data,
            corrections=form_values,
            reason="",
            reviewer="UI"
        )
    
    def get_dashboard(self) -> Optional[DashboardComponent]:
        """
        Get the review dashboard
        
        Returns:
            Dashboard component
        """
        return self.dashboard
    
    def refresh(self) -> None:
        """Refresh the dashboard with latest API data"""
        from api.review import get_review_queue, get_dashboard_stats
        
        # Get data from APIs
        queue = get_review_queue()
        stats = get_dashboard_stats()
        
        # Update dashboard
        self.update_queue(queue)
        self.update_stats(stats)

class TrainingAdapter:
    """Adapter for training APIs to UI components"""
    
    def __init__(self, ui_type: UIType):
        """
        Initialize training adapter
        
        Args:
            ui_type: Type of UI (CLI or Web)
        """
        self.ui_type = ui_type
        
        # Create UI components
        self.dashboard = UIComponentFactory.create_component(
            "dashboard", ui_type, "training", "Model Training"
        )
        
        self.training_form = UIComponentFactory.create_component(
            "form", ui_type, "training_form", "Training Configuration"
        )
        
        # Initialize widgets
        self._init_dashboard()
    
    def _init_dashboard(self) -> None:
        """Initialize dashboard widgets"""
        # Create progress widget
        progress = UIComponentFactory.create_component(
            "progress", self.ui_type, "training_progress", "Training Progress"
        )
        
        # Create metrics widget
        metrics_chart = UIComponentFactory.create_component(
            "chart", self.ui_type, "training_metrics", "Training Metrics"
        )
        
        # Create dataset stats widget
        dataset_table = UIComponentFactory.create_component(
            "table", self.ui_type, "dataset_stats", "Dataset Statistics"
        )
        
        # Create alert widget
        alerts = UIComponentFactory.create_component(
            "alert", self.ui_type, "training_alerts", "Training Alerts"
        )
        
        # Add widgets to dashboard
        if self.dashboard:
            self.dashboard.add_widget("training_form", self.training_form, {"row": 0, "col": 0})
            self.dashboard.add_widget("training_progress", progress, {"row": 0, "col": 1})
            self.dashboard.add_widget("training_metrics", metrics_chart, {"row": 1, "col": 0})
            self.dashboard.add_widget("dataset_stats", dataset_table, {"row": 1, "col": 1})
            self.dashboard.add_widget("training_alerts", alerts, {"row": 2, "col": 0, "colspan": 2})
    
    def init_training_form(self) -> None:
        """Initialize training configuration form"""
        if not self.training_form:
            return
        
        # Create form fields
        fields = {
            "epochs": {
                "type": "number",
                "label": "Training Epochs",
                "required": True,
                "default": 5
            },
            "batch_size": {
                "type": "number",
                "label": "Batch Size",
                "required": True,
                "default": 4
            },
            "learning_rate": {
                "type": "number",
                "label": "Learning Rate",
                "required": True,
                "default": 0.00005
            },
            "pretrained_model": {
                "type": "select",
                "label": "Pretrained Model",
                "required": True,
                "default": "naver-clova-ix/donut-base",
                "options": [
                    "naver-clova-ix/donut-base",
                    "naver-clova-ix/donut-proto",
                    "Custom Model"
                ]
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
            "submit_label": "Start Training",
            "show_reset": True
        }
        
        # Update form
        self.training_form.render(form_data)
    
    def update_progress(self, progress_data: Dict[str, Any]) -> None:
        """
        Update training progress widget
        
        Args:
            progress_data: Training progress data from API
        """
        if not self.dashboard:
            return
        
        # Extract progress information
        current_epoch = progress_data.get("current_epoch", 0)
        total_epochs = progress_data.get("total_epochs", 1)
        progress_pct = progress_data.get("progress", 0)
        
        # Create progress data
        progress_info = {
            "current": current_epoch,
            "total": total_epochs,
            "message": f"Training: Epoch {current_epoch}/{total_epochs} ({progress_pct:.1f}%)"
        }
        
        self.dashboard.update_widget("training_progress", progress_info)
    
    def update_metrics(self, metrics_data: Dict[str, Any]) -> None:
        """
        Update training metrics widget
        
        Args:
            metrics_data: Training metrics data from API
        """
        if not self.dashboard:
            return
        
        # Extract metrics information
        epochs = metrics_data.get("epochs", [])
        train_loss = metrics_data.get("train_loss", [])
        val_loss = metrics_data.get("val_loss", [])
        
        # Create chart data
        chart_data = {
            "type": "line",
            "dataframe": {
                "Epoch": epochs,
                "Training Loss": train_loss,
                "Validation Loss": val_loss
            },
            "options": {
                "title": "Training Progress",
                "x_label": "Epoch",
                "y_label": "Loss"
            }
        }
        
        self.dashboard.update_widget("training_metrics", chart_data)
    
    def update_dataset_stats(self, dataset_data: Dict[str, Any]) -> None:
        """
        Update dataset statistics widget
        
        Args:
            dataset_data: Dataset statistics from API
        """
        if not self.dashboard:
            return
        
        # Create table headers
        headers = ["Metric", "Value"]
        
        # Create table rows
        rows = [
            ["Total Samples", dataset_data.get("total_samples", 0)],
            ["Training Samples", dataset_data.get("train_samples", 0)],
            ["Validation Samples", dataset_data.get("val_samples", 0)],
            ["Sample Split Ratio", f"{dataset_data.get('train_val_split', 0.8) * 100:.0f}%"],
            ["Multi-page Samples", dataset_data.get("multi_page_samples", 0)],
            ["Single-page Samples", dataset_data.get("single_page_samples", 0)]
        ]
        
        table_data = {
            "headers": headers,
            "rows": rows
        }
        
        self.dashboard.update_widget("dataset_stats", table_data)
    
    def add_alert(self, alert_type: str, message: str) -> None:
        """
        Add an alert to the dashboard
        
        Args:
            alert_type: Type of alert (info, success, warning, error)
            message: Alert message
        """
        if not self.dashboard:
            return
        
        alert_data = {
            "type": alert_type,
            "message": message
        }
        
        self.dashboard.update_widget("training_alerts", alert_data)
    
    def start_training(self, form_values: Dict[str, Any]) -> bool:
        """
        Start model training with form values
        
        Args:
            form_values: Form values
            
        Returns:
            True if training started successfully, False otherwise
        """
        from api.training import run_training_pipeline
        
        try:
            # Extract form values
            epochs = int(form_values.get("epochs", 5))
            batch_size = int(form_values.get("batch_size", 4))
            learning_rate = float(form_values.get("learning_rate", 0.00005))
            pretrained_model = form_values.get("pretrained_model", "naver-clova-ix/donut-base")
            gpu_monitor = bool(form_values.get("gpu_monitor", True))
            
            # Add info alert
            self.add_alert("info", "Starting training pipeline...")
            
            # Start training in a separate thread to avoid blocking UI
            import threading
            
            def training_thread():
                try:
                    # Run training pipeline
                    result = run_training_pipeline(
                        start_with_dataset=True,
                        epochs=epochs,
                        batch_size=batch_size,
                        enable_gpu_monitoring=gpu_monitor
                    )
                    
                    # Check result
                    if result.get("status") == "completed":
                        self.add_alert("success", "Training completed successfully!")
                        
                        # Get final metrics
                        training_results = result.get("training", {})
                        eval_metrics = training_results.get("eval_metrics", {})
                        eval_loss = eval_metrics.get("eval_loss", "N/A")
                        
                        self.add_alert("info", f"Final evaluation loss: {eval_loss}")
                    else:
                        error_msg = result.get("training_error", "Unknown error")
                        self.add_alert("error", f"Training failed: {error_msg}")
                except Exception as e:
                    self.add_alert("error", f"Error during training: {str(e)}")
            
            # Start thread
            thread = threading.Thread(target=training_thread)
            thread.daemon = True
            thread.start()
            
            return True
        except Exception as e:
            self.add_alert("error", f"Error starting training: {str(e)}")
            return False
    
    def get_dashboard(self) -> Optional[DashboardComponent]:
        """
        Get the training dashboard
        
        Returns:
            Dashboard component
        """
        return self.dashboard
    
    def refresh(self) -> None:
        """Refresh the dashboard with latest API data"""
        # Initialize training form
        self.init_training_form()
        
        # Try to get training progress from API if available
        try:
            from api.training import get_training_progress
            progress = get_training_progress()
            
            if progress:
                self.update_progress(progress)
                
                # Update metrics if available
                if "metrics" in progress:
                    self.update_metrics(progress["metrics"])
                
                # Update dataset stats if available
                if "dataset" in progress:
                    self.update_dataset_stats(progress["dataset"])
        except (ImportError, Exception):
            # Training API might not be available yet
            pass