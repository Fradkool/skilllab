"""
Review API for SkillLab
Provides high-level functions for document review and feedback
"""

import os
import json
import time
from typing import Dict, List, Any, Optional, Union, Tuple
from pathlib import Path

from config import get_config, AppConfig
from database.review_db import ReviewRepository
from database.sync import sync_databases, sync_review_data

def get_review_repository() -> ReviewRepository:
    """
    Get a review repository instance
    
    Returns:
        Review repository object
    """
    return ReviewRepository()

def get_review_queue(
    issue_filter: str = 'All',
    limit: int = 100,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """
    Get documents flagged for review
    
    Args:
        issue_filter: Filter by issue type ('All' for no filter)
        limit: Maximum number of documents to return
        offset: Offset for pagination
        
    Returns:
        List of document records
    """
    # Ensure databases are in sync
    sync_review_data()
    
    # Get documents from database
    review_repo = get_review_repository()
    try:
        documents = review_repo.get_documents_for_review(issue_filter, limit)
        return documents
    finally:
        review_repo.close()

def get_document_details(document_id: str) -> Optional[Dict[str, Any]]:
    """
    Get detailed information for a specific document
    
    Args:
        document_id: Document ID
        
    Returns:
        Document details or None if not found
    """
    review_repo = get_review_repository()
    try:
        document = review_repo.get_document_details(document_id)
        
        if not document:
            return None
        
        # Get configuration for paths
        config = get_config()
        
        # Add image and JSON paths
        document['image_path'] = []
        if 'image_paths' in document:
            document['image_path'] = document['image_paths']
        
        # Try to get JSON data
        json_path = os.path.join(config.paths.output_dir, "validated_json", f"{document_id}_validated.json")
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                try:
                    document['json_data'] = json.load(f)
                except json.JSONDecodeError:
                    document['json_data'] = None
        
        # Try to get original OCR text
        ocr_path = os.path.join(config.paths.output_dir, "ocr_results", f"{document_id}_ocr.json")
        if os.path.exists(ocr_path):
            with open(ocr_path, 'r', encoding='utf-8') as f:
                try:
                    ocr_data = json.load(f)
                    document['ocr_text'] = ocr_data.get('combined_text', '')
                except json.JSONDecodeError:
                    document['ocr_text'] = ''
        
        return document
    finally:
        review_repo.close()

def update_document_status(document_id: str, status: str) -> bool:
    """
    Update the status of a document
    
    Args:
        document_id: Document ID
        status: New status ('approved', 'rejected', 'pending', etc.)
        
    Returns:
        True if successful, False otherwise
    """
    review_repo = get_review_repository()
    try:
        return review_repo.update_review_status(document_id, status)
    finally:
        review_repo.close()

def approve_document(document_id: str, changes_made: bool = False) -> bool:
    """
    Approve a document
    
    Args:
        document_id: Document ID
        changes_made: Whether changes were made during review
        
    Returns:
        True if approved successfully, False otherwise
    """
    # Update document status to 'approved'
    return save_review_feedback(
        document_id=document_id,
        status='approved',
        corrections={},
        changes_made=changes_made
    )

def reject_document(document_id: str, reason: str) -> bool:
    """
    Reject a document
    
    Args:
        document_id: Document ID
        reason: Reason for rejection
        
    Returns:
        True if rejected successfully, False otherwise
    """
    # Update document status to 'rejected'
    return save_review_feedback(
        document_id=document_id,
        status='rejected',
        reason=reason
    )

def save_document_json(document_id: str, json_data: Dict[str, Any]) -> bool:
    """
    Save document JSON data
    
    Args:
        document_id: Document ID
        json_data: Updated JSON data
        
    Returns:
        True if saved successfully, False otherwise
    """
    # Save document JSON data
    return save_review_feedback(
        document_id=document_id,
        status='in_progress',
        json_data=json_data,
        changes_made=True
    )

def save_review_feedback(
    document_id: str,
    status: str,
    json_data: Optional[Dict[str, Any]] = None,
    corrections: Optional[Dict[str, Any]] = None,
    reason: Optional[str] = None,
    reviewer: Optional[str] = None,
    changes_made: bool = False
) -> bool:
    """
    Save feedback from document review
    
    Args:
        document_id: Document ID
        status: Review status ('approved', 'rejected', etc.)
        json_data: Updated JSON data (None to skip update)
        corrections: Field corrections (None if no corrections)
        reason: Reason for rejection (required if status is 'rejected')
        reviewer: Reviewer name (optional)
        changes_made: Whether changes were made during review
        
    Returns:
        True if successful, False otherwise
    """
    # Get configuration
    config = get_config()
    
    # Get database
    review_repo = get_review_repository()
    
    try:
        # Validate status
        if status not in ['approved', 'rejected', 'pending', 'in_progress']:
            return False
        
        # Require reason for rejection
        if status == 'rejected' and not reason:
            return False
        
        # Update document status
        success = review_repo.update_review_status(document_id, status)
        if not success:
            return False
        
        # Save JSON data if provided
        if json_data:
            # Save to validated_json directory
            json_path = os.path.join(config.paths.output_dir, "validated_json", f"{document_id}_validated.json")
            
            # Create validated JSON structure
            validated_json = {
                "resume_id": document_id,
                "json_data": json_data,
                "validation": {
                    "is_valid": True,
                    "reviewed": True,
                    "review_status": status
                }
            }
            
            # Get original JSON to preserve image paths
            if os.path.exists(json_path):
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        original = json.load(f)
                        # Preserve image paths
                        if 'image_paths' in original:
                            validated_json['image_paths'] = original['image_paths']
                except json.JSONDecodeError:
                    pass
            
            # Save updated JSON
            try:
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(validated_json, f, ensure_ascii=False, indent=2)
            except Exception:
                return False
        
        # Record field corrections if provided
        if corrections:
            for field_name, correction in corrections.items():
                original_value = correction.get('original', '')
                corrected_value = correction.get('corrected', '')
                review_repo.record_field_correction(document_id, field_name, original_value, corrected_value)
        
        # Record review feedback
        feedback_data = {
            'document_id': document_id,
            'status': status,
            'changes_made': changes_made or bool(json_data or corrections),
            'reason': reason or '',
            'fields_corrected': json.dumps(list(corrections.keys()) if corrections else []),
            'timestamp': review_repo._get_now(),
            'reviewer': reviewer or 'system'
        }
        
        success = review_repo.record_review_feedback(feedback_data)
        
        # Sync databases after update
        sync_databases()
        
        return success
    finally:
        review_repo.close()

def get_dashboard_stats() -> Dict[str, Any]:
    """
    Get statistics for the review dashboard
    
    Returns:
        Dictionary with dashboard statistics
    """
    review_repo = get_review_repository()
    try:
        return review_repo.get_dashboard_stats()
    finally:
        review_repo.close()

def get_review_history(limit: int = 100) -> List[Dict[str, Any]]:
    """
    Get review history
    
    Args:
        limit: Maximum number of records to return
        
    Returns:
        List of review history records
    """
    review_repo = get_review_repository()
    try:
        history = review_repo.get_review_history()
        return history[:limit] if len(history) > limit else history
    finally:
        review_repo.close()

def get_performance_stats() -> Dict[str, Any]:
    """
    Get performance statistics
    
    Returns:
        Dictionary with performance statistics
    """
    review_repo = get_review_repository()
    try:
        return review_repo.get_performance_stats()
    finally:
        review_repo.close()

def get_error_analysis() -> Dict[str, Any]:
    """
    Get error analysis data
    
    Returns:
        Dictionary with error analysis
    """
    review_repo = get_review_repository()
    try:
        return review_repo.get_error_analysis()
    finally:
        review_repo.close()

def get_improvement_metrics() -> Dict[str, Any]:
    """
    Get metrics showing improvement over time
    
    Returns:
        Dictionary with improvement metrics
    """
    review_repo = get_review_repository()
    try:
        return review_repo.get_improvement_metrics()
    finally:
        review_repo.close()

def recycle_for_training(document_id: str) -> bool:
    """
    Mark a reviewed document for inclusion in training data
    
    Args:
        document_id: Document ID
        
    Returns:
        True if successful, False otherwise
    """
    # Get configuration
    config = get_config()
    
    # Get document details
    document = get_document_details(document_id)
    if not document:
        return False
    
    # Check if document has been reviewed
    if document.get('review_status') not in ['approved']:
        return False
    
    # Check if JSON data exists
    if 'json_data' not in document or not document['json_data']:
        return False
    
    # Save to training dataset directory
    train_dir = os.path.join(config.paths.output_dir, "donut_dataset", "train")
    os.makedirs(train_dir, exist_ok=True)
    
    # Copy JSON data
    json_data = document['json_data']
    
    # Save as training data
    try:
        # Get original image paths
        image_paths = document.get('image_path', [])
        
        # Create training metadata
        from training.dataset_builder import DonutDatasetBuilder
        
        # Create a temporary dataset builder to format the JSON
        builder = DonutDatasetBuilder(
            validated_json_dir="",
            donut_dataset_dir="",
            task_name=config.dataset.task_name
        )
        
        # Format JSON for training
        formatted_json = builder._format_json_for_donut(json_data.get('json_data', {}))
        
        # For each image, create training sample
        for i, img_path in enumerate(image_paths):
            if not os.path.exists(img_path):
                continue
            
            # Copy image to training directory
            from PIL import Image
            img = Image.open(img_path)
            rgb_img = img.convert('RGB')
            
            # For multi-page, use index; for single page use only ID
            new_filename = f"{document_id}_{i}.jpg" if len(image_paths) > 1 else f"{document_id}.jpg"
            new_path = os.path.join(train_dir, new_filename)
            
            # Save image
            rgb_img.save(new_path, format='JPEG', quality=95)
            
            # Create metadata JSON
            metadata_path = os.path.join(train_dir, f"{document_id}{'_'+str(i) if len(image_paths) > 1 else ''}.json")
            
            # Format the answer using the template
            answer_str = builder.response_template.format(ANSWER=formatted_json)
            
            # Create metadata
            metadata = {
                "gt_parse": answer_str,
                "image_path": os.path.basename(new_path),
                "task_prompt": builder.task_prompt
            }
            
            # Save metadata
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        # Update index file
        index_path = os.path.join(os.path.dirname(train_dir), "train_index.txt")
        updated_index = []
        
        # Read existing index if it exists
        if os.path.exists(index_path):
            with open(index_path, 'r', encoding='utf-8') as f:
                updated_index = [line.strip() for line in f.readlines()]
        
        # Add new metadata filenames
        for i in range(len(image_paths)):
            index_file = f"{document_id}{'_'+str(i) if len(image_paths) > 1 else ''}.json"
            if index_file not in updated_index:
                updated_index.append(index_file)
        
        # Write updated index
        with open(index_path, 'w', encoding='utf-8') as f:
            for line in updated_index:
                f.write(line + "\n")
        
        # Update document status
        review_repo = get_review_repository()
        try:
            review_repo.update_document_status(document_id, "recycled_for_training")
        finally:
            review_repo.close()
        
        return True
    except Exception as e:
        return False

def load_documents_from_filesystem() -> int:
    """
    Load existing documents from filesystem
    
    Returns:
        Number of documents loaded
    """
    review_repo = get_review_repository()
    try:
        return review_repo.load_documents_from_fs()
    finally:
        review_repo.close()