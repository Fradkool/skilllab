"""
Tests for UI adapters
"""

import pytest
from unittest.mock import MagicMock, patch, call

from ui.common.adapter import MonitoringAdapter, ReviewAdapter, TrainingAdapter
from ui.common.factory import UIType

class TestMonitoringAdapter:
    """Tests for MonitoringAdapter"""
    
    def test_init(self):
        """Test initialization"""
        # Create mock dashboard
        with patch('ui.common.adapter.UIComponentFactory.create_component') as mock_create_component:
            # Configure the mock to return different components
            dashboard_mock = MagicMock()
            mock_create_component.side_effect = [
                dashboard_mock,  # dashboard
                MagicMock(),     # resource_chart
                MagicMock(),     # pipeline_progress
                MagicMock(),     # doc_stats_table
                MagicMock()      # alerts
            ]
            
            # Create adapter
            adapter = MonitoringAdapter(UIType.CLI)
            
            # Verify the adapter was initialized correctly
            assert adapter.ui_type == UIType.CLI
            assert adapter.dashboard == dashboard_mock
            
            # Verify the components were created
            assert mock_create_component.call_count == 5
            
            # Verify the dashboard was initialized with widgets
            assert dashboard_mock.add_widget.call_count == 4
    
    def test_update_resources(self):
        """Test updating resources"""
        # Create mock dashboard
        with patch('ui.common.adapter.UIComponentFactory.create_component') as mock_create_component:
            # Configure the mock
            dashboard_mock = MagicMock()
            mock_create_component.side_effect = [
                dashboard_mock,  # dashboard
                MagicMock(),     # resource_chart
                MagicMock(),     # pipeline_progress
                MagicMock(),     # doc_stats_table
                MagicMock()      # alerts
            ]
            
            # Create adapter
            adapter = MonitoringAdapter(UIType.CLI)
            
            # Create resource data
            resource_data = {
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
            
            # Update resources
            adapter.update_resources(resource_data)
            
            # Verify the dashboard was updated
            dashboard_mock.update_widget.assert_called_once()
            assert dashboard_mock.update_widget.call_args[0][0] == "resources"
            assert dashboard_mock.update_widget.call_args[0][1]["type"] == "bar"
            assert dashboard_mock.update_widget.call_args[0][1]["labels"] == ["CPU", "Memory", "GPU Memory", "GPU Util"]
            assert dashboard_mock.update_widget.call_args[0][1]["values"] == [50, 60, 75, 70]
    
    def test_update_pipeline_progress(self):
        """Test updating pipeline progress"""
        # Create mock dashboard
        with patch('ui.common.adapter.UIComponentFactory.create_component') as mock_create_component:
            # Configure the mock
            dashboard_mock = MagicMock()
            mock_create_component.side_effect = [
                dashboard_mock,  # dashboard
                MagicMock(),     # resource_chart
                MagicMock(),     # pipeline_progress
                MagicMock(),     # doc_stats_table
                MagicMock()      # alerts
            ]
            
            # Create adapter
            adapter = MonitoringAdapter(UIType.CLI)
            
            # Create progress data
            progress_data = {
                "ocr": {"completed": 5, "total": 10, "active": False},
                "json": {"completed": 3, "total": 10, "active": True},
                "correction": {"completed": 0, "total": 10, "active": False}
            }
            
            # Update progress
            adapter.update_pipeline_progress(progress_data)
            
            # Verify the dashboard was updated
            dashboard_mock.update_widget.assert_called_once()
            assert dashboard_mock.update_widget.call_args[0][0] == "pipeline"
            assert dashboard_mock.update_widget.call_args[0][1]["current"] == 8
            assert dashboard_mock.update_widget.call_args[0][1]["total"] == 30
            assert "json" in dashboard_mock.update_widget.call_args[0][1]["message"]
    
    def test_refresh(self):
        """Test refreshing the adapter"""
        # Create mock functions
        with patch('ui.common.adapter.UIComponentFactory.create_component') as mock_create_component, \
             patch('ui.common.adapter.get_system_resources') as mock_get_resources, \
             patch('ui.common.adapter.get_pipeline_progress') as mock_get_progress, \
             patch('ui.common.adapter.get_document_processing_stats') as mock_get_stats, \
             patch('ui.common.adapter.MonitoringAdapter.update_resources') as mock_update_resources, \
             patch('ui.common.adapter.MonitoringAdapter.update_pipeline_progress') as mock_update_progress, \
             patch('ui.common.adapter.MonitoringAdapter.update_document_stats') as mock_update_stats:
            
            # Configure mocks
            dashboard_mock = MagicMock()
            mock_create_component.side_effect = [
                dashboard_mock,  # dashboard
                MagicMock(),     # resource_chart
                MagicMock(),     # pipeline_progress
                MagicMock(),     # doc_stats_table
                MagicMock()      # alerts
            ]
            
            # Mock API responses
            mock_get_resources.return_value = {"cpu": {"percent": 50}}
            mock_get_progress.return_value = {"ocr": {"completed": 5, "total": 10}}
            mock_get_stats.return_value = {"total_documents": 100}
            
            # Create adapter
            adapter = MonitoringAdapter(UIType.CLI)
            
            # Refresh adapter
            adapter.refresh()
            
            # Verify API calls
            mock_get_resources.assert_called_once()
            mock_get_progress.assert_called_once()
            mock_get_stats.assert_called_once()
            
            # Verify update calls
            mock_update_resources.assert_called_once_with({"cpu": {"percent": 50}})
            mock_update_progress.assert_called_once_with({"ocr": {"completed": 5, "total": 10}})
            mock_update_stats.assert_called_once_with({"total_documents": 100})

class TestReviewAdapter:
    """Tests for ReviewAdapter"""
    
    def test_init(self):
        """Test initialization"""
        # Create mock components
        with patch('ui.common.adapter.UIComponentFactory.create_component') as mock_create_component:
            # Configure mocks
            dashboard_mock = MagicMock()
            form_mock = MagicMock()
            nav_mock = MagicMock()
            
            mock_create_component.side_effect = [
                dashboard_mock,  # dashboard
                form_mock,       # document_form
                nav_mock         # document_nav
            ]
            
            # Create adapter
            adapter = ReviewAdapter(UIType.WEB)
            
            # Verify initialization
            assert adapter.ui_type == UIType.WEB
            assert adapter.dashboard == dashboard_mock
            assert adapter.document_form == form_mock
            assert adapter.document_nav == nav_mock
            
            # Verify _init_dashboard was called
            assert dashboard_mock.add_widget.call_count >= 3
    
    def test_update_queue(self):
        """Test updating review queue"""
        # Create mock components
        with patch('ui.common.adapter.UIComponentFactory.create_component') as mock_create_component:
            # Configure mocks
            dashboard_mock = MagicMock()
            mock_create_component.side_effect = [
                dashboard_mock,  # dashboard
                MagicMock(),     # document_form
                MagicMock(),     # document_nav
                MagicMock(),     # queue
                MagicMock(),     # stats
            ]
            
            # Create adapter
            adapter = ReviewAdapter(UIType.WEB)
            
            # Create queue data
            queue_data = [
                {
                    "id": "doc1",
                    "filename": "resume1.pdf",
                    "ocr_confidence": 85,
                    "json_confidence": 75,
                    "issues": [{"type": "missing_contact"}],
                    "review_status": "pending"
                },
                {
                    "id": "doc2",
                    "filename": "resume2.pdf",
                    "ocr_confidence": 90,
                    "json_confidence": 80,
                    "issues": [{"type": "low_ocr_confidence"}],
                    "review_status": "approved"
                }
            ]
            
            # Update queue
            adapter.update_queue(queue_data)
            
            # Verify dashboard update
            dashboard_mock.update_widget.assert_called_once()
            assert dashboard_mock.update_widget.call_args[0][0] == "queue"
            assert "headers" in dashboard_mock.update_widget.call_args[0][1]
            assert "rows" in dashboard_mock.update_widget.call_args[0][1]
            assert len(dashboard_mock.update_widget.call_args[0][1]["rows"]) == 2

class TestTrainingAdapter:
    """Tests for TrainingAdapter"""
    
    def test_init(self):
        """Test initialization"""
        # Create mock components
        with patch('ui.common.adapter.UIComponentFactory.create_component') as mock_create_component:
            # Configure mocks
            dashboard_mock = MagicMock()
            form_mock = MagicMock()
            
            mock_create_component.side_effect = [
                dashboard_mock,  # dashboard
                form_mock,       # training_form
                MagicMock(),     # progress
                MagicMock(),     # metrics_chart
                MagicMock(),     # dataset_table
                MagicMock()      # alerts
            ]
            
            # Create adapter
            adapter = TrainingAdapter(UIType.CLI)
            
            # Verify initialization
            assert adapter.ui_type == UIType.CLI
            assert adapter.dashboard == dashboard_mock
            assert adapter.training_form == form_mock
            
            # Verify _init_dashboard was called
            assert dashboard_mock.add_widget.call_count >= 4
    
    def test_update_progress(self):
        """Test updating training progress"""
        # Create mock components
        with patch('ui.common.adapter.UIComponentFactory.create_component') as mock_create_component:
            # Configure mocks
            dashboard_mock = MagicMock()
            mock_create_component.side_effect = [
                dashboard_mock,  # dashboard
                MagicMock(),     # training_form
                MagicMock(),     # progress
                MagicMock(),     # metrics_chart
                MagicMock(),     # dataset_table
                MagicMock()      # alerts
            ]
            
            # Create adapter
            adapter = TrainingAdapter(UIType.CLI)
            
            # Create progress data
            progress_data = {
                "current_epoch": 3,
                "total_epochs": 5,
                "progress": 60.0
            }
            
            # Update progress
            adapter.update_progress(progress_data)
            
            # Verify dashboard update
            dashboard_mock.update_widget.assert_called_once()
            assert dashboard_mock.update_widget.call_args[0][0] == "training_progress"
            assert dashboard_mock.update_widget.call_args[0][1]["current"] == 3
            assert dashboard_mock.update_widget.call_args[0][1]["total"] == 5
            assert "60.0%" in dashboard_mock.update_widget.call_args[0][1]["message"]