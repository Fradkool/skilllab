"""
Database Manager for SkillLab Review Interface
Handles interactions with the SQLite database for the review system
"""

import os
import json
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple

from utils.logger import setup_logger

# Setup logger
logger = setup_logger("review_db_manager")

class ReviewDatabase:
    """Database manager for the review interface"""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the review database
        
        Args:
            db_path: Path to SQLite database (default: review/review.db)
        """
        # Set default path if not provided
        if db_path is None:
            project_root = Path(__file__).parent.parent
            db_path = os.path.join(project_root, "review", "review.db")
        
        self.db_path = db_path
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Initialize database
        self._init_db()
        
        # Load existing documents from filesystem
        self._load_documents_from_fs()
    
    def _init_db(self):
        """Initialize the database schema"""
        logger.info(f"Initializing review database at {self.db_path}")
        
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
            
            # Create review_feedback table
            cursor.execute('''
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
            )
            ''')
            
            # Create field_corrections table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS field_corrections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id TEXT,
                field_name TEXT,
                original_value TEXT,
                corrected_value TEXT,
                timestamp TIMESTAMP,
                FOREIGN KEY (document_id) REFERENCES documents(id)
            )
            ''')
            
            conn.commit()
            conn.close()
            
            logger.info("Database schema initialized")
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")
    
    def _load_documents_from_fs(self):
        """Load existing documents from filesystem"""
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
                return
            
            # Create connection
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get existing document IDs in database
            cursor.execute("SELECT id FROM documents")
            existing_ids = [row[0] for row in cursor.fetchall()]
            
            # Load documents from validated_json directory
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
                                    'created_at': datetime.now(),
                                    'updated_at': datetime.now(),
                                    'image_paths': doc_data.get('image_paths', [])
                                }
                                
                                # Insert document
                                self._add_document_to_db(doc_record, cursor)
                                
                                # Add issues
                                if not is_valid:
                                    self._add_document_issue(
                                        doc_id, 
                                        "validation_failure", 
                                        f"Validation failed with coverage {validation.get('coverage', 0.0) * 100:.1f}%",
                                        cursor
                                    )
                                
                                if validation.get('correction_attempts', 0) >= 3:
                                    self._add_document_issue(
                                        doc_id,
                                        "multiple_corrections",
                                        f"Required {validation.get('correction_attempts', 0)} correction attempts",
                                        cursor
                                    )
                        except Exception as e:
                            logger.error(f"Error processing {file_name}: {str(e)}")
            
            # Load documents from OCR results 
            # (This is a simplified version - in a real system, we would check
            # for OCR quality and flag documents with poor OCR quality)
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
                                    'created_at': datetime.now(),
                                    'updated_at': datetime.now(),
                                    'image_paths': ocr_data.get("image_paths", [])
                                }
                                
                                # Insert document
                                self._add_document_to_db(doc_record, cursor)
                                
                                # Add issue
                                self._add_document_issue(
                                    doc_id,
                                    "low_ocr_confidence",
                                    f"OCR confidence score ({ocr_confidence:.1f}%) below threshold",
                                    cursor
                                )
                        except Exception as e:
                            logger.error(f"Error processing {file_name}: {str(e)}")
            
            conn.commit()
            conn.close()
            
            logger.info("Completed loading documents from filesystem")
        except Exception as e:
            logger.error(f"Error loading documents from filesystem: {str(e)}")
    
    def _add_document_to_db(self, doc_record: Dict[str, Any], cursor):
        """
        Add a document to the database
        
        Args:
            doc_record: Document record
            cursor: Database cursor
        """
        # Extract image paths to store separately
        image_paths = doc_record.pop('image_paths', []) if 'image_paths' in doc_record else []
        
        # Insert document
        cursor.execute('''
        INSERT INTO documents (
            id, filename, status, ocr_confidence, json_confidence,
            correction_count, flagged_for_review, review_status,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            doc_record['id'],
            doc_record['filename'],
            doc_record['status'],
            doc_record['ocr_confidence'],
            doc_record['json_confidence'],
            doc_record['correction_count'],
            doc_record['flagged_for_review'],
            doc_record['review_status'],
            doc_record['created_at'],
            doc_record['updated_at']
        ))
        
        # Store image paths in document record for later retrieval
        doc_record['image_paths'] = image_paths
    
    def _add_document_issue(self, doc_id: str, issue_type: str, details: str, cursor):
        """
        Add an issue to a document
        
        Args:
            doc_id: Document ID
            issue_type: Type of issue
            details: Issue details
            cursor: Database cursor
        """
        cursor.execute('''
        INSERT INTO document_issues (
            document_id, issue_type, issue_details, created_at
        ) VALUES (?, ?, ?, ?)
        ''', (doc_id, issue_type, details, datetime.now()))
    
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
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Prepare query based on filter
            if issue_filter == 'All':
                cursor.execute('''
                SELECT d.* FROM documents d
                WHERE d.flagged_for_review = 1 AND d.review_status != 'completed'
                ORDER BY d.created_at DESC
                LIMIT ?
                ''', (limit,))
            else:
                cursor.execute('''
                SELECT d.* FROM documents d
                JOIN document_issues i ON d.id = i.document_id
                WHERE d.flagged_for_review = 1 AND d.review_status != 'completed'
                AND i.issue_type = ?
                GROUP BY d.id
                ORDER BY d.created_at DESC
                LIMIT ?
                ''', (issue_filter, limit))
            
            # Fetch documents
            documents = []
            for row in cursor.fetchall():
                doc = dict(row)
                
                # Fetch issues for this document
                cursor.execute('''
                SELECT issue_type, issue_details FROM document_issues
                WHERE document_id = ?
                ''', (doc['id'],))
                
                issues = []
                for issue_row in cursor.fetchall():
                    issues.append({
                        'type': issue_row[0],
                        'details': issue_row[1]
                    })
                
                doc['issues'] = issues
                
                # Add to list
                documents.append(doc)
            
            conn.close()
            
            return documents
        except Exception as e:
            logger.error(f"Error getting documents for review: {str(e)}")
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
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Fetch document
            cursor.execute('''
            SELECT * FROM documents
            WHERE id = ?
            ''', (document_id,))
            
            row = cursor.fetchone()
            if not row:
                conn.close()
                return None
            
            doc = dict(row)
            
            # Fetch issues
            cursor.execute('''
            SELECT issue_type, issue_details FROM document_issues
            WHERE document_id = ?
            ''', (document_id,))
            
            issues = []
            for issue_row in cursor.fetchall():
                issues.append({
                    'type': issue_row[0],
                    'details': issue_row[1]
                })
            
            doc['issues'] = issues
            
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
            
            conn.close()
            
            return doc
        except Exception as e:
            logger.error(f"Error getting document details for {document_id}: {str(e)}")
            return None
    
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
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Update document status
            cursor.execute('''
            UPDATE documents SET
                status = ?,
                updated_at = ?
            WHERE id = ?
            ''', (status, datetime.now(), document_id))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Updated document status: {document_id} -> {status}")
            return True
        except Exception as e:
            logger.error(f"Error updating document status {document_id}: {str(e)}")
            return False
    
    def update_review_status(self, document_id: str, status: str) -> bool:
        """
        Update document review status
        
        Args:
            document_id: Document ID
            status: Review status (pending, in_progress, approved, rejected, etc.)
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Update document
            cursor.execute('''
            UPDATE documents SET
                review_status = ?,
                updated_at = ?
            WHERE id = ?
            ''', (status, datetime.now(), document_id))
            
            # If approved or rejected, mark as completed
            if status in ['approved', 'rejected']:
                cursor.execute('''
                UPDATE documents SET
                    flagged_for_review = 0
                WHERE id = ?
                ''', (document_id,))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Updated review status for {document_id}: {status}")
            return True
        except Exception as e:
            logger.error(f"Error updating review status for {document_id}: {str(e)}")
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
                - fields_corrected: JSON string with corrected fields
                - timestamp: Timestamp (optional)
                - reviewer: Reviewer name (optional)
            
        Returns:
            True if recorded successfully, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Set defaults
            document_id = feedback.get('document_id')
            status = feedback.get('status')
            changes_made = 1 if feedback.get('changes_made', False) else 0
            reason = feedback.get('reason', '')
            fields_corrected = json.dumps(feedback.get('fields_corrected', {})) if isinstance(feedback.get('fields_corrected'), dict) else feedback.get('fields_corrected', '')
            timestamp = feedback.get('timestamp', datetime.now())
            reviewer = feedback.get('reviewer', 'system')
            
            # Insert feedback
            cursor.execute('''
            INSERT INTO review_feedback (
                document_id, status, changes_made, reason,
                fields_corrected, timestamp, reviewer
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                document_id, status, changes_made, reason,
                fields_corrected, timestamp, reviewer
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Recorded review feedback for {document_id} ({status})")
            return True
        except Exception as e:
            logger.error(f"Error recording review feedback: {str(e)}")
            return False
    
    def record_field_correction(self, document_id: str, field_name: str, 
                               original_value: str, corrected_value: str) -> bool:
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
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Insert correction record
            cursor.execute('''
            INSERT INTO field_corrections (
                document_id, field_name, original_value, corrected_value, timestamp
            ) VALUES (?, ?, ?, ?, ?)
            ''', (document_id, field_name, original_value, corrected_value, datetime.now()))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Recorded field correction for {document_id}.{field_name}")
            return True
        except Exception as e:
            logger.error(f"Error recording field correction: {str(e)}")
            return False
    
    def get_issue_types(self) -> List[str]:
        """
        Get all issue types in the database
        
        Returns:
            List of issue types
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT DISTINCT issue_type FROM document_issues
            ORDER BY issue_type
            ''')
            
            issue_types = [row[0] for row in cursor.fetchall()]
            
            conn.close()
            
            return issue_types
        except Exception as e:
            logger.error(f"Error getting issue types: {str(e)}")
            return []
    
    def get_dashboard_stats(self) -> Dict[str, Any]:
        """
        Get statistics for the dashboard
        
        Returns:
            Dictionary with dashboard statistics
        """
        stats = {
            'total_documents': 0,
            'flagged_documents': 0,
            'reviewed_documents': 0,
            'issue_stats': {},
            'pipeline_stats': {}
        }
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get document counts
            cursor.execute("SELECT COUNT(*) FROM documents")
            stats['total_documents'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM documents WHERE flagged_for_review = 1")
            stats['flagged_documents'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM documents WHERE review_status IN ('approved', 'rejected')")
            stats['reviewed_documents'] = cursor.fetchone()[0]
            
            # Get issue statistics
            cursor.execute('''
            SELECT issue_type, COUNT(*) FROM document_issues
            GROUP BY issue_type
            ''')
            
            for row in cursor.fetchall():
                stats['issue_stats'][row[0]] = row[1]
            
            # Get pipeline statistics
            cursor.execute('''
            SELECT status, COUNT(*) FROM documents
            GROUP BY status
            ''')
            
            for row in cursor.fetchall():
                stats['pipeline_stats'][row[0]] = row[1]
            
            conn.close()
            
            return stats
        except Exception as e:
            logger.error(f"Error getting dashboard stats: {str(e)}")
            return stats
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get performance statistics
        
        Returns:
            Dictionary with performance statistics
        """
        stats = {
            'total_reviewed': 0,
            'approved': 0,
            'rejected': 0,
            'avg_corrections': 0
        }
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get review counts
            cursor.execute("SELECT COUNT(*) FROM review_feedback")
            stats['total_reviewed'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM review_feedback WHERE status = 'approved'")
            stats['approved'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM review_feedback WHERE status = 'rejected'")
            stats['rejected'] = cursor.fetchone()[0]
            
            # Get average corrections
            cursor.execute('''
            SELECT AVG(correction_count) FROM documents
            WHERE review_status IN ('approved', 'rejected')
            ''')
            
            avg_corrections = cursor.fetchone()[0]
            stats['avg_corrections'] = round(avg_corrections, 2) if avg_corrections else 0
            
            conn.close()
            
            return stats
        except Exception as e:
            logger.error(f"Error getting performance stats: {str(e)}")
            return stats
    
    def get_review_history(self) -> List[Dict[str, Any]]:
        """
        Get review history
        
        Returns:
            List of review records
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT * FROM review_feedback
            ORDER BY timestamp DESC
            ''')
            
            history = [dict(row) for row in cursor.fetchall()]
            
            conn.close()
            
            return history
        except Exception as e:
            logger.error(f"Error getting review history: {str(e)}")
            return []
    
    def get_error_analysis(self) -> Dict[str, Any]:
        """
        Get error analysis data
        
        Returns:
            Dictionary with error analysis
        """
        analysis = {
            'issue_counts': {},
            'field_errors': {}
        }
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get issue counts
            cursor.execute('''
            SELECT issue_type, COUNT(*) FROM document_issues
            GROUP BY issue_type
            ''')
            
            for row in cursor.fetchall():
                analysis['issue_counts'][row[0]] = row[1]
            
            # Get field errors
            cursor.execute('''
            SELECT field_name, COUNT(*) FROM field_corrections
            GROUP BY field_name
            ''')
            
            for row in cursor.fetchall():
                analysis['field_errors'][row[0]] = row[1]
            
            conn.close()
            
            return analysis
        except Exception as e:
            logger.error(f"Error getting error analysis: {str(e)}")
            return analysis
    
    def get_improvement_metrics(self) -> Dict[str, Any]:
        """
        Get metrics showing improvement over time
        
        Returns:
            Dictionary with improvement metrics
        """
        metrics = {
            'weekly_accuracy': [],
            'model_contribution': {}
        }
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get weekly accuracy (past 8 weeks)
            current_date = datetime.now()
            
            for i in range(8):
                start_date = current_date - timedelta(days=(i+1)*7)
                end_date = current_date - timedelta(days=i*7)
                
                cursor.execute('''
                SELECT COUNT(*) FROM documents
                WHERE created_at >= ? AND created_at < ?
                ''', (start_date, end_date))
                
                total = cursor.fetchone()[0]
                
                cursor.execute('''
                SELECT COUNT(*) FROM documents
                WHERE created_at >= ? AND created_at < ?
                AND flagged_for_review = 0
                ''', (start_date, end_date))
                
                valid = cursor.fetchone()[0]
                
                if total > 0:
                    accuracy = (valid / total) * 100
                else:
                    accuracy = 0
                
                metrics['weekly_accuracy'].append({
                    'week': f"Week -{i+1}",
                    'accuracy': round(accuracy, 1)
                })
            
            # Reverse to show oldest first
            metrics['weekly_accuracy'].reverse()
            
            # Get model contribution (average confidence scores)
            cursor.execute("SELECT AVG(ocr_confidence) FROM documents")
            ocr_accuracy = cursor.fetchone()[0]
            metrics['model_contribution']['ocr_accuracy'] = round(ocr_accuracy or 0, 1)
            
            cursor.execute("SELECT AVG(json_confidence) FROM documents")
            json_accuracy = cursor.fetchone()[0]
            metrics['model_contribution']['json_accuracy'] = round(json_accuracy or 0, 1)
            
            conn.close()
            
            return metrics
        except Exception as e:
            logger.error(f"Error getting improvement metrics: {str(e)}")
            return metrics