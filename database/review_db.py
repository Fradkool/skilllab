"""
Review database for SkillLab
Manages the storage and retrieval of review data
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, timedelta

from .core import BaseRepository, DatabaseConnection
from config import get_config

# Setup logger
logger = logging.getLogger(__name__)

# Schema definition
REVIEW_SCHEMA = """
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

-- Review feedback table
CREATE TABLE IF NOT EXISTS review_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id TEXT,
    status TEXT,
    changes_made INTEGER,
    reason TEXT,
    fields_corrected TEXT,
    timestamp TIMESTAMP,
    reviewer TEXT,
    FOREIGN KEY (document_id) REFERENCES documents(id)
);

-- Field corrections table
CREATE TABLE IF NOT EXISTS field_corrections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id TEXT,
    field_name TEXT,
    original_value TEXT,
    corrected_value TEXT,
    timestamp TIMESTAMP,
    FOREIGN KEY (document_id) REFERENCES documents(id)
);
"""

class ReviewRepository(BaseRepository):
    """Repository for review data"""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize review repository
        
        Args:
            db_path: Path to database (None to use configured path)
        """
        config = get_config()
        review_db_path = db_path or config.review.db_path
        super().__init__(DatabaseConnection(review_db_path))
        
        # Initialize database if needed
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema"""
        self._create_database(REVIEW_SCHEMA)
        
    def load_documents_from_fs(self) -> int:
        """
        Load existing documents from filesystem
        
        Returns:
            Number of documents loaded
        """
        try:
            # Get project root
            project_root = Path(__file__).parent.parent
            
            # Paths to check for documents
            output_dir = os.path.join(project_root, "data", "output")
            validated_json_dir = os.path.join(output_dir, "validated_json")
            json_results_dir = os.path.join(output_dir, "json_results")
            ocr_results_dir = os.path.join(output_dir, "ocr_results")
            
            # Check if any of these directories exist
            if not (os.path.exists(validated_json_dir) or os.path.exists(json_results_dir) or os.path.exists(ocr_results_dir)):
                logger.warning("No document directories found to import")
                return 0
            
            # Get existing document IDs in database
            existing_docs = self.db.fetch_all("SELECT id FROM documents")
            existing_ids = [row["id"] for row in existing_docs]
            
            # Track documents added
            documents_added = 0
            
            # Process validated JSON documents
            if os.path.exists(validated_json_dir):
                for file_name in os.listdir(validated_json_dir):
                    if file_name.endswith("_validated.json"):
                        try:
                            # Extract document ID
                            doc_id = file_name.replace("_validated.json", "")
                            
                            # Skip if already in database
                            if doc_id in existing_ids:
                                continue
                            
                            # Parse JSON file
                            file_path = os.path.join(validated_json_dir, file_name)
                            with open(file_path, 'r', encoding='utf-8') as f:
                                doc_data = json.load(f)
                            
                            # Check if document has validation info
                            validation = doc_data.get('validation', {})
                            is_valid = validation.get('is_valid', False)
                            
                            # Add to database if flagged for review
                            if not is_valid or validation.get('correction_attempts', 0) >= 3:
                                # Prepare document record
                                doc_record = {
                                    'id': doc_id,
                                    'filename': f"{doc_id}.pdf",
                                    'status': 'validated' if is_valid else 'needs_review',
                                    'ocr_confidence': validation.get('ocr_confidence', 0.0),
                                    'json_confidence': validation.get('coverage', 0.0) * 100,
                                    'correction_count': validation.get('correction_attempts', 0),
                                    'flagged_for_review': 1 if not is_valid else 0,
                                    'review_status': 'pending',
                                    'created_at': self._get_now(),
                                    'updated_at': self._get_now()
                                }
                                
                                # Insert document
                                with self.db.transaction() as conn:
                                    self.db.insert("documents", doc_record)
                                    
                                    # Add issues
                                    if not is_valid:
                                        self.add_document_issue(
                                            doc_id, 
                                            "validation_failure", 
                                            f"Validation failed with coverage {validation.get('coverage', 0.0) * 100:.1f}%"
                                        )
                                    
                                    if validation.get('correction_attempts', 0) >= 3:
                                        self.add_document_issue(
                                            doc_id,
                                            "multiple_corrections",
                                            f"Required {validation.get('correction_attempts', 0)} correction attempts"
                                        )
                                
                                documents_added += 1
                        except Exception as e:
                            logger.error(f"Error processing {file_name}: {e}")
            
            # Process OCR results
            if os.path.exists(ocr_results_dir):
                for file_name in os.listdir(ocr_results_dir):
                    if file_name.endswith("_ocr.json"):
                        try:
                            # Extract document ID
                            doc_id = file_name.replace("_ocr.json", "")
                            
                            # Skip if already in database
                            if doc_id in existing_ids:
                                continue
                            
                            # Parse JSON file
                            file_path = os.path.join(ocr_results_dir, file_name)
                            with open(file_path, 'r', encoding='utf-8') as f:
                                ocr_data = json.load(f)
                            
                            # Calculate average OCR confidence
                            confidences = []
                            for page_result in ocr_data.get("page_results", []):
                                for element in page_result.get("text_elements", []):
                                    if "confidence" in element:
                                        confidences.append(element["confidence"])
                            
                            ocr_confidence = 0.0
                            if confidences:
                                ocr_confidence = sum(confidences) / len(confidences) * 100
                            
                            # Flag for review if OCR confidence is low
                            if ocr_confidence < 75:
                                # Prepare document record
                                doc_record = {
                                    'id': doc_id,
                                    'filename': os.path.basename(ocr_data.get("original_path", f"{doc_id}.pdf")),
                                    'status': 'ocr_complete',
                                    'ocr_confidence': ocr_confidence,
                                    'json_confidence': 0.0,
                                    'correction_count': 0,
                                    'flagged_for_review': 1,
                                    'review_status': 'pending',
                                    'created_at': self._get_now(),
                                    'updated_at': self._get_now()
                                }
                                
                                # Insert document
                                with self.db.transaction() as conn:
                                    self.db.insert("documents", doc_record)
                                    
                                    # Add issue
                                    self.add_document_issue(
                                        doc_id,
                                        "low_ocr_confidence",
                                        f"OCR confidence score ({ocr_confidence:.1f}%) below threshold"
                                    )
                                
                                documents_added += 1
                        except Exception as e:
                            logger.error(f"Error processing {file_name}: {e}")
            
            logger.info(f"Loaded {documents_added} documents from filesystem")
            return documents_added
        except Exception as e:
            logger.error(f"Error loading documents from filesystem: {e}")
            return 0
    
    def add_document(self, document: Dict[str, Any]) -> bool:
        """
        Add or update a document
        
        Args:
            document: Document record
            
        Returns:
            True if added/updated successfully, False otherwise
        """
        try:
            # Check if document already exists
            existing = self.db.fetch_one(
                "SELECT id FROM documents WHERE id = ?", 
                (document['id'],)
            )
            
            now = self._get_now()
            
            if existing:
                # Update existing document
                document['updated_at'] = now
                self.db.update(
                    "documents",
                    document,
                    "id = ?",
                    (document['id'],)
                )
            else:
                # Set timestamps if not provided
                if 'created_at' not in document:
                    document['created_at'] = now
                if 'updated_at' not in document:
                    document['updated_at'] = now
                
                # Insert new document
                self.db.insert("documents", document)
            
            logger.info(f"{'Updated' if existing else 'Added'} document: {document['id']}")
            return True
        except Exception as e:
            logger.error(f"Error adding/updating document {document.get('id')}: {e}")
            return False
    
    def add_document_issue(self, document_id: str, issue_type: str, details: str) -> bool:
        """
        Add an issue to a document
        
        Args:
            document_id: Document ID
            issue_type: Type of issue
            details: Issue details
            
        Returns:
            True if added successfully, False otherwise
        """
        try:
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
            
            # Update document flag
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
            
            logger.info(f"Added issue to document {document_id}: {issue_type}")
            return True
        except Exception as e:
            logger.error(f"Error adding issue to document {document_id}: {e}")
            return False
    
    def update_document_status(self, document_id: str, status: str) -> bool:
        """
        Update document status
        
        Args:
            document_id: Document ID
            status: New status (registered, ocr_complete, json_complete, validated, etc.)
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            self.db.update(
                "documents",
                {
                    "status": status,
                    "updated_at": self._get_now()
                },
                "id = ?",
                (document_id,)
            )
            
            logger.info(f"Updated document status: {document_id} -> {status}")
            return True
        except Exception as e:
            logger.error(f"Error updating document status {document_id}: {e}")
            return False
    
    def update_review_status(self, document_id: str, status: str) -> bool:
        """
        Update document review status
        
        Args:
            document_id: Document ID
            status: Review status (pending, in_progress, approved, rejected, completed)
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            # Update document
            self.db.update(
                "documents",
                {
                    "review_status": status,
                    "updated_at": self._get_now()
                },
                "id = ?",
                (document_id,)
            )
            
            # If approved or rejected, mark as completed
            if status in ['approved', 'rejected']:
                self.db.update(
                    "documents",
                    {
                        "flagged_for_review": 0
                    },
                    "id = ?",
                    (document_id,)
                )
            
            logger.info(f"Updated review status for {document_id}: {status}")
            return True
        except Exception as e:
            logger.error(f"Error updating review status for {document_id}: {e}")
            return False
    
    def record_review_feedback(self, feedback: Dict[str, Any]) -> bool:
        """
        Record feedback from a review
        
        Args:
            feedback: Dictionary with feedback data
                - document_id: Document ID
                - status: Review status (approved, rejected)
                - changes_made: Boolean indicating if changes were made
                - reason: Reason for rejection
                - fields_corrected: Dictionary with corrected fields
                - timestamp: Timestamp (optional)
                - reviewer: Reviewer name (optional)
            
        Returns:
            True if recorded successfully, False otherwise
        """
        try:
            # Set defaults
            document_id = feedback.get('document_id')
            status = feedback.get('status')
            changes_made = 1 if feedback.get('changes_made', False) else 0
            reason = feedback.get('reason', '')
            
            # Handle fields_corrected
            if isinstance(feedback.get('fields_corrected'), dict):
                fields_corrected = self._serialize_json(feedback.get('fields_corrected'))
            else:
                fields_corrected = feedback.get('fields_corrected', '')
            
            timestamp = feedback.get('timestamp', self._get_now())
            reviewer = feedback.get('reviewer', 'system')
            
            # Insert feedback
            self.db.insert(
                "review_feedback",
                {
                    "document_id": document_id,
                    "status": status,
                    "changes_made": changes_made,
                    "reason": reason,
                    "fields_corrected": fields_corrected,
                    "timestamp": timestamp,
                    "reviewer": reviewer
                }
            )
            
            logger.info(f"Recorded review feedback for {document_id} ({status})")
            return True
        except Exception as e:
            logger.error(f"Error recording review feedback: {e}")
            return False
    
    def record_field_correction(
        self, 
        document_id: str, 
        field_name: str, 
        original_value: str, 
        corrected_value: str
    ) -> bool:
        """
        Record a field correction
        
        Args:
            document_id: Document ID
            field_name: Field name
            original_value: Original value
            corrected_value: Corrected value
            
        Returns:
            True if recorded successfully, False otherwise
        """
        try:
            # Insert correction record
            self.db.insert(
                "field_corrections",
                {
                    "document_id": document_id,
                    "field_name": field_name,
                    "original_value": original_value,
                    "corrected_value": corrected_value,
                    "timestamp": self._get_now()
                }
            )
            
            logger.info(f"Recorded field correction for {document_id}.{field_name}")
            return True
        except Exception as e:
            logger.error(f"Error recording field correction: {e}")
            return False
    
    def get_issue_types(self) -> List[str]:
        """
        Get all issue types in the database
        
        Returns:
            List of issue types
        """
        try:
            result = self.db.fetch_all(
                "SELECT DISTINCT issue_type FROM document_issues ORDER BY issue_type"
            )
            
            return [row["issue_type"] for row in result]
        except Exception as e:
            logger.error(f"Error getting issue types: {e}")
            return []
    
    def get_documents_for_review(self, issue_filter: str = 'All', limit: int = 100) -> List[Dict[str, Any]]:
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
                documents = self.db.fetch_all(
                    """
                    SELECT d.* 
                    FROM documents d
                    WHERE d.flagged_for_review = 1 AND d.review_status != 'completed'
                    ORDER BY d.created_at DESC
                    LIMIT ?
                    """, 
                    (limit,)
                )
            else:
                documents = self.db.fetch_all(
                    """
                    SELECT d.* 
                    FROM documents d
                    JOIN document_issues i ON d.id = i.document_id
                    WHERE d.flagged_for_review = 1 
                    AND d.review_status != 'completed'
                    AND i.issue_type = ?
                    GROUP BY d.id
                    ORDER BY d.created_at DESC
                    LIMIT ?
                    """, 
                    (issue_filter, limit)
                )
            
            # Fetch issues for each document
            for doc in documents:
                doc_id = doc["id"]
                issues = self.db.fetch_all(
                    """
                    SELECT issue_type, issue_details 
                    FROM document_issues
                    WHERE document_id = ?
                    """, 
                    (doc_id,)
                )
                
                # Format issues to match review adapter expectations
                formatted_issues = []
                for issue in issues:
                    formatted_issues.append({
                        "type": issue["issue_type"],
                        "details": issue["issue_details"]
                    })
                
                doc["issues"] = formatted_issues
            
            return documents
        except Exception as e:
            logger.error(f"Error getting documents for review: {e}")
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
            doc = self.db.fetch_one(
                """
                SELECT * 
                FROM documents
                WHERE id = ?
                """, 
                (document_id,)
            )
            
            if not doc:
                return None
            
            # Fetch issues
            issues = self.db.fetch_all(
                """
                SELECT issue_type, issue_details 
                FROM document_issues
                WHERE document_id = ?
                """, 
                (document_id,)
            )
            
            # Format issues to match review adapter expectations
            formatted_issues = []
            for issue in issues:
                formatted_issues.append({
                    "type": issue["issue_type"],
                    "details": issue["issue_details"]
                })
            
            doc["issues"] = formatted_issues
            
            # Try to find image paths from filesystem
            project_root = Path(__file__).parent.parent
            validated_json_dir = os.path.join(project_root, "data", "output", "validated_json")
            json_path = os.path.join(validated_json_dir, f"{document_id}_validated.json")
            
            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                    if 'image_paths' in json_data:
                        doc['image_paths'] = json_data['image_paths']
            
            # If no image paths found, try OCR results
            if 'image_paths' not in doc:
                ocr_dir = os.path.join(project_root, "data", "output", "ocr_results")
                ocr_path = os.path.join(ocr_dir, f"{document_id}_ocr.json")
                
                if os.path.exists(ocr_path):
                    with open(ocr_path, 'r', encoding='utf-8') as f:
                        ocr_data = json.load(f)
                        if 'image_paths' in ocr_data:
                            doc['image_paths'] = ocr_data['image_paths']
            
            return doc
        except Exception as e:
            logger.error(f"Error getting document details for {document_id}: {e}")
            return None
    
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
            doc_stats = self.db.fetch_one(
                """
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN flagged_for_review = 1 THEN 1 ELSE 0 END) as flagged,
                    SUM(CASE WHEN review_status IN ('approved', 'rejected', 'completed') THEN 1 ELSE 0 END) as reviewed
                FROM documents
                """
            )
            
            if doc_stats:
                stats["total_documents"] = doc_stats["total"]
                stats["flagged_documents"] = doc_stats["flagged"]
                stats["reviewed_documents"] = doc_stats["reviewed"]
            
            # Issue statistics
            issue_results = self.db.fetch_all(
                """
                SELECT issue_type, COUNT(*) as count
                FROM document_issues
                GROUP BY issue_type
                ORDER BY count DESC
                """
            )
            
            for row in issue_results:
                stats["issue_stats"][row["issue_type"]] = row["count"]
            
            # Pipeline statistics
            pipeline_stats = self.db.fetch_all(
                """
                SELECT status, COUNT(*) as count
                FROM documents
                GROUP BY status
                """
            )
            
            for row in pipeline_stats:
                stats["pipeline_stats"][row["status"]] = row["count"]
            
            return stats
        except Exception as e:
            logger.error(f"Error getting dashboard stats: {e}")
            return stats
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get performance statistics
        
        Returns:
            Dictionary with performance statistics
        """
        stats = {
            "total_reviewed": 0,
            "approved": 0,
            "rejected": 0,
            "avg_corrections": 0,
            "improvement_metrics": {}
        }
        
        try:
            # Get review counts
            review_stats = self.db.fetch_one(
                """
                SELECT 
                    COUNT(*) as total_reviewed,
                    SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) as approved,
                    SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected
                FROM review_feedback
                """
            )
            
            if review_stats:
                stats["total_reviewed"] = review_stats["total_reviewed"]
                stats["approved"] = review_stats["approved"]
                stats["rejected"] = review_stats["rejected"]
            
            # Get average corrections
            avg_corrections = self.db.fetch_one(
                """
                SELECT AVG(correction_count) as avg_corrections
                FROM documents
                WHERE review_status IN ('approved', 'rejected')
                """
            )
            
            if avg_corrections and avg_corrections["avg_corrections"]:
                stats["avg_corrections"] = round(avg_corrections["avg_corrections"], 2)
            
            # Add improvement metrics
            improvement_metrics = self.get_improvement_metrics()
            stats["improvement_metrics"] = improvement_metrics
            
            return stats
        except Exception as e:
            logger.error(f"Error getting performance stats: {e}")
            return stats
    
    def get_review_history(self) -> List[Dict[str, Any]]:
        """
        Get review history
        
        Returns:
            List of review records
        """
        try:
            history = self.db.fetch_all(
                """
                SELECT * FROM review_feedback
                ORDER BY timestamp DESC
                """
            )
            
            return history
        except Exception as e:
            logger.error(f"Error getting review history: {e}")
            return []
    
    def get_error_analysis(self) -> Dict[str, Any]:
        """
        Get error analysis data
        
        Returns:
            Dictionary with error analysis
        """
        analysis = {
            "issue_counts": {},
            "field_errors": {}
        }
        
        try:
            # Get issue counts
            issue_counts = self.db.fetch_all(
                """
                SELECT issue_type, COUNT(*) as count
                FROM document_issues
                GROUP BY issue_type
                ORDER BY count DESC
                """
            )
            
            for row in issue_counts:
                analysis["issue_counts"][row["issue_type"]] = row["count"]
            
            # Get field errors
            field_errors = self.db.fetch_all(
                """
                SELECT field_name, COUNT(*) as count
                FROM field_corrections
                GROUP BY field_name
                ORDER BY count DESC
                """
            )
            
            for row in field_errors:
                analysis["field_errors"][row["field_name"]] = row["count"]
            
            return analysis
        except Exception as e:
            logger.error(f"Error getting error analysis: {e}")
            return analysis
    
    def get_improvement_metrics(self) -> Dict[str, Any]:
        """
        Get metrics showing improvement over time
        
        Returns:
            Dictionary with improvement metrics
        """
        metrics = {
            "weekly_accuracy": [],
            "model_contribution": {}
        }
        
        try:
            # Get weekly accuracy (past 8 weeks)
            current_date = datetime.now()
            
            for i in range(8):
                start_date = (current_date - timedelta(days=(i+1)*7)).isoformat()
                end_date = (current_date - timedelta(days=i*7)).isoformat()
                
                # Count documents in this period
                period_docs = self.db.fetch_one(
                    """
                    SELECT COUNT(*) as total
                    FROM documents
                    WHERE created_at >= ? AND created_at < ?
                    """, 
                    (start_date, end_date)
                )
                
                total = period_docs["total"] if period_docs else 0
                
                # Count non-flagged documents
                valid_docs = self.db.fetch_one(
                    """
                    SELECT COUNT(*) as valid
                    FROM documents
                    WHERE created_at >= ? AND created_at < ?
                    AND flagged_for_review = 0
                    """, 
                    (start_date, end_date)
                )
                
                valid = valid_docs["valid"] if valid_docs else 0
                
                accuracy = (valid / total) * 100 if total > 0 else 0
                
                metrics["weekly_accuracy"].append({
                    "week": f"Week -{i+1}",
                    "accuracy": round(accuracy, 1)
                })
            
            # Reverse to show oldest first
            metrics["weekly_accuracy"].reverse()
            
            # Get model contribution (average confidence scores)
            ocr_acc = self.db.fetch_one("SELECT AVG(ocr_confidence) as avg FROM documents")
            json_acc = self.db.fetch_one("SELECT AVG(json_confidence) as avg FROM documents")
            
            metrics["model_contribution"]["ocr_accuracy"] = round(ocr_acc["avg"] if ocr_acc and ocr_acc["avg"] else 0, 1)
            metrics["model_contribution"]["json_accuracy"] = round(json_acc["avg"] if json_acc and json_acc["avg"] else 0, 1)
            
            return metrics
        except Exception as e:
            logger.error(f"Error getting improvement metrics: {e}")
            return metrics
    
    def sync_review_data(self) -> Tuple[int, int]:
        """
        Synchronize review data with filesystem
        
        Returns:
            Tuple with (documents_synced, issues_synced)
        """
        # Call our load_documents_from_fs method
        docs_loaded = self.load_documents_from_fs()
        return (docs_loaded, 0)  # For now, we don't separately track issues