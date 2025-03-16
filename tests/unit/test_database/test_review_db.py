"""
Unit tests for the review database repository
"""

import os
import sys
import pytest
import tempfile
import sqlite3
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from database.review_db import ReviewRepository
from database.core import DatabaseConnection


@pytest.fixture
def temp_db_path():
    """Create a temporary database file path"""
    with tempfile.NamedTemporaryFile(suffix='.db') as tmp:
        yield tmp.name


@pytest.fixture
def mock_config():
    """Mock configuration for testing"""
    with patch('database.review_db.get_config') as mock_get_config:
        config = MagicMock()
        config.review.db_path = ':memory:'
        mock_get_config.return_value = config
        yield config


@pytest.fixture
def review_repo(temp_db_path):
    """Create a review repository with a temporary database"""
    db_conn = DatabaseConnection(temp_db_path)
    repo = ReviewRepository(temp_db_path)
    yield repo
    # Clean up
    repo.close()


class TestReviewRepository:
    """Test the review database repository"""

    def test_init_database(self, review_repo):
        """Test database initialization"""
        # Check that tables were created
        with review_repo.db.transaction() as conn:
            # Check documents table
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='documents'")
            assert cursor.fetchone() is not None

            # Check document_issues table
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='document_issues'")
            assert cursor.fetchone() is not None

            # Check review_feedback table
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='review_feedback'")
            assert cursor.fetchone() is not None

            # Check field_corrections table
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='field_corrections'")
            assert cursor.fetchone() is not None

    def test_add_document(self, review_repo):
        """Test adding a document"""
        doc_id = "test_doc_123"
        document = {
            'id': doc_id,
            'filename': f"{doc_id}.pdf",
            'status': 'ocr_complete',
            'ocr_confidence': 85.5,
            'json_confidence': 75.0,
            'correction_count': 0,
            'flagged_for_review': 1,
            'review_status': 'pending',
        }

        # Add document
        result = review_repo.add_document(document)
        assert result is True

        # Retrieve document
        doc = review_repo.db.fetch_one(
            "SELECT * FROM documents WHERE id = ?", 
            (doc_id,)
        )
        
        assert doc is not None
        assert doc['id'] == doc_id
        assert doc['filename'] == f"{doc_id}.pdf"
        assert doc['status'] == 'ocr_complete'
        assert doc['ocr_confidence'] == 85.5
        assert doc['json_confidence'] == 75.0
        assert doc['correction_count'] == 0
        assert doc['flagged_for_review'] == 1
        assert doc['review_status'] == 'pending'
        assert 'created_at' in doc
        assert 'updated_at' in doc

        # Update document
        updated_doc = document.copy()
        updated_doc['status'] = 'json_complete'
        updated_doc['json_confidence'] = 90.0
        
        result = review_repo.add_document(updated_doc)
        assert result is True
        
        # Retrieve updated document
        doc = review_repo.db.fetch_one(
            "SELECT * FROM documents WHERE id = ?", 
            (doc_id,)
        )
        
        assert doc['status'] == 'json_complete'
        assert doc['json_confidence'] == 90.0

    def test_add_document_issue(self, review_repo):
        """Test adding a document issue"""
        # First add a document
        doc_id = "test_doc_456"
        document = {
            'id': doc_id,
            'filename': f"{doc_id}.pdf",
            'status': 'ocr_complete',
            'ocr_confidence': 65.5,  # Low confidence
            'json_confidence': 0.0,
            'correction_count': 0,
            'flagged_for_review': 0,  # Not flagged yet
            'review_status': 'pending',
        }
        
        review_repo.add_document(document)
        
        # Add issue
        issue_type = "low_ocr_confidence"
        issue_details = "OCR confidence score (65.5%) below threshold"
        
        result = review_repo.add_document_issue(doc_id, issue_type, issue_details)
        assert result is True
        
        # Check issue was added
        issues = review_repo.db.fetch_all(
            "SELECT * FROM document_issues WHERE document_id = ?",
            (doc_id,)
        )
        
        assert len(issues) == 1
        assert issues[0]['document_id'] == doc_id
        assert issues[0]['issue_type'] == issue_type
        assert issues[0]['issue_details'] == issue_details
        
        # Check document was flagged for review
        doc = review_repo.db.fetch_one(
            "SELECT flagged_for_review, review_status FROM documents WHERE id = ?",
            (doc_id,)
        )
        
        assert doc['flagged_for_review'] == 1
        assert doc['review_status'] == 'pending'

    def test_update_document_status(self, review_repo):
        """Test updating document status"""
        # First add a document
        doc_id = "test_doc_789"
        document = {
            'id': doc_id,
            'filename': f"{doc_id}.pdf",
            'status': 'ocr_complete',
            'ocr_confidence': 85.0,
            'json_confidence': 0.0,
            'correction_count': 0,
            'flagged_for_review': 0,
            'review_status': 'pending',
        }
        
        review_repo.add_document(document)
        
        # Update status
        new_status = "json_complete"
        result = review_repo.update_document_status(doc_id, new_status)
        assert result is True
        
        # Check status was updated
        doc = review_repo.db.fetch_one(
            "SELECT status FROM documents WHERE id = ?",
            (doc_id,)
        )
        
        assert doc['status'] == new_status

    def test_update_review_status(self, review_repo):
        """Test updating review status"""
        # First add a document
        doc_id = "test_doc_abc"
        document = {
            'id': doc_id,
            'filename': f"{doc_id}.pdf",
            'status': 'validated',
            'ocr_confidence': 95.0,
            'json_confidence': 90.0,
            'correction_count': 1,
            'flagged_for_review': 1,  # Flagged for review
            'review_status': 'pending',
        }
        
        review_repo.add_document(document)
        
        # Update review status to approved
        new_status = "approved"
        result = review_repo.update_review_status(doc_id, new_status)
        assert result is True
        
        # Check review status was updated and flag was cleared
        doc = review_repo.db.fetch_one(
            "SELECT review_status, flagged_for_review FROM documents WHERE id = ?",
            (doc_id,)
        )
        
        assert doc['review_status'] == new_status
        assert doc['flagged_for_review'] == 0  # Should be cleared when approved

    def test_record_review_feedback(self, review_repo):
        """Test recording review feedback"""
        # First add a document
        doc_id = "test_doc_feedback"
        document = {
            'id': doc_id,
            'filename': f"{doc_id}.pdf",
            'status': 'validated',
            'ocr_confidence': 95.0,
            'json_confidence': 90.0,
            'correction_count': 1,
            'flagged_for_review': 1,
            'review_status': 'pending',
        }
        
        review_repo.add_document(document)
        
        # Record feedback
        feedback = {
            'document_id': doc_id,
            'status': 'approved',
            'changes_made': True,
            'reason': '',
            'fields_corrected': {'name': 'John Smith', 'email': 'john@example.com'},
        }
        
        result = review_repo.record_review_feedback(feedback)
        assert result is True
        
        # Check feedback was recorded
        feedback_records = review_repo.db.fetch_all(
            "SELECT * FROM review_feedback WHERE document_id = ?",
            (doc_id,)
        )
        
        assert len(feedback_records) == 1
        assert feedback_records[0]['document_id'] == doc_id
        assert feedback_records[0]['status'] == 'approved'
        assert feedback_records[0]['changes_made'] == 1
        assert feedback_records[0]['reason'] == ''
        # Fields corrected should be serialized to JSON
        assert 'fields_corrected' in feedback_records[0]

    def test_record_field_correction(self, review_repo):
        """Test recording a field correction"""
        doc_id = "test_doc_correction"
        document = {
            'id': doc_id,
            'filename': f"{doc_id}.pdf",
            'status': 'validated',
            'ocr_confidence': 95.0,
            'json_confidence': 90.0,
            'correction_count': 1,
            'flagged_for_review': 1,
            'review_status': 'pending',
        }
        
        review_repo.add_document(document)
        
        # Record field correction
        field_name = "name"
        original_value = "Jon Smith"
        corrected_value = "John Smith"
        
        result = review_repo.record_field_correction(
            doc_id, field_name, original_value, corrected_value
        )
        assert result is True
        
        # Check correction was recorded
        corrections = review_repo.db.fetch_all(
            "SELECT * FROM field_corrections WHERE document_id = ?",
            (doc_id,)
        )
        
        assert len(corrections) == 1
        assert corrections[0]['document_id'] == doc_id
        assert corrections[0]['field_name'] == field_name
        assert corrections[0]['original_value'] == original_value
        assert corrections[0]['corrected_value'] == corrected_value

    def test_get_documents_for_review(self, review_repo):
        """Test getting documents for review"""
        # Add multiple documents with different issues
        docs = [
            {
                'id': "doc_with_ocr_issue",
                'filename': "doc_with_ocr_issue.pdf",
                'status': 'ocr_complete',
                'ocr_confidence': 65.0,
                'json_confidence': 0.0,
                'correction_count': 0,
                'flagged_for_review': 1,
                'review_status': 'pending',
            },
            {
                'id': "doc_with_json_issue",
                'filename': "doc_with_json_issue.pdf",
                'status': 'json_complete',
                'ocr_confidence': 90.0,
                'json_confidence': 65.0,
                'correction_count': 0,
                'flagged_for_review': 1,
                'review_status': 'pending',
            },
            {
                'id': "doc_completed",
                'filename': "doc_completed.pdf",
                'status': 'validated',
                'ocr_confidence': 95.0,
                'json_confidence': 95.0,
                'correction_count': 0,
                'flagged_for_review': 0,
                'review_status': 'completed',
            }
        ]
        
        for doc in docs:
            review_repo.add_document(doc)
        
        # Add issues
        review_repo.add_document_issue("doc_with_ocr_issue", "low_ocr_confidence", "OCR score low")
        review_repo.add_document_issue("doc_with_json_issue", "low_json_confidence", "JSON score low")
        
        # Get all documents for review
        documents = review_repo.get_documents_for_review('All')
        
        # Should only return flagged documents that aren't completed
        assert len(documents) == 2
        doc_ids = [doc['id'] for doc in documents]
        assert "doc_with_ocr_issue" in doc_ids
        assert "doc_with_json_issue" in doc_ids
        assert "doc_completed" not in doc_ids
        
        # Check issues are included and formatted correctly
        for doc in documents:
            if doc['id'] == "doc_with_ocr_issue":
                assert len(doc['issues']) == 1
                assert doc['issues'][0]['type'] == "low_ocr_confidence"
                assert doc['issues'][0]['details'] == "OCR score low"
        
        # Filter by issue type
        ocr_docs = review_repo.get_documents_for_review('low_ocr_confidence')
        assert len(ocr_docs) == 1
        assert ocr_docs[0]['id'] == "doc_with_ocr_issue"
        
        json_docs = review_repo.get_documents_for_review('low_json_confidence')
        assert len(json_docs) == 1
        assert json_docs[0]['id'] == "doc_with_json_issue"

    def test_get_dashboard_stats(self, review_repo):
        """Test getting dashboard stats"""
        # Add multiple documents with different statuses
        docs = [
            {
                'id': "doc1",
                'filename': "doc1.pdf",
                'status': 'ocr_complete',
                'ocr_confidence': 95.0,
                'json_confidence': 0.0,
                'correction_count': 0,
                'flagged_for_review': 1,
                'review_status': 'pending',
            },
            {
                'id': "doc2",
                'filename': "doc2.pdf",
                'status': 'json_complete',
                'ocr_confidence': 90.0,
                'json_confidence': 85.0,
                'correction_count': 0,
                'flagged_for_review': 1,
                'review_status': 'pending',
            },
            {
                'id': "doc3",
                'filename': "doc3.pdf",
                'status': 'validated',
                'ocr_confidence': 95.0,
                'json_confidence': 95.0,
                'correction_count': 1,
                'flagged_for_review': 0,
                'review_status': 'approved',
            }
        ]
        
        for doc in docs:
            review_repo.add_document(doc)
        
        # Add issues
        review_repo.add_document_issue("doc1", "low_ocr_confidence", "OCR score low")
        review_repo.add_document_issue("doc2", "validation_failure", "Failed validation")
        
        # Get dashboard stats
        stats = review_repo.get_dashboard_stats()
        
        # Check document stats
        assert stats['total_documents'] == 3
        assert stats['flagged_documents'] == 2
        assert stats['reviewed_documents'] == 1
        
        # Check issue stats
        assert len(stats['issue_stats']) == 2
        assert stats['issue_stats']['low_ocr_confidence'] == 1
        assert stats['issue_stats']['validation_failure'] == 1
        
        # Check pipeline stats
        assert len(stats['pipeline_stats']) == 3
        assert stats['pipeline_stats']['ocr_complete'] == 1
        assert stats['pipeline_stats']['json_complete'] == 1
        assert stats['pipeline_stats']['validated'] == 1