"""
Integration tests for UI components
"""

import pytest
from unittest.mock import MagicMock, patch

from ui.common.factory import UIComponentFactory, UIType
from ui.common.adapter import MonitoringAdapter
from ui.common.manager import UIManager, UIMode

class TestComponentIntegration:
    """Integration tests for UI components"""
    
    def test_factory_with_real_components(self):
        """Test factory with real components"""
        # Test creating CLI components
        cli_table = UIComponentFactory.create_component("table", UIType.CLI, "test_table", "Test Table")
        assert cli_table is not None
        assert cli_table.name == "test_table"
        assert cli_table.description == "Test Table"
        
        # Test creating web components
        web_progress = UIComponentFactory.create_component("progress", UIType.WEB, "test_progress", "Test Progress")
        assert web_progress is not None
        assert web_progress.name == "test_progress"
        assert web_progress.description == "Test Progress"
    
    def test_dashboard_with_components(self):
        """Test dashboard with real components"""
        # Create dashboard
        dashboard = UIComponentFactory.create_component("dashboard", UIType.CLI, "test_dashboard", "Test Dashboard")
        assert dashboard is not None
        
        # Create child components
        table = UIComponentFactory.create_component("table", UIType.CLI, "test_table", "Test Table")
        progress = UIComponentFactory.create_component("progress", UIType.CLI, "test_progress", "Test Progress")
        
        # Add components to dashboard
        dashboard.add_widget("table_widget", table, {"row": 0, "col": 0})
        dashboard.add_widget("progress_widget", progress, {"row": 1, "col": 0})
        
        # Update widget data
        table_data = {
            "headers": ["Column 1", "Column 2"],
            "rows": [["Value 1", "Value 2"], ["Value 3", "Value 4"]]
        }
        dashboard.update_widget("table_widget", table_data)
        
        progress_data = {
            "current": 5,
            "total": 10,
            "message": "Processing..."
        }
        dashboard.update_widget("progress_widget", progress_data)
        
        # Check widgets data was properly set
        assert "table_widget" in dashboard.widgets
        assert "progress_widget" in dashboard.widgets
        
        # Ensure the widgets exist in the dashboard
        assert dashboard.widgets["table_widget"]["component"] is table
        assert dashboard.widgets["progress_widget"]["component"] is progress
        
        # Verify table data
        assert table.headers == table_data["headers"]
        assert table.rows == table_data["rows"]
        
        # Verify progress data
        assert progress.current == progress_data["current"]
        assert progress.total == progress_data["total"]
        assert progress.message == progress_data["message"]

class TestMonitoringAdapterIntegration:
    """Integration tests for monitoring adapter"""
    
    def test_adapter_with_real_components(self):
        """Test monitoring adapter with real components"""
        # Create adapter
        adapter = MonitoringAdapter(UIType.CLI)
        
        # Get dashboard
        dashboard = adapter.get_dashboard()
        assert dashboard is not None
        
        # Check dashboard has the expected widgets
        assert "resources" in dashboard.widgets
        assert "pipeline" in dashboard.widgets
        assert "doc_stats" in dashboard.widgets
        assert "alerts" in dashboard.widgets
        
        # Update with real data
        resources = {
            "cpu": {"percent": 50},
            "memory": {"percent": 60, "used_gb": 8, "total_gb": 16},
            "gpu": {
                "0": {
                    "utilization_percent": 70,
                    "memory_used_gb": 6,
                    "memory_total_gb": 8
                }
            }
        }
        adapter.update_resources(resources)
        
        pipeline = {
            "ocr": {"completed": 5, "total": 10, "active": False},
            "json": {"completed": 3, "total": 10, "active": True},
            "correction": {"completed": 0, "total": 10, "active": False}
        }
        adapter.update_pipeline_progress(pipeline)
        
        # Verify resource widget was updated
        resource_widget = dashboard.widgets["resources"]["component"]
        assert isinstance(resource_widget, UIComponentFactory._component_map[UIType.CLI]["chart"])
        
        # Verify pipeline widget was updated
        pipeline_widget = dashboard.widgets["pipeline"]["component"]
        assert isinstance(pipeline_widget, UIComponentFactory._component_map[UIType.CLI]["progress"])
        assert pipeline_widget.current == 8  # Sum of completed steps
        assert pipeline_widget.total == 30   # Sum of total steps
        assert "json" in pipeline_widget.message  # Should mention the active step

class TestUIManagerIntegration:
    """Integration tests for UI manager"""
    
    def test_manager_with_real_adapters(self):
        """Test UI manager with real adapters"""
        # Create manager
        manager = UIManager(UIType.CLI)
        
        # Check initial state
        assert manager.current_mode == UIMode.DASHBOARD
        assert manager.main_nav is not None
        
        # Check adapters
        assert manager.monitoring_adapter is not None
        assert manager.review_adapter is not None
        assert manager.training_adapter is not None
        
        # Test mode switching
        manager.set_mode(UIMode.MONITOR)
        assert manager.current_mode == UIMode.MONITOR
        
        manager.set_mode(UIMode.REVIEW)
        assert manager.current_mode == UIMode.REVIEW
        
        manager.set_mode(UIMode.TRAINING)
        assert manager.current_mode == UIMode.TRAINING
        
        manager.set_mode(UIMode.EXTRACTION)
        assert manager.current_mode == UIMode.EXTRACTION