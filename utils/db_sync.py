"""
Database Synchronization Utility
Syncs data between metrics database and review database
"""

import os
import sys
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from utils.logger import setup_logger

# Setup logger
logger = setup_logger("db_sync")

def sync_databases(metrics_db_path: Optional[str] = None, review_db_path: Optional[str] = None) -> Tuple[int, int]:
    """
    Synchronize data between metrics and review databases
    
    Args:
        metrics_db_path: Path to metrics SQLite database (default: data/metrics.db)
        review_db_path: Path to review SQLite database (default: review/review.db)
        
    Returns:
        Tuple with (documents_synced, issues_synced)
    """
    # Set default paths if not provided
    if metrics_db_path is None:
        metrics_db_path = os.path.join(project_root, "data", "metrics.db")
    
    if review_db_path is None:
        review_db_path = os.path.join(project_root, "review", "review.db")
    
    # Check if databases exist
    metrics_exists = os.path.exists(metrics_db_path)
    review_exists = os.path.exists(review_db_path)
    
    if not metrics_exists and not review_exists:
        logger.error("Neither metrics nor review database exists")
        return (0, 0)
    
    # Track sync counts
    docs_synced = 0
    issues_synced = 0
    
    try:
        # Open connections to both databases
        metrics_conn = sqlite3.connect(metrics_db_path) if metrics_exists else None
        review_conn = sqlite3.connect(review_db_path) if review_exists else None
        
        # If both databases exist, sync from metrics to review
        if metrics_conn and review_conn:
            metrics_cursor = metrics_conn.cursor()
            review_cursor = review_conn.cursor()
            
            # Get all documents from metrics database
            metrics_cursor.execute("SELECT id, filename, status, ocr_confidence, json_confidence, correction_count, flagged_for_review, review_status, created_at, updated_at FROM documents")
            metrics_docs = metrics_cursor.fetchall()
            
            # Get existing document IDs in review database
            review_cursor.execute("SELECT id FROM documents")
            review_doc_ids = [row[0] for row in review_cursor.fetchall()]
            
            # For each document in metrics, add to review if not exists
            for doc in metrics_docs:
                doc_id = doc[0]
                
                if doc_id not in review_doc_ids:
                    # Insert document into review database
                    review_cursor.execute('''
                    INSERT INTO documents (
                        id, filename, status, ocr_confidence, json_confidence,
                        correction_count, flagged_for_review, review_status,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', doc)
                    
                    docs_synced += 1
                else:
                    # Update existing document with latest metrics
                    review_cursor.execute('''
                    UPDATE documents SET
                        status = ?,
                        ocr_confidence = ?,
                        json_confidence = ?,
                        correction_count = ?,
                        flagged_for_review = ?,
                        review_status = ?,
                        updated_at = ?
                    WHERE id = ?
                    ''', (doc[2], doc[3], doc[4], doc[5], doc[6], doc[7], doc[9], doc_id))
            
            # Sync issues from metrics to review
            metrics_cursor.execute("SELECT document_id, issue_type, issue_details, created_at FROM document_issues")
            metrics_issues = metrics_cursor.fetchall()
            
            # Get existing issues in review database
            review_cursor.execute("SELECT document_id, issue_type, issue_details FROM document_issues")
            review_issues = set((row[0], row[1], row[2]) for row in review_cursor.fetchall())
            
            # Add new issues to review database
            for issue in metrics_issues:
                doc_id, issue_type, issue_details = issue[0], issue[1], issue[2]
                
                if (doc_id, issue_type, issue_details) not in review_issues:
                    # Insert issue into review database
                    review_cursor.execute('''
                    INSERT INTO document_issues (
                        document_id, issue_type, issue_details, created_at
                    ) VALUES (?, ?, ?, ?)
                    ''', issue)
                    
                    issues_synced += 1
            
            # Sync completed reviews back to metrics database
            review_cursor.execute('''
            SELECT d.id, d.review_status, rf.status 
            FROM documents d
            LEFT JOIN review_feedback rf ON d.id = rf.document_id
            WHERE d.review_status IN ('approved', 'rejected', 'completed')
            ''')
            completed_reviews = review_cursor.fetchall()
            
            # Update metrics database with review status
            for review in completed_reviews:
                doc_id, review_status, feedback_status = review
                status = feedback_status if feedback_status else review_status
                
                metrics_cursor.execute('''
                UPDATE documents SET
                    review_status = ?,
                    updated_at = ?
                WHERE id = ?
                ''', (status, datetime.now(), doc_id))
            
            # Commit changes
            review_conn.commit()
            metrics_conn.commit()
        
        # Close connections
        if metrics_conn:
            metrics_conn.close()
        
        if review_conn:
            review_conn.close()
        
        logger.info(f"Database sync complete. Synced {docs_synced} documents and {issues_synced} issues.")
        return (docs_synced, issues_synced)
    
    except Exception as e:
        logger.error(f"Error syncing databases: {str(e)}")
        return (0, 0)

if __name__ == "__main__":
    # Run sync as standalone script
    print("Starting database synchronization...")
    docs, issues = sync_databases()
    print(f"Sync complete. Synced {docs} documents and {issues} issues.")