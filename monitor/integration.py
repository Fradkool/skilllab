"""
Integration module for SkillLab monitoring
Connects the monitoring system to the main pipeline
"""

import os
import threading
import sys
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

from utils.logger import setup_logger
from monitor.metrics import MetricsCollector

# Add project root to sys.path if needed
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

# Import the review database manager if available
try:
    from review.db_manager import ReviewDatabase
    HAS_REVIEW_DB = True
except ImportError:
    HAS_REVIEW_DB = False

logger = setup_logger("monitor_integration")

class MonitoringIntegration:
    """Integrates monitoring into the main pipeline"""
    
    def __init__(self, db_path: Optional[str] = None, enabled: bool = True):
        """
        Initialize monitoring integration
        
        Args:
            db_path: Path to SQLite database for metrics
            enabled: Whether monitoring is enabled
        """
        self.enabled = enabled
        self.metrics_collector = None
        self.review_db = None
        
        if enabled:
            # Set up metrics collector
            if db_path is None:
                # Use default path in project directory
                project_root = Path(__file__).parent.parent
                db_path = os.path.join(project_root, "data", "metrics.db")
                
                # Create directory if not exists
                os.makedirs(os.path.dirname(db_path), exist_ok=True)
            
            self.metrics_collector = MetricsCollector(db_path=db_path)
            
            # Initialize review database if available
            if HAS_REVIEW_DB:
                try:
                    self.review_db = ReviewDatabase()
                    logger.info("Review database integrated with monitoring")
                except Exception as e:
                    logger.error(f"Error initializing review database: {str(e)}")
            
            # Start metrics tracking
            self.metrics_collector.start_tracking()
            
            logger.info(f"Monitoring integration initialized with database at {db_path}")
        else:
            logger.info("Monitoring integration disabled")
    
    def register_document(self, document_id: str, filename: str) -> bool:
        """
        Register a document for monitoring
        
        Args:
            document_id: Document identifier
            filename: Original filename
            
        Returns:
            True if registered successfully, False otherwise
        """
        if not self.enabled or self.metrics_collector is None:
            return False
        
        success = self.metrics_collector.register_document(document_id, filename)
        
        # Also register in review database if available
        if success and self.review_db:
            try:
                # Check if document already exists in review database
                existing_doc = self.review_db.get_document_details(document_id)
                
                if not existing_doc:
                    # Create a connection to the review database
                    import sqlite3
                    from datetime import datetime
                    
                    conn = sqlite3.connect(self.review_db.db_path)
                    cursor = conn.cursor()
                    
                    # Insert basic document record
                    cursor.execute('''
                    INSERT INTO documents (
                        id, filename, status, ocr_confidence, json_confidence,
                        correction_count, flagged_for_review, review_status,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        document_id, filename, 'registered', 0.0, 0.0,
                        0, 0, 'none', datetime.now(), datetime.now()
                    ))
                    
                    conn.commit()
                    conn.close()
                    
                    logger.info(f"Document {document_id} registered in review database")
            except Exception as e:
                logger.error(f"Error registering document in review database: {str(e)}")
        
        return success
    
    def update_ocr_results(self, document_id: str, ocr_results: Dict[str, Any]) -> bool:
        """
        Update document with OCR results
        
        Args:
            document_id: Document identifier
            ocr_results: OCR extraction results
            
        Returns:
            True if updated successfully, False otherwise
        """
        if not self.enabled or self.metrics_collector is None:
            return False
        
        # Extract OCR confidence
        ocr_confidence = 0.0
        try:
            # Calculate average confidence from text elements
            confidences = []
            for page_result in ocr_results.get("page_results", []):
                for element in page_result.get("text_elements", []):
                    if "confidence" in element:
                        confidences.append(element["confidence"])
            
            if confidences:
                ocr_confidence = sum(confidences) / len(confidences) * 100
        except Exception as e:
            logger.error(f"Error calculating OCR confidence: {str(e)}")
        
        # Update document status and confidence
        success1 = self.metrics_collector.update_document_status(document_id, "ocr_complete")
        success2 = self.metrics_collector.update_document_confidence(document_id, ocr_confidence=ocr_confidence)
        
        # Check for OCR issues
        if ocr_confidence < 75:
            self.metrics_collector.flag_for_review(
                document_id, 
                "low_ocr_confidence", 
                f"OCR confidence score ({ocr_confidence:.1f}%) below threshold"
            )
        
        # Check for missing text
        if len(ocr_results.get("combined_text", "")) < 100:
            self.metrics_collector.flag_for_review(
                document_id,
                "ocr_extraction_failure",
                "Very little text extracted from document"
            )
        
        return success1 and success2
    
    def update_json_results(self, document_id: str, json_data: Dict[str, Any]) -> bool:
        """
        Update document with JSON generation results
        
        Args:
            document_id: Document identifier
            json_data: Generated JSON data
            
        Returns:
            True if updated successfully, False otherwise
        """
        if not self.enabled or self.metrics_collector is None:
            return False
        
        # Calculate JSON extraction confidence
        json_confidence = 0.0
        try:
            # Check for critical fields
            critical_fields = ["Name", "Email", "Phone"]
            field_count = sum(1 for field in critical_fields if json_data.get(field))
            critical_field_score = (field_count / len(critical_fields)) * 100
            
            # Check for skills
            skills_score = min(100, len(json_data.get("Skills", [])) * 10)
            
            # Check for experience
            experience_score = min(100, len(json_data.get("Experience", [])) * 25)
            
            # Calculate overall confidence
            json_confidence = (critical_field_score * 0.5) + (skills_score * 0.25) + (experience_score * 0.25)
        except Exception as e:
            logger.error(f"Error calculating JSON confidence: {str(e)}")
        
        # Update document status and confidence
        success1 = self.metrics_collector.update_document_status(document_id, "json_complete")
        success2 = self.metrics_collector.update_document_confidence(document_id, json_confidence=json_confidence)
        
        # Check for critical field issues
        critical_fields = ["Name", "Email", "Phone"]
        missing_fields = [field for field in critical_fields if not json_data.get(field)]
        
        if missing_fields:
            self.metrics_collector.flag_for_review(
                document_id,
                "missing_contact",
                f"Missing critical fields: {', '.join(missing_fields)}"
            )
        
        return success1 and success2
    
    def update_correction_results(self, document_id: str, correction_data: Dict[str, Any]) -> bool:
        """
        Update document with auto-correction results
        
        Args:
            document_id: Document identifier
            correction_data: Auto-correction results
            
        Returns:
            True if updated successfully, False otherwise
        """
        if not self.enabled or self.metrics_collector is None:
            return False
        
        # Increment correction count
        self.metrics_collector.increment_correction_count(document_id)
        
        # Check if validation was successful
        is_valid = correction_data.get("is_valid", False)
        coverage = correction_data.get("coverage", 0.0)
        
        if is_valid:
            # Update document status to validated
            success = self.metrics_collector.update_document_status(document_id, "validated")
        else:
            # Flag for review if validation failed
            self.metrics_collector.flag_for_review(
                document_id,
                "validation_failure",
                f"Validation failed with coverage {coverage:.1f}%"
            )
            success = True
        
        return success
    
    def record_training_progress(self, epoch: int, total_epochs: int, metrics: Dict[str, Any]) -> bool:
        """
        Record training progress
        
        Args:
            epoch: Current epoch
            total_epochs: Total number of epochs
            metrics: Training metrics
            
        Returns:
            True if recorded successfully, False otherwise
        """
        if not self.enabled or self.metrics_collector is None:
            return False
        
        # Record current epoch
        self.metrics_collector.record_metric(
            "training",
            "current_epoch",
            epoch
        )
        
        # Record progress percentage
        progress = (epoch / total_epochs) * 100
        self.metrics_collector.record_metric(
            "training",
            "progress",
            progress
        )
        
        # Record loss
        if "loss" in metrics:
            self.metrics_collector.record_metric(
                "training",
                "loss",
                metrics["loss"]
            )
        
        # Record validation loss if available
        if "val_loss" in metrics:
            self.metrics_collector.record_metric(
                "training",
                "val_loss",
                metrics["val_loss"]
            )
        
        return True
    
    def shutdown(self):
        """Shut down monitoring"""
        if self.enabled and self.metrics_collector is not None:
            self.metrics_collector.stop_tracking()
            logger.info("Monitoring integration shutdown")

# Singleton instance for global access
_monitoring_instance = None

def get_monitoring() -> Optional[MonitoringIntegration]:
    """
    Get the monitoring integration instance
    
    Returns:
        MonitoringIntegration instance or None if not initialized
    """
    return _monitoring_instance

def initialize_monitoring(db_path: Optional[str] = None, enabled: bool = True) -> MonitoringIntegration:
    """
    Initialize the monitoring integration
    
    Args:
        db_path: Path to SQLite database for metrics
        enabled: Whether monitoring is enabled
        
    Returns:
        MonitoringIntegration instance
    """
    global _monitoring_instance
    if _monitoring_instance is None:
        _monitoring_instance = MonitoringIntegration(db_path=db_path, enabled=enabled)
    return _monitoring_instance

def shutdown_monitoring():
    """Shut down monitoring"""
    global _monitoring_instance
    if _monitoring_instance is not None:
        _monitoring_instance.shutdown()
        _monitoring_instance = None