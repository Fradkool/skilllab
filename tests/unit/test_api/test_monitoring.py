"""
Unit tests for the monitoring API
"""

import os
import sys
import json
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

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


class TestMonitoringAPI:
    """Test the monitoring API functions"""
    
    @patch('api.monitoring.get_config')
    @patch('api.monitoring.initialize_monitoring')
    def test_initialize_monitoring_system(self, mock_init_monitoring, mock_get_config):
        """Test initializing the monitoring system"""
        # Setup mocks
        mock_config = MagicMock()
        mock_config.monitoring = MagicMock()
        mock_config.monitoring.metrics_db = '/path/to/db.sqlite'
        mock_get_config.return_value = mock_config
        mock_init_monitoring.return_value = MagicMock()
        
        # Call function
        result = initialize_monitoring_system(enabled=True)
        
        # Check results
        assert result is True
        mock_get_config.assert_called_once()
        assert mock_config.monitoring.enabled is True
        mock_init_monitoring.assert_called_once_with(
            db_path='/path/to/db.sqlite',
            enabled=True
        )
    
    @patch('api.monitoring.shutdown_monitoring')
    def test_shutdown_monitoring_system(self, mock_shutdown):
        """Test shutting down the monitoring system"""
        # Setup mock
        mock_shutdown.return_value = None
        
        # Call function
        result = shutdown_monitoring_system()
        
        # Check results
        assert result is True
        mock_shutdown.assert_called_once()
    
    @patch('api.monitoring.shutdown_monitoring')
    def test_shutdown_monitoring_system_error(self, mock_shutdown):
        """Test shutting down with an exception"""
        # Setup mock
        mock_shutdown.side_effect = Exception("Test error")
        
        # Call function
        result = shutdown_monitoring_system()
        
        # Check results
        assert result is False
        mock_shutdown.assert_called_once()
    
    @patch('api.monitoring.psutil')
    @patch('api.monitoring.GPUMonitor')
    def test_get_system_resources(self, mock_gpu_monitor_class, mock_psutil):
        """Test getting system resources"""
        # Setup psutil mocks
        mock_psutil.cpu_percent.return_value = 25.0
        mock_psutil.cpu_count.side_effect = [8, 4]  # logical, physical
        
        mock_memory = MagicMock()
        mock_memory.total = 16 * (1024 ** 3)  # 16GB
        mock_memory.available = 8 * (1024 ** 3)  # 8GB
        mock_memory.used = 8 * (1024 ** 3)  # 8GB
        mock_memory.percent = 50.0
        mock_psutil.virtual_memory.return_value = mock_memory
        
        mock_disk = MagicMock()
        mock_disk.total = 500 * (1024 ** 3)  # 500GB
        mock_disk.used = 100 * (1024 ** 3)  # 100GB
        mock_disk.free = 400 * (1024 ** 3)  # 400GB
        mock_disk.percent = 20.0
        mock_psutil.disk_usage.return_value = mock_disk
        
        # Setup GPU mock
        mock_gpu_monitor = MagicMock()
        mock_gpu_monitor.has_gpu = True
        mock_gpu_monitor._get_gpu_stats.return_value = {
            0: {
                "name": "GeForce RTX 3080",
                "memory": {
                    "total_mb": 10240,  # 10GB
                    "used_mb": 2048     # 2GB
                },
                "utilization": {
                    "gpu_percent": 30.0
                },
                "temperature_c": 65.0
            }
        }
        mock_gpu_monitor_class.return_value = mock_gpu_monitor
        
        # Mock datetime
        with patch('api.monitoring.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 1, 12, 0, 0)
            
            # Call function
            result = get_system_resources()
            
            # Check results
            assert result["timestamp"] == "2024-01-01T12:00:00"
            assert result["cpu"]["percent"] == 25.0
            assert result["cpu"]["cores"] == 8
            assert result["cpu"]["physical_cores"] == 4
            assert result["memory"]["total_gb"] == 16.0
            assert result["memory"]["available_gb"] == 8.0
            assert result["memory"]["used_gb"] == 8.0
            assert result["memory"]["percent"] == 50.0
            assert result["disk"]["total_gb"] == 500.0
            assert result["disk"]["used_gb"] == 100.0
            assert result["disk"]["free_gb"] == 400.0
            assert result["disk"]["percent"] == 20.0
            assert "gpu" in result
            assert "0" in result["gpu"]
            assert result["gpu"]["0"]["name"] == "GeForce RTX 3080"
            assert result["gpu"]["0"]["memory_total_gb"] == 10.0
            assert result["gpu"]["0"]["memory_used_gb"] == 2.0
            assert result["gpu"]["0"]["utilization_percent"] == 30.0
            assert result["gpu"]["0"]["temperature_c"] == 65.0
    
    @patch('api.monitoring.GPUMonitor')
    def test_start_resource_monitoring(self, mock_gpu_monitor_class):
        """Test starting resource monitoring"""
        # Setup mock
        mock_gpu_monitor = MagicMock()
        mock_gpu_monitor.start_monitoring.return_value = True
        mock_gpu_monitor_class.return_value = mock_gpu_monitor
        
        # Call function
        result = start_resource_monitoring("test_activity")
        
        # Check results
        assert result is True
        mock_gpu_monitor.start_monitoring.assert_called_once_with("test_activity")
    
    @patch('api.monitoring.GPUMonitor')
    def test_stop_resource_monitoring(self, mock_gpu_monitor_class):
        """Test stopping resource monitoring"""
        # Setup mock
        mock_gpu_monitor = MagicMock()
        mock_summary = {"cpu": 25.0, "gpu": 30.0, "duration": 60.0}
        mock_gpu_monitor.get_summary.return_value = mock_summary
        mock_gpu_monitor_class.return_value = mock_gpu_monitor
        
        # Call function
        result = stop_resource_monitoring("test_activity")
        
        # Check results
        assert result == mock_summary
        mock_gpu_monitor.stop_monitoring.assert_called_once_with("test_activity")
        mock_gpu_monitor.get_summary.assert_called_once_with("test_activity")
    
    @patch('api.monitoring.get_metrics_repository')
    def test_get_pipeline_progress(self, mock_get_repo):
        """Test getting pipeline progress"""
        # Setup mock database
        mock_repo = MagicMock()
        
        # Mock database fetch methods
        mock_status_rows = [
            {"status": "registered", "count": 10},
            {"status": "ocr_complete", "count": 8},
            {"status": "json_complete", "count": 6},
            {"status": "validated", "count": 4}
        ]
        
        mock_pipeline_metrics = [
            {"metric_name": "ocr", "metric_value": 1.0, "timestamp": "2024-01-01T12:00:00"}
        ]
        
        mock_dataset_metrics = [
            {
                "metric_name": "build_time",
                "metric_value": 120.0,
                "details": json.dumps({
                    "train_samples": 80,
                    "val_samples": 20
                })
            },
            {
                "metric_name": "progress",
                "metric_value": 75.0,
                "details": None
            }
        ]
        
        # Setup repo fetch_all mock to return different results for different queries
        def mock_fetch_all(query, params=None):
            if "status, COUNT(*)" in query:
                return mock_status_rows
            elif "metric_type = 'pipeline'" in query:
                return mock_pipeline_metrics
            elif "metric_type = 'dataset'" in query:
                return mock_dataset_metrics
            return []
        
        mock_repo.db.fetch_all = mock_fetch_all
        mock_get_repo.return_value = mock_repo
        
        # Call function
        result = get_pipeline_progress()
        
        # Check results
        assert "ocr" in result
        assert "json" in result
        assert "correction" in result
        assert "dataset" in result
        assert "training" in result
        
        assert result["ocr"]["total"] == 28  # Sum of all documents
        assert result["ocr"]["completed"] == 8
        assert result["ocr"]["active"] is True  # From pipeline metrics
        
        assert result["json"]["completed"] == 6
        assert result["correction"]["completed"] == 4
        
        assert result["dataset"]["completed"] == 100  # From dataset metrics
        assert result["dataset"]["total"] == 100
        
        assert result["training"]["completed"] == 75  # From training progress
        assert result["training"]["total"] == 100
    
    @patch('api.monitoring.get_metrics_repository')
    def test_get_performance_metrics(self, mock_get_repo):
        """Test getting performance metrics"""
        # Setup mocks
        mock_repo = MagicMock()
        
        # Mock metrics data
        mock_metrics = [
            {
                "metric_type": "resource",
                "metric_name": "cpu_usage",
                "metric_value": 25.0,
                "timestamp": "2024-01-01T12:00:00",
                "details": None
            },
            {
                "metric_type": "resource",
                "metric_name": "memory_usage",
                "metric_value": 50.0,
                "timestamp": "2024-01-01T12:01:00",
                "details": None
            },
            {
                "metric_type": "performance",
                "metric_name": "ocr_time",
                "metric_value": 1.5,
                "timestamp": "2024-01-01T12:02:00",
                "details": json.dumps({"document_id": "doc1"})
            }
        ]
        
        mock_repo.db.fetch_all.return_value = mock_metrics
        mock_get_repo.return_value = mock_repo
        
        # Mock datetime
        with patch('api.monitoring.datetime') as mock_datetime:
            now = datetime(2024, 1, 1, 13, 0, 0)
            mock_datetime.now.return_value = now
            
            # Call function
            result = get_performance_metrics(time_range="hour")
            
            # Check results
            assert result["time_range"] == "hour"
            assert result["start_time"] == (now - timedelta(hours=1)).isoformat()
            assert result["end_time"] == now.isoformat()
            
            assert "resource" in result["metrics"]
            assert "performance" in result["metrics"]
            
            assert "cpu_usage" in result["metrics"]["resource"]
            assert "memory_usage" in result["metrics"]["resource"]
            assert "ocr_time" in result["metrics"]["performance"]
            
            assert len(result["metrics"]["resource"]["cpu_usage"]) == 1
            assert result["metrics"]["resource"]["cpu_usage"][0]["value"] == 25.0
            
            assert result["metrics"]["performance"]["ocr_time"][0]["details"] == {"document_id": "doc1"}
    
    @patch('api.monitoring.get_metrics_repository')
    def test_get_recent_activity(self, mock_get_repo):
        """Test getting recent activity"""
        # Setup mocks
        mock_repo = MagicMock()
        
        # Mock activity data
        mock_activities = [
            {
                "type": "pipeline",
                "id": 1,
                "start_time": "2024-01-01T12:00:00",
                "end_time": "2024-01-01T12:30:00",
                "status": "completed",
                "start_step": "ocr",
                "end_step": "json",
                "document_count": 10,
                "details": json.dumps({"success": True})
            },
            {
                "type": "step",
                "id": 2,
                "start_time": "2024-01-01T12:00:00",
                "end_time": "2024-01-01T12:15:00",
                "status": "completed",
                "step_name": "ocr",
                "document_count": 10,
                "details": None
            }
        ]
        
        mock_repo.db.fetch_all.return_value = mock_activities
        mock_get_repo.return_value = mock_repo
        
        # Call function
        result = get_recent_activity(limit=10)
        
        # Check results
        assert len(result) == 2
        assert result[0]["type"] == "pipeline"
        assert result[0]["id"] == 1
        assert result[0]["status"] == "completed"
        assert result[0]["start_time"] == "2024-01-01T12:00:00"
        assert result[0]["end_time"] == "2024-01-01T12:30:00"
        assert result[0]["step"] == "ocr"
        assert result[0]["end_step"] == "json"
        assert result[0]["document_count"] == 10
        assert result[0]["details"] == {"success": True}
        
        assert result[1]["type"] == "step"
        assert result[1]["step"] == "ocr"
    
    @patch('api.monitoring.get_metrics_repository')
    def test_get_document_processing_stats(self, mock_get_repo):
        """Test getting document processing stats"""
        # Setup mocks
        mock_repo = MagicMock()
        
        # Mock document stats
        mock_doc_stats = {
            "total": 100,
            "avg_ocr_confidence": 85.5,
            "avg_json_confidence": 78.3,
            "avg_correction_count": 1.2,
            "flagged_count": 15
        }
        
        # Mock status counts
        mock_status_rows = [
            {"status": "registered", "count": 100},
            {"status": "ocr_complete", "count": 80},
            {"status": "json_complete", "count": 60},
            {"status": "validated", "count": 40}
        ]
        
        # Mock processing times
        mock_processing_rows = [
            {"step_name": "ocr", "avg_time": 1.5},
            {"step_name": "json", "avg_time": 2.0},
            {"step_name": "correction", "avg_time": 0.5}
        ]
        
        # Configure mock repo
        mock_repo.db.fetch_one.return_value = mock_doc_stats
        
        def mock_fetch_all(query, *args, **kwargs):
            if "status, COUNT" in query:
                return mock_status_rows
            elif "step_name, AVG" in query:
                return mock_processing_rows
            return []
        
        mock_repo.db.fetch_all = mock_fetch_all
        mock_get_repo.return_value = mock_repo
        
        # Call function
        result = get_document_processing_stats()
        
        # Check results
        assert result["total_documents"] == 100
        assert result["average_ocr_confidence"] == 85.5
        assert result["average_json_confidence"] == 78.3
        assert result["average_correction_count"] == 1.2
        assert result["flagged_document_count"] == 15
        
        assert "status_counts" in result
        assert result["status_counts"]["registered"] == 100
        assert result["status_counts"]["ocr_complete"] == 80
        assert result["status_counts"]["json_complete"] == 60
        assert result["status_counts"]["validated"] == 40
        
        assert "average_processing_times" in result
        assert result["average_processing_times"]["ocr"] == 1.5
        assert result["average_processing_times"]["json"] == 2.0
        assert result["average_processing_times"]["correction"] == 0.5
    
    @patch('api.monitoring.get_metrics_repository')
    def test_record_custom_metric(self, mock_get_repo):
        """Test recording a custom metric"""
        # Setup mocks
        mock_repo = MagicMock()
        mock_repo.record_metric.return_value = True
        mock_get_repo.return_value = mock_repo
        
        # Call function
        result = record_custom_metric(
            metric_type="custom",
            metric_name="test_metric",
            metric_value=42.0,
            details={"note": "Test data"}
        )
        
        # Check results
        assert result is True
        mock_get_repo.assert_called_once()
        mock_repo.record_metric.assert_called_once_with(
            metric_type="custom",
            metric_name="test_metric",
            metric_value=42.0,
            details={"note": "Test data"}
        )