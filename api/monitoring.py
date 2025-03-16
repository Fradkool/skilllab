"""
Monitoring API for SkillLab
Provides high-level functions for system monitoring and metrics
"""

import os
import time
import json
import psutil
import logging
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime, timedelta

from config import get_config
from database import get_metrics_repository
from monitor.integration import get_monitoring, initialize_monitoring
from utils.gpu_monitor import GPUMonitor

# Setup logger
logger = logging.getLogger(__name__)

def initialize_monitoring_system(enabled: bool = True) -> bool:
    """
    Initialize the monitoring system
    
    Args:
        enabled: Whether to enable monitoring
        
    Returns:
        True if successful, False otherwise
    """
    config = get_config()
    
    # Update configuration
    config.monitoring.enabled = enabled
    
    # Initialize monitoring
    monitoring = initialize_monitoring(
        db_path=config.monitoring.metrics_db,
        enabled=enabled
    )
    
    return monitoring is not None

def shutdown_monitoring_system() -> bool:
    """
    Shutdown the monitoring system
    
    Returns:
        True if successful, False otherwise
    """
    from monitor.integration import shutdown_monitoring
    
    try:
        shutdown_monitoring()
        return True
    except Exception:
        return False

def get_system_resources() -> Dict[str, Any]:
    """
    Get current system resource usage
    
    Returns:
        Dictionary with resource usage information
    """
    # Get CPU and memory info
    cpu_percent = psutil.cpu_percent()
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    resources = {
        "timestamp": datetime.now().isoformat(),
        "cpu": {
            "percent": cpu_percent,
            "cores": psutil.cpu_count(),
            "physical_cores": psutil.cpu_count(logical=False)
        },
        "memory": {
            "total_gb": memory.total / (1024 ** 3),
            "available_gb": memory.available / (1024 ** 3),
            "used_gb": memory.used / (1024 ** 3),
            "percent": memory.percent
        },
        "disk": {
            "total_gb": disk.total / (1024 ** 3),
            "used_gb": disk.used / (1024 ** 3),
            "free_gb": disk.free / (1024 ** 3),
            "percent": disk.percent
        }
    }
    
    # Add GPU information if available
    gpu_monitor = GPUMonitor()
    if gpu_monitor.has_gpu:
        gpu_stats = gpu_monitor._get_gpu_stats()
        resources["gpu"] = {}
        
        for gpu_id, gpu_data in gpu_stats.items():
            resources["gpu"][str(gpu_id)] = {
                "name": gpu_data.get("name", "Unknown"),
                "memory_total_gb": gpu_data.get("memory", {}).get("total_mb", 0) / 1024,
                "memory_used_gb": gpu_data.get("memory", {}).get("used_mb", 0) / 1024,
                "utilization_percent": gpu_data.get("utilization", {}).get("gpu_percent", 0),
                "temperature_c": gpu_data.get("temperature_c", 0)
            }
    
    return resources

def start_resource_monitoring(activity: str) -> bool:
    """
    Start resource monitoring for a specific activity
    
    Args:
        activity: Activity name
        
    Returns:
        True if monitoring started, False otherwise
    """
    gpu_monitor = GPUMonitor()
    return gpu_monitor.start_monitoring(activity)

def stop_resource_monitoring(activity: str) -> Dict[str, Any]:
    """
    Stop resource monitoring for a specific activity
    
    Args:
        activity: Activity name
        
    Returns:
        Dictionary with monitoring summary
    """
    gpu_monitor = GPUMonitor()
    gpu_monitor.stop_monitoring(activity)
    return gpu_monitor.get_summary(activity)

def get_pipeline_progress() -> Dict[str, Any]:
    """
    Get current pipeline progress
    
    Returns:
        Dictionary with pipeline progress information
    """
    metrics_repo = get_metrics_repository()
    if not metrics_repo:
        return {"error": "Metrics repository not available"}
    
    # Map statuses to pipeline steps
    pipeline_progress = {
        "ocr": {"completed": 0, "total": 0, "active": False},
        "json": {"completed": 0, "total": 0, "active": False},
        "correction": {"completed": 0, "total": 0, "active": False},
        "dataset": {"completed": 0, "total": 0, "active": False},
        "training": {"completed": 0, "total": 0, "active": False}
    }
    
    try:
        # Use the repository for querying document stats
        conn = metrics_repo.db.get_connection()
        
        # Get document count by status
        cursor = conn.cursor()
        cursor.execute("SELECT status, COUNT(*) FROM documents GROUP BY status")
        status_counts = {status: count for status, count in cursor.fetchall()}
        
        # Get total document count
        total_documents = sum(status_counts.values())
        
        # Update pipeline progress with document counts
        for step in ["ocr", "json", "correction"]:
            pipeline_progress[step]["total"] = total_documents
        
        # Map statuses to completed steps
        if "ocr_complete" in status_counts:
            pipeline_progress["ocr"]["completed"] = status_counts["ocr_complete"]
        
        if "json_complete" in status_counts:
            pipeline_progress["json"]["completed"] = status_counts["json_complete"]
        
        if "validated" in status_counts:
            pipeline_progress["correction"]["completed"] = status_counts["validated"]
        
        # Get active pipeline from metrics
        pipeline_metrics = metrics_repo.db.fetch_all(
            """
            SELECT metric_name, metric_value, timestamp 
            FROM metrics 
            WHERE metric_type = 'pipeline'
            ORDER BY timestamp DESC
            LIMIT 1
            """
        )
        
        if pipeline_metrics:
            active_step = pipeline_metrics[0]["metric_name"]
            if active_step in pipeline_progress:
                pipeline_progress[active_step]["active"] = True
        
        # Get dataset and training metrics
        dataset_metrics = metrics_repo.db.fetch_all(
            """
            SELECT metric_name, metric_value, details
            FROM metrics
            WHERE metric_type = 'dataset' OR metric_type = 'training'
            ORDER BY timestamp DESC
            LIMIT 10
            """
        )
        
        # Process dataset and training metrics
        for metric in dataset_metrics:
            metric_name = metric["metric_name"]
            metric_value = metric["metric_value"]
            details_json = metric["details"]
            
            if metric_name == "build_time" and details_json:
                try:
                    details = json.loads(details_json)
                    train_samples = details.get("train_samples", 0)
                    val_samples = details.get("val_samples", 0)
                    dataset_samples = train_samples + val_samples
                    pipeline_progress["dataset"]["completed"] = dataset_samples
                    pipeline_progress["dataset"]["total"] = dataset_samples
                except json.JSONDecodeError:
                    pass
            
            if metric_name == "progress":
                training_progress = metric_value
                pipeline_progress["training"]["completed"] = int(training_progress)
                pipeline_progress["training"]["total"] = 100
    
    except Exception as e:
        logger.error(f"Error getting pipeline progress: {e}")
    
    return pipeline_progress

def get_performance_metrics(
    time_range: str = "day",
    metric_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get performance metrics over time
    
    Args:
        time_range: Time range ('hour', 'day', 'week', 'month')
        metric_type: Optional metric type filter
        
    Returns:
        Dictionary with performance metrics
    """
    metrics_repo = get_metrics_repository()
    if not metrics_repo:
        return {"error": "Metrics repository not available"}
    
    # Calculate time range
    now = datetime.now()
    if time_range == "hour":
        start_time = now - timedelta(hours=1)
    elif time_range == "day":
        start_time = now - timedelta(days=1)
    elif time_range == "week":
        start_time = now - timedelta(weeks=1)
    elif time_range == "month":
        start_time = now - timedelta(days=30)
    else:
        return {"error": "Invalid time range"}
    
    # Format start time for SQLite
    start_time_str = start_time.isoformat()
    
    # Initialize results
    results = {
        "time_range": time_range,
        "start_time": start_time_str,
        "end_time": now.isoformat(),
        "metrics": {}
    }
    
    try:
        # Build query parameters
        params = [start_time_str]
        where_clause = "timestamp >= ?"
        
        if metric_type:
            where_clause += " AND metric_type = ?"
            params.append(metric_type)
        
        # Use repository to fetch metrics
        metrics_data = metrics_repo.db.fetch_all(
            f"""
            SELECT metric_type, metric_name, metric_value, timestamp, details
            FROM metrics
            WHERE {where_clause}
            ORDER BY timestamp ASC
            """,
            tuple(params)
        )
        
        # Process results
        for metric in metrics_data:
            m_type = metric["metric_type"]
            m_name = metric["metric_name"]
            m_value = metric["metric_value"]
            m_time = metric["timestamp"]
            m_details = metric["details"]
            
            # Create metric type group if it doesn't exist
            if m_type not in results["metrics"]:
                results["metrics"][m_type] = {}
            
            # Create metric name group if it doesn't exist
            if m_name not in results["metrics"][m_type]:
                results["metrics"][m_type][m_name] = []
            
            # Parse details if available
            details = None
            if m_details:
                try:
                    details = json.loads(m_details)
                except json.JSONDecodeError:
                    details = m_details
            
            # Add data point
            results["metrics"][m_type][m_name].append({
                "timestamp": m_time,
                "value": m_value,
                "details": details
            })
    
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        results["error"] = str(e)
    
    return results

def get_recent_activity(limit: int = 20) -> List[Dict[str, Any]]:
    """
    Get recent pipeline activity
    
    Args:
        limit: Maximum number of records to return
        
    Returns:
        List of activity records
    """
    metrics_repo = get_metrics_repository()
    if not metrics_repo:
        return []
    
    activities = []
    
    try:
        # Use the repository to fetch recent activity
        query = f"""
        SELECT 'pipeline' as type, id, start_time, end_time, status, start_step, end_step, document_count, details
        FROM pipeline_runs
        UNION ALL
        SELECT 'step' as type, id, start_time, end_time, status, step_name, NULL, document_count, details
        FROM step_executions
        ORDER BY start_time DESC
        LIMIT {limit}
        """
        
        # Execute query
        raw_activities = metrics_repo.db.fetch_all(query)
        
        # Process results
        for record in raw_activities:
            record_type = record["type"]
            record_id = record["id"]
            start_time = record["start_time"]
            end_time = record["end_time"]
            status = record["status"]
            step = record["start_step"] if record_type == "pipeline" else record["step_name"]
            end_step = record.get("end_step")
            doc_count = record.get("document_count")
            details_json = record.get("details")
            
            # Parse details if available
            details = None
            if details_json:
                try:
                    details = json.loads(details_json)
                except json.JSONDecodeError:
                    details = details_json
            
            # Create activity record
            activity = {
                "type": record_type,
                "id": record_id,
                "start_time": start_time,
                "end_time": end_time,
                "status": status,
                "step": step
            }
            
            if end_step:
                activity["end_step"] = end_step
            
            if doc_count:
                activity["document_count"] = doc_count
            
            if details:
                activity["details"] = details
            
            activities.append(activity)
    
    except Exception as e:
        logger.error(f"Error getting recent activity: {e}")
    
    return activities

def get_document_processing_stats() -> Dict[str, Any]:
    """
    Get document processing statistics
    
    Returns:
        Dictionary with document processing statistics
    """
    metrics_repo = get_metrics_repository()
    if not metrics_repo:
        return {"error": "Metrics repository not available"}
    
    stats = {
        "total_documents": 0,
        "average_ocr_confidence": 0,
        "average_json_confidence": 0,
        "average_correction_count": 0,
        "flagged_document_count": 0,
        "status_counts": {},
        "average_processing_times": {}
    }
    
    try:
        # Get general document stats using repository
        doc_stats = metrics_repo.db.fetch_one("""
        SELECT 
            COUNT(*) as total,
            AVG(ocr_confidence) as avg_ocr_confidence,
            AVG(json_confidence) as avg_json_confidence,
            AVG(correction_count) as avg_correction_count,
            SUM(CASE WHEN flagged_for_review = 1 THEN 1 ELSE 0 END) as flagged_count
        FROM documents
        """)
        
        if doc_stats:
            stats.update({
                "total_documents": doc_stats["total"],
                "average_ocr_confidence": doc_stats["avg_ocr_confidence"],
                "average_json_confidence": doc_stats["avg_json_confidence"],
                "average_correction_count": doc_stats["avg_correction_count"],
                "flagged_document_count": doc_stats["flagged_count"]
            })
        
        # Get counts by status
        status_rows = metrics_repo.db.fetch_all("""
        SELECT status, COUNT(*) as count
        FROM documents 
        GROUP BY status
        """)
        
        status_counts = {}
        for row in status_rows:
            status_counts[row["status"]] = row["count"]
        
        stats["status_counts"] = status_counts
        
        # Get processing times from recent pipeline runs
        processing_rows = metrics_repo.db.fetch_all("""
        SELECT step_name, AVG(
            CASE 
                WHEN end_time IS NOT NULL AND start_time IS NOT NULL 
                THEN (julianday(end_time) - julianday(start_time)) * 86400 
                ELSE NULL 
            END
        ) as avg_time
        FROM step_executions
        WHERE end_time IS NOT NULL
        GROUP BY step_name
        """)
        
        processing_times = {}
        for row in processing_rows:
            processing_times[row["step_name"]] = row["avg_time"]
        
        stats["average_processing_times"] = processing_times
    
    except Exception as e:
        logger.error(f"Error getting document processing stats: {e}")
        stats["error"] = str(e)
    
    return stats

def record_custom_metric(
    metric_type: str,
    metric_name: str,
    metric_value: float,
    details: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Record a custom metric
    
    Args:
        metric_type: Metric type (category)
        metric_name: Metric name
        metric_value: Numeric value
        details: Optional additional details
        
    Returns:
        True if successful, False otherwise
    """
    metrics_repo = get_metrics_repository()
    if not metrics_repo:
        return False
    
    return metrics_repo.record_metric(
        metric_type=metric_type,
        metric_name=metric_name,
        metric_value=metric_value,
        details=details
    )