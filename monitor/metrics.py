"""
Metrics collection for SkillLab monitor
Collects and tracks metrics from the SkillLab pipeline
"""

import os
import time
import json
import sqlite3
import threading
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from utils.logger import setup_logger

logger = setup_logger("monitor_metrics")

class MetricsCollector:
    """Collects and tracks metrics from the SkillLab pipeline"""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize metrics collector
        
        Args:
            db_path: Path to SQLite database (None for in-memory)
        """
        # Set database path
        self.db_path = db_path or ":memory:"
        
        # Initialize database
        self._init_db()
        
        # Initialize tracking
        self.tracking = False
        self.tracking_thread = None
        
        # Document confidence metrics
        self.document_metrics = {}
        
        # Confidence thresholds
        self.confidence_thresholds = {
            "extraction": 75,  # Below this, flag for review
            "critical_fields": 85,  # For name, email, phone
            "ocr_quality": 80,  # OCR confidence
            "schema_validation": 100  # Schema validation (pass/fail)
        }
    
    def _init_db(self):
        """Initialize the database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create documents table
            cursor.execute('''
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
            )
            ''')
            
            # Create document_issues table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS document_issues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id TEXT,
                issue_type TEXT,
                issue_details TEXT,
                created_at TIMESTAMP,
                FOREIGN KEY (document_id) REFERENCES documents(id)
            )
            ''')
            
            # Create metrics table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP,
                metric_type TEXT,
                metric_name TEXT,
                metric_value REAL,
                details TEXT
            )
            ''')
            
            conn.commit()
            conn.close()
            
            logger.info(f"Initialized metrics database at {self.db_path}")
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")
    
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
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if document already exists
            cursor.execute("SELECT id FROM documents WHERE id = ?", (document_id,))
            if cursor.fetchone():
                # Update existing document
                cursor.execute("""
                UPDATE documents SET
                    filename = ?,
                    updated_at = ?
                WHERE id = ?
                """, (filename, datetime.now(), document_id))
            else:
                # Insert new document
                cursor.execute("""
                INSERT INTO documents (
                    id, filename, status, ocr_confidence, json_confidence,
                    correction_count, flagged_for_review, review_status,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    document_id, filename, "registered", 0.0, 0.0,
                    0, 0, "none", datetime.now(), datetime.now()
                ))
            
            # Initialize document metrics
            self.document_metrics[document_id] = {
                "filename": filename,
                "status": "registered",
                "ocr_confidence": 0.0,
                "json_confidence": 0.0,
                "correction_count": 0,
                "flagged_for_review": False,
                "review_status": "none",
                "issues": []
            }
            
            conn.commit()
            conn.close()
            
            logger.info(f"Registered document: {document_id} ({filename})")
            return True
        except Exception as e:
            logger.error(f"Error registering document {document_id}: {str(e)}")
            return False
    
    def update_document_status(self, document_id: str, status: str) -> bool:
        """
        Update document status
        
        Args:
            document_id: Document identifier
            status: New status (registered, ocr_complete, json_complete, validated, etc.)
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Update document status
            cursor.execute("""
            UPDATE documents SET
                status = ?,
                updated_at = ?
            WHERE id = ?
            """, (status, datetime.now(), document_id))
            
            conn.commit()
            conn.close()
            
            # Update in-memory metrics
            if document_id in self.document_metrics:
                self.document_metrics[document_id]["status"] = status
            
            logger.info(f"Updated document status: {document_id} -> {status}")
            return True
        except Exception as e:
            logger.error(f"Error updating document status {document_id}: {str(e)}")
            return False
    
    def update_document_confidence(self, document_id: str, 
                               ocr_confidence: Optional[float] = None,
                               json_confidence: Optional[float] = None) -> bool:
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
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            update_query = "UPDATE documents SET updated_at = ?"
            params = [datetime.now()]
            
            if ocr_confidence is not None:
                update_query += ", ocr_confidence = ?"
                params.append(ocr_confidence)
            
            if json_confidence is not None:
                update_query += ", json_confidence = ?"
                params.append(json_confidence)
            
            update_query += " WHERE id = ?"
            params.append(document_id)
            
            # Update document
            cursor.execute(update_query, params)
            
            # Check if document should be flagged for review
            should_flag = False
            flag_reason = None
            
            # Get current document data
            cursor.execute("SELECT ocr_confidence, json_confidence FROM documents WHERE id = ?", (document_id,))
            result = cursor.fetchone()
            
            if result:
                doc_ocr_conf = result[0] if ocr_confidence is None else ocr_confidence
                doc_json_conf = result[1] if json_confidence is None else json_confidence
                
                # Flag if below thresholds
                if doc_ocr_conf < self.confidence_thresholds["ocr_quality"]:
                    should_flag = True
                    flag_reason = "low_ocr_confidence"
                elif doc_json_conf < self.confidence_thresholds["extraction"]:
                    should_flag = True
                    flag_reason = "low_json_confidence"
            
            # Flag for review if needed
            if should_flag:
                cursor.execute("""
                UPDATE documents SET
                    flagged_for_review = 1,
                    review_status = 'pending'
                WHERE id = ?
                """, (document_id,))
                
                # Add issue
                if flag_reason:
                    cursor.execute("""
                    INSERT INTO document_issues (
                        document_id, issue_type, issue_details, created_at
                    ) VALUES (?, ?, ?, ?)
                    """, (
                        document_id, flag_reason, 
                        f"Confidence below threshold: {doc_ocr_conf if flag_reason == 'low_ocr_confidence' else doc_json_conf}",
                        datetime.now()
                    ))
            
            conn.commit()
            conn.close()
            
            # Update in-memory metrics
            if document_id in self.document_metrics:
                if ocr_confidence is not None:
                    self.document_metrics[document_id]["ocr_confidence"] = ocr_confidence
                if json_confidence is not None:
                    self.document_metrics[document_id]["json_confidence"] = json_confidence
                
                if should_flag:
                    self.document_metrics[document_id]["flagged_for_review"] = True
                    self.document_metrics[document_id]["review_status"] = "pending"
                    if flag_reason and flag_reason not in [i["type"] for i in self.document_metrics[document_id]["issues"]]:
                        self.document_metrics[document_id]["issues"].append({
                            "type": flag_reason,
                            "details": f"Confidence below threshold"
                        })
            
            logger.info(f"Updated document confidence: {document_id} (OCR: {ocr_confidence}, JSON: {json_confidence})")
            return True
        except Exception as e:
            logger.error(f"Error updating document confidence {document_id}: {str(e)}")
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
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get current correction count
            cursor.execute("SELECT correction_count FROM documents WHERE id = ?", (document_id,))
            result = cursor.fetchone()
            
            if result:
                current_count = result[0]
                new_count = current_count + 1
                
                # Update document
                cursor.execute("""
                UPDATE documents SET
                    correction_count = ?,
                    updated_at = ?
                WHERE id = ?
                """, (new_count, datetime.now(), document_id))
                
                # Flag for review if too many corrections
                if new_count >= 3:
                    cursor.execute("""
                    UPDATE documents SET
                        flagged_for_review = 1,
                        review_status = 'pending'
                    WHERE id = ?
                    """, (document_id,))
                    
                    # Add issue
                    cursor.execute("""
                    INSERT INTO document_issues (
                        document_id, issue_type, issue_details, created_at
                    ) VALUES (?, ?, ?, ?)
                    """, (
                        document_id, "multiple_corrections", 
                        f"Document required {new_count} correction attempts",
                        datetime.now()
                    ))
                
                conn.commit()
                conn.close()
                
                # Update in-memory metrics
                if document_id in self.document_metrics:
                    self.document_metrics[document_id]["correction_count"] = new_count
                    
                    if new_count >= 3:
                        self.document_metrics[document_id]["flagged_for_review"] = True
                        self.document_metrics[document_id]["review_status"] = "pending"
                        self.document_metrics[document_id]["issues"].append({
                            "type": "multiple_corrections",
                            "details": f"Document required {new_count} correction attempts"
                        })
                
                logger.info(f"Incremented correction count for {document_id}: {new_count}")
                return True
            else:
                logger.warning(f"Document not found: {document_id}")
                conn.close()
                return False
        except Exception as e:
            logger.error(f"Error incrementing correction count for {document_id}: {str(e)}")
            return False
    
    def flag_for_review(self, document_id: str, issue_type: str, details: str) -> bool:
        """
        Flag document for review
        
        Args:
            document_id: Document identifier
            issue_type: Type of issue (missing_contact, low_ocr_confidence, etc.)
            details: Issue details
            
        Returns:
            True if flagged successfully, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Update document
            cursor.execute("""
            UPDATE documents SET
                flagged_for_review = 1,
                review_status = 'pending',
                updated_at = ?
            WHERE id = ?
            """, (datetime.now(), document_id))
            
            # Add issue
            cursor.execute("""
            INSERT INTO document_issues (
                document_id, issue_type, issue_details, created_at
            ) VALUES (?, ?, ?, ?)
            """, (document_id, issue_type, details, datetime.now()))
            
            conn.commit()
            conn.close()
            
            # Update in-memory metrics
            if document_id in self.document_metrics:
                self.document_metrics[document_id]["flagged_for_review"] = True
                self.document_metrics[document_id]["review_status"] = "pending"
                self.document_metrics[document_id]["issues"].append({
                    "type": issue_type,
                    "details": details
                })
            
            logger.info(f"Flagged document for review: {document_id} ({issue_type})")
            return True
        except Exception as e:
            logger.error(f"Error flagging document for review {document_id}: {str(e)}")
            return False
    
    def update_review_status(self, document_id: str, status: str) -> bool:
        """
        Update document review status
        
        Args:
            document_id: Document identifier
            status: Review status (pending, in_progress, completed, etc.)
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Update document
            cursor.execute("""
            UPDATE documents SET
                review_status = ?,
                updated_at = ?
            WHERE id = ?
            """, (status, datetime.now(), document_id))
            
            conn.commit()
            conn.close()
            
            # Update in-memory metrics
            if document_id in self.document_metrics:
                self.document_metrics[document_id]["review_status"] = status
            
            logger.info(f"Updated review status for {document_id}: {status}")
            return True
        except Exception as e:
            logger.error(f"Error updating review status for {document_id}: {str(e)}")
            return False
    
    def record_metric(self, metric_type: str, metric_name: str, 
                    metric_value: float, details: Optional[Dict] = None) -> bool:
        """
        Record a general metric
        
        Args:
            metric_type: Type of metric (performance, resource, quality, etc.)
            metric_name: Name of the metric
            metric_value: Numeric value
            details: Optional additional details (JSON serializable)
            
        Returns:
            True if recorded successfully, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Convert details to JSON string if provided
            details_json = json.dumps(details) if details else None
            
            # Insert metric
            cursor.execute("""
            INSERT INTO metrics (
                timestamp, metric_type, metric_name, metric_value, details
            ) VALUES (?, ?, ?, ?, ?)
            """, (datetime.now(), metric_type, metric_name, metric_value, details_json))
            
            conn.commit()
            conn.close()
            
            logger.debug(f"Recorded metric: {metric_type}.{metric_name} = {metric_value}")
            return True
        except Exception as e:
            logger.error(f"Error recording metric {metric_type}.{metric_name}: {str(e)}")
            return False
    
    def get_review_stats(self) -> Dict[str, Any]:
        """
        Get statistics about documents flagged for review
        
        Returns:
            Dictionary with review statistics
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get total flagged documents
            cursor.execute("SELECT COUNT(*) FROM documents WHERE flagged_for_review = 1")
            flagged_count = cursor.fetchone()[0] or 0
            
            # Get reviewed documents
            cursor.execute("SELECT COUNT(*) FROM documents WHERE flagged_for_review = 1 AND review_status = 'completed'")
            reviewed_count = cursor.fetchone()[0] or 0
            
            # Get issue counts
            cursor.execute("""
            SELECT issue_type, COUNT(*) 
            FROM document_issues 
            GROUP BY issue_type 
            ORDER BY COUNT(*) DESC
            """)
            issue_counts = {issue_type: count for issue_type, count in cursor.fetchall()}
            
            conn.close()
            
            return {
                "flagged": flagged_count,
                "reviewed": reviewed_count,
                "issues": issue_counts
            }
        except Exception as e:
            logger.error(f"Error getting review stats: {str(e)}")
            return {
                "flagged": 0,
                "reviewed": 0,
                "issues": {}
            }
    
    def get_pipeline_progress(self) -> Dict[str, Dict[str, Any]]:
        """
        Get pipeline progress statistics
        
        Returns:
            Dictionary with pipeline progress
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get counts by status
            cursor.execute("""
            SELECT status, COUNT(*) 
            FROM documents 
            GROUP BY status
            """)
            status_counts = {status: count for status, count in cursor.fetchall()}
            
            # Count total documents
            total_documents = sum(status_counts.values())
            
            # Map statuses to pipeline steps
            pipeline_progress = {
                "ocr": {"completed": 0, "total": total_documents, "active": False},
                "json": {"completed": 0, "total": total_documents, "active": False},
                "correction": {"completed": 0, "total": total_documents, "active": False},
                "dataset": {"completed": 0, "total": 0, "active": False},
                "training": {"completed": 0, "total": 100, "active": False}
            }
            
            # Count completed steps
            if "ocr_complete" in status_counts:
                pipeline_progress["ocr"]["completed"] = status_counts["ocr_complete"]
            
            if "json_complete" in status_counts:
                pipeline_progress["json"]["completed"] = status_counts["json_complete"]
            
            if "validated" in status_counts:
                pipeline_progress["correction"]["completed"] = status_counts["validated"]
            
            conn.close()
            
            return pipeline_progress
        except Exception as e:
            logger.error(f"Error getting pipeline progress: {str(e)}")
            return {
                "ocr": {"completed": 0, "total": 0, "active": False},
                "json": {"completed": 0, "total": 0, "active": False},
                "correction": {"completed": 0, "total": 0, "active": False},
                "dataset": {"completed": 0, "total": 0, "active": False},
                "training": {"completed": 0, "total": 100, "active": False}
            }
    
    def start_tracking(self, interval: float = 5.0):
        """
        Start background tracking of metrics
        
        Args:
            interval: Update interval in seconds
        """
        if self.tracking:
            logger.warning("Metrics tracking already started")
            return
        
        self.tracking = True
        self.tracking_thread = threading.Thread(target=self._tracking_loop, args=(interval,))
        self.tracking_thread.daemon = True
        self.tracking_thread.start()
        
        logger.info(f"Started metrics tracking (interval: {interval}s)")
    
    def stop_tracking(self):
        """Stop background tracking of metrics"""
        if not self.tracking:
            logger.warning("Metrics tracking not started")
            return
        
        self.tracking = False
        if self.tracking_thread and self.tracking_thread.is_alive():
            self.tracking_thread.join(timeout=5.0)
        
        logger.info("Stopped metrics tracking")
    
    def _tracking_loop(self, interval: float):
        """
        Background tracking loop
        
        Args:
            interval: Update interval in seconds
        """
        while self.tracking:
            try:
                # Record system metrics
                self._record_system_metrics()
                
                # Record document metrics
                self._record_document_metrics()
                
                # Sleep for interval
                time.sleep(interval)
            except Exception as e:
                logger.error(f"Error in metrics tracking loop: {str(e)}")
                time.sleep(1.0)
    
    def _record_system_metrics(self):
        """Record system metrics"""
        try:
            # Record CPU usage
            import psutil
            cpu_percent = psutil.cpu_percent()
            self.record_metric("resource", "cpu_usage", cpu_percent)
            
            # Record memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_gb = memory.used / (1024 ** 3)
            
            self.record_metric("resource", "memory_usage_percent", memory_percent)
            self.record_metric("resource", "memory_usage_gb", memory_gb)
            
            # Record GPU metrics if available
            if torch.cuda.is_available():
                try:
                    # Record GPU memory usage
                    gpu_memory_used = torch.cuda.memory_allocated() / (1024 ** 3)
                    gpu_memory_total = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
                    gpu_memory_percent = (gpu_memory_used / gpu_memory_total) * 100
                    
                    self.record_metric("resource", "gpu_memory_usage_percent", gpu_memory_percent)
                    self.record_metric("resource", "gpu_memory_usage_gb", gpu_memory_used)
                except Exception as e:
                    logger.error(f"Error recording GPU metrics: {str(e)}")
        except Exception as e:
            logger.error(f"Error recording system metrics: {str(e)}")
    
    def _record_document_metrics(self):
        """Record document metrics"""
        try:
            # Get document statistics
            review_stats = self.get_review_stats()
            
            # Record review metrics
            self.record_metric("quality", "documents_flagged", review_stats["flagged"])
            self.record_metric("quality", "documents_reviewed", review_stats["reviewed"])
            
            # Record issue metrics
            for issue_type, count in review_stats.get("issues", {}).items():
                self.record_metric("quality", f"issue_{issue_type}", count)
        except Exception as e:
            logger.error(f"Error recording document metrics: {str(e)}")

if __name__ == "__main__":
    # Test the metrics collector
    collector = MetricsCollector(db_path="test_metrics.db")
    
    # Register some test documents
    for i in range(10):
        collector.register_document(f"doc_{i}", f"resume_{i}.pdf")
    
    # Update document statuses
    for i in range(10):
        collector.update_document_status(f"doc_{i}", "ocr_complete")
    
    for i in range(8):
        collector.update_document_status(f"doc_{i}", "json_complete")
    
    for i in range(5):
        collector.update_document_status(f"doc_{i}", "validated")
    
    # Update confidence scores
    for i in range(10):
        collector.update_document_confidence(f"doc_{i}", ocr_confidence=85.0 - i * 3, json_confidence=90.0 - i * 5)
    
    # Flag some documents for review
    collector.flag_for_review("doc_6", "missing_contact", "Email and phone missing")
    collector.flag_for_review("doc_7", "schema_validation", "Invalid experience structure")
    collector.flag_for_review("doc_8", "multiple_corrections", "Required 3 correction attempts")
    
    # Get statistics
    review_stats = collector.get_review_stats()
    pipeline_progress = collector.get_pipeline_progress()
    
    print("Review Stats:", json.dumps(review_stats, indent=2))
    print("Pipeline Progress:", json.dumps(pipeline_progress, indent=2))