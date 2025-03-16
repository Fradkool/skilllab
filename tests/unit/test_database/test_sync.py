"""
Unit tests for database synchronization
"""

import os
import sys
import pytest
import tempfile
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from database.sync import sync_databases, sync_review_data
from database.review_db import ReviewRepository
from database.metrics_db import MetricsRepository


@pytest.fixture
def temp_db_path():
    """Create a temporary database file path"""
    with tempfile.NamedTemporaryFile(suffix='.db') as tmp:
        yield tmp.name


@pytest.fixture
def mock_metrics_repo():
    """Mock metrics repository for testing"""
    repo = MagicMock(spec=MetricsRepository)
    
    # Setup mock data
    mock_doc1 = {
        'id': 'doc1',
        'status': 'ocr_complete',
        'ocr_confidence': 85.0,
        'json_confidence': 0.0,
        'correction_count': 0,
        'flagged_for_review': 1,
        'review_status': 'pending',
        'updated_at': '2024-01-01T10:00:00',
        'issues': [
            {'type': 'low_ocr_confidence', 'details': 'OCR score low'}
        ]
    }
    
    mock_doc2 = {
        'id': 'doc2',
        'status': 'json_complete',
        'ocr_confidence': 90.0,
        'json_confidence': 70.0,
        'correction_count': 0,
        'flagged_for_review': 1,
        'review_status': 'pending',
        'updated_at': '2024-01-01T11:00:00',
        'issues': [
            {'type': 'low_json_confidence', 'details': 'JSON score low'}
        ]
    }
    
    # Setup mock methods
    repo.get_review_queue.return_value = [mock_doc1, mock_doc2]
    repo.get_document_details.side_effect = lambda doc_id: (
        mock_doc1 if doc_id == 'doc1' else mock_doc2 if doc_id == 'doc2' else None
    )
    
    return repo


@pytest.fixture
def mock_review_repo():
    """Mock review repository for testing"""
    repo = MagicMock(spec=ReviewRepository)
    
    # Setup mock data
    mock_doc3 = {
        'id': 'doc3',
        'status': 'validated',
        'ocr_confidence': 95.0,
        'json_confidence': 90.0,
        'correction_count': 1,
        'flagged_for_review': 0,
        'review_status': 'approved',
        'updated_at': '2024-01-01T12:00:00',
        'issues': []
    }
    
    # Setup mock methods
    repo.get_documents_for_review.return_value = [mock_doc3]
    repo.get_document_details.return_value = mock_doc3
    repo.load_documents_from_fs.return_value = 2  # Mock 2 documents loaded
    
    return repo


class TestDatabaseSync:
    """Test database synchronization functionality"""
    
    def test_sync_databases(self, mock_metrics_repo, mock_review_repo):
        """Test synchronizing metrics and review databases"""
        # Run sync with mock repositories
        result = sync_databases(mock_metrics_repo, mock_review_repo)
        
        # Check that docs were added from metrics to review
        assert mock_review_repo.add_document.call_count >= 2
        
        # Check that issues were added
        assert mock_review_repo.add_document_issue.call_count >= 2
        
        # Check review status was synced back to metrics
        assert mock_metrics_repo.update_document_status.call_count >= 1
        
        # Check result contains sync counts
        assert isinstance(result, tuple)
        assert len(result) == 2
        docs_synced, issues_synced = result
        assert isinstance(docs_synced, int)
        assert isinstance(issues_synced, int)
    
    def test_sync_review_data(self, mock_metrics_repo, mock_review_repo):
        """Test synchronizing review data with filesystem and metrics"""
        # Patch repositories
        with patch('database.sync.ReviewRepository', return_value=mock_review_repo), \
             patch('database.sync.MetricsRepository', return_value=mock_metrics_repo), \
             patch('database.sync.sync_databases', return_value=(3, 2)):
            
            # Run sync_review_data
            docs_synced, issues_synced = sync_review_data()
            
            # Check load_documents_from_fs was called
            assert mock_review_repo.load_documents_from_fs.called
            
            # Check sync_databases was called
            assert docs_synced > 0
            assert issues_synced > 0