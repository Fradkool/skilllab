"""
Unit tests for the review API
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from api.review import (
    get_review_repository,
    get_review_queue,
    get_document_details,
    update_document_status,
    approve_document,
    reject_document,
    save_document_json,
    save_review_feedback,
    get_dashboard_stats,
    get_review_history,
    get_performance_stats,
    get_error_analysis,
    get_improvement_metrics,
    load_documents_from_filesystem,
    sync_review_data
)


class TestReviewAPI:
    """Test the review API functions"""
    
    @patch('api.review.ReviewRepository')
    def test_get_review_repository(self, mock_review_repo_class):
        """Test getting a review repository instance"""
        mock_instance = MagicMock()
        mock_review_repo_class.return_value = mock_instance
        
        repo = get_review_repository()
        
        assert repo is mock_instance
        mock_review_repo_class.assert_called_once()
    
    @patch('api.review.sync_review_data')
    @patch('api.review.get_review_repository')
    def test_get_review_queue(self, mock_get_repo, mock_sync):
        """Test getting the review queue"""
        # Setup mocks
        mock_repo = MagicMock()
        mock_docs = [{'id': 'doc1'}, {'id': 'doc2'}]
        mock_repo.get_documents_for_review.return_value = mock_docs
        mock_get_repo.return_value = mock_repo
        
        # Call function
        result = get_review_queue(issue_filter='test_filter', limit=50)
        
        # Check results
        assert result == mock_docs
        mock_sync.assert_called_once()
        mock_get_repo.assert_called_once()
        mock_repo.get_documents_for_review.assert_called_once_with('test_filter', 50)
        mock_repo.close.assert_called_once()
    
    @patch('api.review.get_review_repository')
    def test_get_document_details(self, mock_get_repo):
        """Test getting document details"""
        # Setup mocks
        mock_repo = MagicMock()
        mock_doc = {
            'id': 'doc1',
            'filename': 'doc1.pdf',
            'status': 'validated',
            'ocr_confidence': 95.0,
            'image_paths': ['/path/to/image1.png']
        }
        mock_repo.get_document_details.return_value = mock_doc
        mock_get_repo.return_value = mock_repo
        
        # Setup file system mocks
        with patch('os.path.exists', return_value=False), \
             patch('builtins.open', MagicMock()):
            
            # Call function
            result = get_document_details('doc1')
            
            # Check results
            assert result == mock_doc
            assert 'image_path' in result
            mock_get_repo.assert_called_once()
            mock_repo.get_document_details.assert_called_once_with('doc1')
            mock_repo.close.assert_called_once()
    
    @patch('api.review.get_review_repository')
    def test_update_document_status(self, mock_get_repo):
        """Test updating document status"""
        # Setup mocks
        mock_repo = MagicMock()
        mock_repo.update_review_status.return_value = True
        mock_get_repo.return_value = mock_repo
        
        # Call function
        result = update_document_status('doc1', 'approved')
        
        # Check results
        assert result is True
        mock_get_repo.assert_called_once()
        mock_repo.update_review_status.assert_called_once_with('doc1', 'approved')
        mock_repo.close.assert_called_once()
    
    @patch('api.review.save_review_feedback')
    def test_approve_document(self, mock_save_feedback):
        """Test approving a document"""
        # Setup mock
        mock_save_feedback.return_value = True
        
        # Call function
        result = approve_document('doc1', changes_made=True)
        
        # Check results
        assert result is True
        mock_save_feedback.assert_called_once_with(
            document_id='doc1',
            status='approved',
            corrections={},
            changes_made=True
        )
    
    @patch('api.review.save_review_feedback')
    def test_reject_document(self, mock_save_feedback):
        """Test rejecting a document"""
        # Setup mock
        mock_save_feedback.return_value = True
        
        # Call function
        result = reject_document('doc1', reason='Test reason')
        
        # Check results
        assert result is True
        mock_save_feedback.assert_called_once_with(
            document_id='doc1',
            status='rejected',
            reason='Test reason'
        )
    
    @patch('api.review.save_review_feedback')
    def test_save_document_json(self, mock_save_feedback):
        """Test saving document JSON data"""
        # Setup mock
        mock_save_feedback.return_value = True
        mock_json_data = {'name': 'John Smith'}
        
        # Call function
        result = save_document_json('doc1', mock_json_data)
        
        # Check results
        assert result is True
        mock_save_feedback.assert_called_once_with(
            document_id='doc1',
            status='in_progress',
            json_data=mock_json_data,
            changes_made=True
        )
    
    @patch('api.review.get_review_repository')
    @patch('api.review.sync_databases')
    def test_save_review_feedback(self, mock_sync, mock_get_repo):
        """Test saving review feedback"""
        # Setup mocks
        mock_repo = MagicMock()
        mock_repo.update_review_status.return_value = True
        mock_repo.record_review_feedback.return_value = True
        mock_repo._get_now.return_value = '2024-01-01T12:00:00'
        mock_get_repo.return_value = mock_repo
        
        with patch('os.path.exists', return_value=False), \
             patch('builtins.open', MagicMock()):
            
            # Call function with minimal arguments
            result = save_review_feedback(
                document_id='doc1',
                status='approved'
            )
            
            # Check results
            assert result is True
            mock_get_repo.assert_called_once()
            mock_repo.update_review_status.assert_called_once_with('doc1', 'approved')
            mock_repo.record_review_feedback.assert_called_once()
            mock_sync.assert_called_once()
            mock_repo.close.assert_called_once()
    
    @patch('api.review.get_review_repository')
    def test_get_dashboard_stats(self, mock_get_repo):
        """Test getting dashboard stats"""
        # Setup mocks
        mock_repo = MagicMock()
        mock_stats = {
            'total_documents': 10,
            'flagged_documents': 5,
            'reviewed_documents': 3,
            'issue_stats': {'low_ocr_confidence': 2},
            'pipeline_stats': {'validated': 5}
        }
        mock_repo.get_dashboard_stats.return_value = mock_stats
        mock_get_repo.return_value = mock_repo
        
        # Call function
        result = get_dashboard_stats()
        
        # Check results
        assert result == mock_stats
        mock_get_repo.assert_called_once()
        mock_repo.get_dashboard_stats.assert_called_once()
        mock_repo.close.assert_called_once()
    
    @patch('api.review.get_review_repository')
    def test_get_review_history(self, mock_get_repo):
        """Test getting review history"""
        # Setup mocks
        mock_repo = MagicMock()
        mock_history = [
            {'document_id': 'doc1', 'status': 'approved'},
            {'document_id': 'doc2', 'status': 'rejected'}
        ]
        mock_repo.get_review_history.return_value = mock_history
        mock_get_repo.return_value = mock_repo
        
        # Call function
        result = get_review_history(limit=50)
        
        # Check results
        assert result == mock_history
        mock_get_repo.assert_called_once()
        mock_repo.get_review_history.assert_called_once()
        mock_repo.close.assert_called_once()
    
    @patch('api.review.get_review_repository')
    def test_load_documents_from_filesystem(self, mock_get_repo):
        """Test loading documents from filesystem"""
        # Setup mocks
        mock_repo = MagicMock()
        mock_repo.load_documents_from_fs.return_value = 5
        mock_get_repo.return_value = mock_repo
        
        # Call function
        result = load_documents_from_filesystem()
        
        # Check results
        assert result == 5
        mock_get_repo.assert_called_once()
        mock_repo.load_documents_from_fs.assert_called_once()
        mock_repo.close.assert_called_once()
    
    @patch('api.review.sync_review_data')
    def test_sync_review_data_api(self, mock_sync):
        """Test sync review data API function"""
        # Setup mock
        mock_sync.return_value = (5, 3)
        
        # Call function
        docs, issues = sync_review_data()
        
        # Check results
        assert docs == 5
        assert issues == 3
        mock_sync.assert_called_once()