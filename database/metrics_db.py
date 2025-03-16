"""
Metrics database for SkillLab
Manages the collection and storage of metrics data
"""

import os
import logging
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime

from .core import BaseRepository, DatabaseConnection
from config import get_config

# Setup logger
logger = logging.getLogger(__name__)

# Schema definition
METRICS_SCHEMA = """
-- Documents table
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    filename TEXT,
    status TEXT,
    ocr_confidence REAL,
    json_confidence REAL,
    correction_count INTEGER,
    flagged_for_review INTEGER,
    review_status TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Document issues table
CREATE TABLE IF NOT EXISTS document_issues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id TEXT,
    issue_type TEXT,
    issue_details TEXT,
    created_at TIMESTAMP,
    FOREIGN KEY (document_id) REFERENCES documents(id)
);

-- Metrics table
CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP,
    metric_type TEXT,
    metric_name TEXT,
    metric_value REAL,
    details TEXT
);

-- Resource usage table
CREATE TABLE IF NOT EXISTS resource_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP,
    activity TEXT,
    cpu_percent REAL,
    memory_mb REAL,
    gpu_device INTEGER,
    gpu_name TEXT,
    gpu_utilization REAL,
    gpu_memory_used_mb REAL,
    gpu_memory_total_mb REAL,
    temperature_c REAL
);

-- Pipeline runs table
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    status TEXT,
    start_step TEXT,
    end_step TEXT,
    document_count INTEGER,
    details TEXT
);

-- Step execution table
CREATE TABLE IF NOT EXISTS step_executions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pipeline_run_id INTEGER,
    step_name TEXT,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    status TEXT,
    document_count INTEGER,
    details TEXT,
    FOREIGN KEY (pipeline_run_id) REFERENCES pipeline_runs(id)
);
"""

class MetricsRepository(BaseRepository):
    """Repository for metrics data"""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize metrics repository
        
        Args:
            db_path: Path to database (None to use configured path)
        """
        config = get_config()
        metrics_db_path = db_path or config.monitoring.metrics_db
        super().__init__(DatabaseConnection(metrics_db_path))
        
        # Initialize database if needed
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema"""
        self._create_database(METRICS_SCHEMA)
    
    def register_document(self, document_id: str, filename: str) -> bool:
        """
        Register a document for tracking
        
        Args:
            document_id: Document identifier
            filename: Original filename
            
        Returns:
            True if registered successfully, False otherwise
        """
        try:
            # Check if document already exists
            existing = self.db.fetch_one(
                "SELECT id FROM documents WHERE id = ?", 
                (document_id,)
            )
            
            now = self._get_now()
            
            if existing:
                # Update existing document
                self.db.update(
                    "documents",
                    {"filename": filename, "updated_at": now},
                    "id = ?",
                    (document_id,)
                )
            else:
                # Insert new document
                self.db.insert(
                    "documents",
                    {
                        "id": document_id,
                        "filename": filename,
                        "status": "registered",
                        "ocr_confidence": 0.0,
                        "json_confidence": 0.0,
                        "correction_count": 0,
                        "flagged_for_review": 0,
                        "review_status": "none",
                        "created_at": now,
                        "updated_at": now
                    }
                )
            
            logger.info(f"Registered document: {document_id} ({filename})")
            return True
        except Exception as e:
            logger.error(f"Error registering document {document_id}: {e}")
            return False
    
    def update_document_status(self, document_id: str, status: str) -> bool:
        """
        Update document status
        
        Args:
            document_id: Document identifier
            status: New status
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            self.db.update(
                "documents",
                {"status": status, "updated_at": self._get_now()},
                "id = ?",
                (document_id,)
            )
            
            logger.info(f"Updated document status: {document_id} -> {status}")
            return True
        except Exception as e:
            logger.error(f"Error updating document status {document_id}: {e}")
            return False
    
    def update_document_confidence(
        self, 
        document_id: str, 
        ocr_confidence: Optional[float] = None,
        json_confidence: Optional[float] = None
    ) -> bool:
        """
        Update document confidence scores
        
        Args:
            document_id: Document identifier
            ocr_confidence: OCR confidence score (0-100)
            json_confidence: JSON extraction confidence score (0-100)
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            update_data = {"updated_at": self._get_now()}
            
            if ocr_confidence is not None:
                update_data["ocr_confidence"] = ocr_confidence
            
            if json_confidence is not None:
                update_data["json_confidence"] = json_confidence
            
            self.db.update(
                "documents",
                update_data,
                "id = ?",
                (document_id,)
            )
            
            # Check if document should be flagged for review
            should_flag = False
            flag_reason = None
            
            # Get current document data
            doc = self.db.fetch_one(
                "SELECT ocr_confidence, json_confidence FROM documents WHERE id = ?", 
                (document_id,)
            )
            
            if doc:
                doc_ocr_conf = ocr_confidence if ocr_confidence is not None else doc["ocr_confidence"]
                doc_json_conf = json_confidence if json_confidence is not None else doc["json_confidence"]
                
                # Flag if below thresholds
                if doc_ocr_conf < 75:
                    should_flag = True
                    flag_reason = "low_ocr_confidence"
                elif doc_json_conf < 75:
                    should_flag = True
                    flag_reason = "low_json_confidence"
            
            # Flag for review if needed
            if should_flag:
                self.db.update(
                    "documents",
                    {
                        "flagged_for_review": 1,
                        "review_status": "pending"
                    },
                    "id = ?",
                    (document_id,)
                )
                
                # Add issue
                if flag_reason:
                    confidence_value = doc_ocr_conf if flag_reason == "low_ocr_confidence" else doc_json_conf
                    self.flag_for_review(
                        document_id, 
                        flag_reason, 
                        f"Confidence below threshold: {confidence_value:.1f}%"
                    )
            
            logger.info(f"Updated document confidence: {document_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating document confidence {document_id}: {e}")
            return False
    
    def increment_correction_count(self, document_id: str) -> bool:
        """
        Increment document correction count
        
        Args:
            document_id: Document identifier
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            # Get current correction count
            doc = self.db.fetch_one(
                "SELECT correction_count FROM documents WHERE id = ?", 
                (document_id,)
            )
            
            if not doc:
                logger.warning(f"Document not found: {document_id}")
                return False
            
            current_count = doc["correction_count"]
            new_count = current_count + 1
            
            # Update document
            self.db.update(
                "documents",
                {
                    "correction_count": new_count,
                    "updated_at": self._get_now()
                },
                "id = ?",
                (document_id,)
            )
            
            # Flag for review if too many corrections
            if new_count >= 3:
                self.db.update(
                    "documents",
                    {
                        "flagged_for_review": 1,
                        "review_status": "pending"
                    },
                    "id = ?",
                    (document_id,)
                )
                
                # Add issue
                self.flag_for_review(
                    document_id,
                    "multiple_corrections",
                    f"Document required {new_count} correction attempts"
                )
            
            logger.info(f"Incremented correction count for {document_id}: {new_count}")
            return True
        except Exception as e:
            logger.error(f"Error incrementing correction count for {document_id}: {e}")
            return False
    
    def flag_for_review(self, document_id: str, issue_type: str, details: str) -> bool:
        """
        Flag document for review
        
        Args:
            document_id: Document identifier
            issue_type: Type of issue
            details: Issue details
            
        Returns:
            True if flagged successfully, False otherwise
        """
        try:
            # Update document
            self.db.update(
                "documents",
                {
                    "flagged_for_review": 1,
                    "review_status": "pending",
                    "updated_at": self._get_now()
                },
                "id = ?",
                (document_id,)
            )
            
            # Add issue
            self.db.insert(
                "document_issues",
                {
                    "document_id": document_id,
                    "issue_type": issue_type,
                    "issue_details": details,
                    "created_at": self._get_now()
                }
            )
            
            logger.info(f"Flagged document for review: {document_id} ({issue_type})")
            return True
        except Exception as e:
            logger.error(f"Error flagging document for review {document_id}: {e}")
            return False
    
    def record_metric(
        self, 
        metric_type: str, 
        metric_name: str, 
        metric_value: float, 
        details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Record a general metric
        
        Args:
            metric_type: Type of metric (performance, resource, quality, etc.)
            metric_name: Name of the metric
            metric_value: Numeric value
            details: Optional additional details
            
        Returns:
            True if recorded successfully, False otherwise
        """
        try:
            details_json = self._serialize_json(details) if details else None
            
            self.db.insert(
                "metrics",
                {
                    "timestamp": self._get_now(),
                    "metric_type": metric_type,
                    "metric_name": metric_name,
                    "metric_value": metric_value,
                    "details": details_json
                }
            )
            
            logger.debug(f"Recorded metric: {metric_type}.{metric_name} = {metric_value}")
            return True
        except Exception as e:
            logger.error(f"Error recording metric {metric_type}.{metric_name}: {e}")
            return False
    
    def record_resource_usage(
        self, 
        activity: str, 
        cpu_percent: float, 
        memory_mb: float,
        gpu_data: Optional[Dict[int, Dict[str, Any]]] = None
    ) -> bool:
        """
        Record resource usage
        
        Args:
            activity: Current activity
            cpu_percent: CPU usage percentage
            memory_mb: Memory usage in MB
            gpu_data: GPU usage data by device ID
            
        Returns:
            True if recorded successfully, False otherwise
        """
        try:
            timestamp = self._get_now()
            
            if gpu_data:
                # Insert one row per GPU
                for gpu_id, gpu_info in gpu_data.items():
                    self.db.insert(
                        "resource_usage",
                        {
                            "timestamp": timestamp,
                            "activity": activity,
                            "cpu_percent": cpu_percent,
                            "memory_mb": memory_mb,
                            "gpu_device": gpu_id,
                            "gpu_name": gpu_info.get("name", "unknown"),
                            "gpu_utilization": gpu_info.get("utilization", {}).get("gpu_percent", 0),
                            "gpu_memory_used_mb": gpu_info.get("memory", {}).get("used_mb", 0),
                            "gpu_memory_total_mb": gpu_info.get("memory", {}).get("total_mb", 0),
                            "temperature_c": gpu_info.get("temperature_c", 0)
                        }
                    )
            else:
                # Insert CPU-only data
                self.db.insert(
                    "resource_usage",
                    {
                        "timestamp": timestamp,
                        "activity": activity,
                        "cpu_percent": cpu_percent,
                        "memory_mb": memory_mb,
                    }
                )
            
            return True
        except Exception as e:
            logger.error(f"Error recording resource usage: {e}")
            return False
    
    def start_pipeline_run(self, start_step: str, end_step: str) -> int:
        """
        Start a pipeline run
        
        Args:
            start_step: Starting step
            end_step: Ending step
            
        Returns:
            Pipeline run ID
        """
        try:
            run_id = self.db.insert(
                "pipeline_runs",
                {
                    "start_time": self._get_now(),
                    "end_time": None,
                    "status": "running",
                    "start_step": start_step,
                    "end_step": end_step,
                    "document_count": 0,
                    "details": None
                }
            )
            
            logger.info(f"Started pipeline run #{run_id}: {start_step} -> {end_step}")
            return run_id
        except Exception as e:
            logger.error(f"Error starting pipeline run: {e}")
            return -1
    
    def end_pipeline_run(
        self, 
        run_id: int, 
        status: str, 
        document_count: int, 
        details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        End a pipeline run
        
        Args:
            run_id: Pipeline run ID
            status: Run status (completed, failed, etc.)
            document_count: Number of documents processed
            details: Optional run details
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            details_json = self._serialize_json(details) if details else None
            
            self.db.update(
                "pipeline_runs",
                {
                    "end_time": self._get_now(),
                    "status": status,
                    "document_count": document_count,
                    "details": details_json
                },
                "id = ?",
                (run_id,)
            )
            
            logger.info(f"Ended pipeline run #{run_id}: {status}, {document_count} documents")
            return True
        except Exception as e:
            logger.error(f"Error ending pipeline run {run_id}: {e}")
            return False
    
    def record_step_execution(
        self,
        pipeline_run_id: int,
        step_name: str,
        status: str,
        document_count: int,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Record a step execution
        
        Args:
            pipeline_run_id: Pipeline run ID
            step_name: Step name
            status: Step status
            document_count: Number of documents processed
            start_time: Start time (None for now)
            end_time: End time (None for now)
            details: Optional step details
            
        Returns:
            Step execution ID
        """
        try:
            now = self._get_now()
            details_json = self._serialize_json(details) if details else None
            
            step_id = self.db.insert(
                "step_executions",
                {
                    "pipeline_run_id": pipeline_run_id,
                    "step_name": step_name,
                    "start_time": start_time or now,
                    "end_time": end_time,
                    "status": status,
                    "document_count": document_count,
                    "details": details_json
                }
            )
            
            logger.info(f"Recorded step execution: {step_name} in run #{pipeline_run_id}")
            return step_id
        except Exception as e:
            logger.error(f"Error recording step execution {step_name}: {e}")
            return -1
    
    def update_step_execution(
        self,
        step_id: int,
        status: str,
        document_count: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update a step execution
        
        Args:
            step_id: Step execution ID
            status: Step status
            document_count: Number of documents processed
            details: Optional step details
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            update_data = {
                "status": status,
                "end_time": self._get_now()
            }
            
            if document_count is not None:
                update_data["document_count"] = document_count
            
            if details is not None:
                update_data["details"] = self._serialize_json(details)
            
            self.db.update(
                "step_executions",
                update_data,
                "id = ?",
                (step_id,)
            )
            
            logger.info(f"Updated step execution #{step_id}: {status}")
            return True
        except Exception as e:
            logger.error(f"Error updating step execution {step_id}: {e}")
            return False
    
    def get_dashboard_stats(self) -> Dict[str, Any]:
        """
        Get statistics for dashboard
        
        Returns:
            Dictionary with dashboard statistics
        """
        stats = {
            "total_documents": 0,
            "flagged_documents": 0,
            "reviewed_documents": 0,
            "issue_stats": {},
            "pipeline_stats": {}
        }
        
        try:
            # Document stats
            doc_stats = self.db.fetch_one("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN flagged_for_review = 1 THEN 1 ELSE 0 END) as flagged,
                    SUM(CASE WHEN review_status IN ('approved', 'rejected', 'completed') THEN 1 ELSE 0 END) as reviewed
                FROM documents
            """)
            
            if doc_stats:
                stats["total_documents"] = doc_stats["total"]
                stats["flagged_documents"] = doc_stats["flagged"]
                stats["reviewed_documents"] = doc_stats["reviewed"]
            
            # Issue statistics
            issue_results = self.db.fetch_all("""
                SELECT issue_type, COUNT(*) as count
                FROM document_issues
                GROUP BY issue_type
                ORDER BY count DESC
            """)
            
            for row in issue_results:
                stats["issue_stats"][row["issue_type"]] = row["count"]
            
            # Pipeline statistics
            pipeline_stats = self.db.fetch_all("""
                SELECT status, COUNT(*) as count
                FROM documents
                GROUP BY status
            """)
            
            for row in pipeline_stats:
                stats["pipeline_stats"][row["status"]] = row["count"]
            
            return stats
        except Exception as e:
            logger.error(f"Error getting dashboard stats: {e}")
            return stats
    
    def get_review_queue(self, issue_filter: str = 'All', limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get documents flagged for review
        
        Args:
            issue_filter: Filter by issue type (All for no filter)
            limit: Maximum number of documents to return
            
        Returns:
            List of document records
        """
        try:
            documents = []
            
            if issue_filter == 'All':
                documents = self.db.fetch_all("""
                    SELECT d.* 
                    FROM documents d
                    WHERE d.flagged_for_review = 1 AND d.review_status != 'completed'
                    ORDER BY d.created_at DESC
                    LIMIT ?
                """, (limit,))
            else:
                documents = self.db.fetch_all("""
                    SELECT d.* 
                    FROM documents d
                    JOIN document_issues i ON d.id = i.document_id
                    WHERE d.flagged_for_review = 1 
                    AND d.review_status != 'completed'
                    AND i.issue_type = ?
                    GROUP BY d.id
                    ORDER BY d.created_at DESC
                    LIMIT ?
                """, (issue_filter, limit))
            
            # Fetch issues for each document
            for doc in documents:
                doc_id = doc["id"]
                issues = self.db.fetch_all("""
                    SELECT issue_type, issue_details 
                    FROM document_issues
                    WHERE document_id = ?
                """, (doc_id,))
                
                doc["issues"] = issues
            
            return documents
        except Exception as e:
            logger.error(f"Error getting review queue: {e}")
            return []
    
    def get_document_details(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Get details for a specific document
        
        Args:
            document_id: Document ID
            
        Returns:
            Document record or None if not found
        """
        try:
            doc = self.db.fetch_one("""
                SELECT * 
                FROM documents
                WHERE id = ?
            """, (document_id,))
            
            if not doc:
                return None
            
            # Fetch issues
            issues = self.db.fetch_all("""
                SELECT issue_type, issue_details 
                FROM document_issues
                WHERE document_id = ?
            """, (document_id,))
            
            doc["issues"] = issues
            
            return doc
        except Exception as e:
            logger.error(f"Error getting document details for {document_id}: {e}")
            return None