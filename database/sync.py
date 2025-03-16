"""
Database Synchronization for SkillLab
Syncs data between metrics database and review database
"""

import logging
from typing import Tuple, Optional
from datetime import datetime

from .metrics_db import MetricsRepository
from .review_db import ReviewRepository
from config import get_config

# Setup logger
logger = logging.getLogger(__name__)

def sync_databases(metrics_repo: Optional[MetricsRepository] = None,
                  review_repo: Optional[ReviewRepository] = None) -> Tuple[int, int]:
    """
    Synchronize data between metrics and review databases
    
    Args:
        metrics_repo: Metrics repository (None to create a new instance)
        review_repo: Review repository (None to create a new instance)
        
    Returns:
        Tuple with (documents_synced, issues_synced)
    """
    # Create repositories if not provided
    metrics_db = metrics_repo or MetricsRepository()
    review_db = review_repo or ReviewRepository()
    
    # Track sync counts
    docs_synced = 0
    issues_synced = 0
    
    try:
        # First, load any new documents from filesystem
        docs_loaded_review = review_db.load_documents_from_fs()
        if docs_loaded_review > 0:
            logger.info(f"Loaded {docs_loaded_review} documents from filesystem to review database")
        
        # Sync from metrics to review
        # Get all documents from metrics database
        metrics_documents = metrics_db.get_review_queue('All', limit=1000)
        
        # Get existing document IDs in review database
        review_documents = review_db.get_documents_for_review('All', limit=1000)
        review_doc_ids = [doc["id"] for doc in review_documents]
        
        # For each document in metrics, add to review if not exists
        for doc in metrics_documents:
            doc_id = doc["id"]
            
            if doc_id not in review_doc_ids:
                # Add document to review database
                review_db.add_document(doc)
                docs_synced += 1
            else:
                # Update existing document with latest metrics
                update_data = {
                    "id": doc_id,
                    "status": doc["status"],
                    "ocr_confidence": doc["ocr_confidence"],
                    "json_confidence": doc["json_confidence"],
                    "correction_count": doc["correction_count"],
                    "flagged_for_review": doc["flagged_for_review"],
                    "review_status": doc["review_status"],
                    "updated_at": doc["updated_at"]
                }
                review_db.add_document(update_data)
        
        # Sync issues from metrics to review
        for doc in metrics_documents:
            doc_id = doc["id"]
            
            # Get issues for this document
            if "issues" in doc and doc["issues"]:
                for issue in doc["issues"]:
                    # Handle different issue structure formats
                    if "type" in issue and "details" in issue:
                        issue_type = issue["type"]
                        issue_details = issue["details"]
                    elif "issue_type" in issue and "issue_details" in issue:
                        issue_type = issue["issue_type"]
                        issue_details = issue["issue_details"]
                    else:
                        logger.warning(f"Unknown issue format: {issue}")
                        continue
                    
                    # Check if issue exists in review database
                    # (This is a simplified check, in a production system 
                    # we would track issue IDs for more robust comparison)
                    existing_issue = False
                    for review_doc in review_documents:
                        if review_doc["id"] == doc_id:
                            for rev_issue in review_doc.get("issues", []):
                                # Handle different issue structure formats
                                rev_type = rev_issue.get("type", rev_issue.get("issue_type", ""))
                                rev_details = rev_issue.get("details", rev_issue.get("issue_details", ""))
                                
                                if (rev_type == issue_type and rev_details == issue_details):
                                    existing_issue = True
                                    break
                    
                    if not existing_issue:
                        # Add issue to review database
                        review_db.add_document_issue(doc_id, issue_type, issue_details)
                        issues_synced += 1
        
        # Sync completed reviews back to metrics database
        # Get documents with review status in the review database
        reviewed_docs = []
        for doc in review_documents:
            if doc["review_status"] in ["approved", "rejected", "completed"]:
                reviewed_docs.append(doc)
        
        # Update metrics database with review status
        for doc in reviewed_docs:
            doc_id = doc["id"]
            review_status = doc["review_status"]
            
            # Update metrics database
            metrics_db.update_document_status(doc_id, doc["status"])
            metrics_doc = metrics_db.get_document_details(doc_id)
            
            if metrics_doc and metrics_doc.get("review_status") != review_status:
                # Update metrics with review status
                metrics_db.db.update(
                    "documents",
                    {
                        "review_status": review_status,
                        "updated_at": datetime.now().isoformat()
                    },
                    "id = ?",
                    (doc_id,)
                )
        
        logger.info(f"Database sync complete. Synced {docs_synced} documents and {issues_synced} issues.")
        return (docs_synced, issues_synced)
    
    except Exception as e:
        logger.error(f"Error syncing databases: {e}")
        return (0, 0)
    finally:
        # Close connections
        metrics_db.close()
        review_db.close()

def sync_review_data() -> Tuple[int, int]:
    """
    Synchronize review data with filesystem and metrics database
    
    Returns:
        Tuple with (documents_synced, issues_synced)
    """
    # Create a review repository
    review_db = ReviewRepository()
    
    try:
        # Load any new documents from filesystem
        docs_loaded = review_db.load_documents_from_fs()
        
        # Then sync with metrics database
        metrics_db = MetricsRepository()
        try:
            docs_synced, issues_synced = sync_databases(metrics_db, review_db)
            total_docs = docs_loaded + docs_synced
            
            logger.info(f"Review data sync complete. Loaded {docs_loaded} from filesystem, synced {docs_synced} from metrics.")
            return (total_docs, issues_synced)
        finally:
            metrics_db.close()
    
    except Exception as e:
        logger.error(f"Error syncing review data: {e}")
        return (0, 0)
    finally:
        # Close connection
        review_db.close()

if __name__ == "__main__":
    # Enable logging
    logging.basicConfig(level=logging.INFO)
    
    # Run sync as standalone script
    print("Starting database synchronization...")
    docs, issues = sync_databases()
    print(f"Sync complete. Synced {docs} documents and {issues} issues.")