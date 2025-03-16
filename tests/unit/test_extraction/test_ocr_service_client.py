"""
Unit tests for OCR service client
"""

import os
import pytest
import unittest.mock as mock
from unittest.mock import patch, MagicMock
import json

from extraction.ocr_service_client import OCRServiceClient

class TestOCRServiceClient:
    """Test OCR service client functionality"""
    
    @pytest.fixture
    def client(self):
        """Create OCR service client fixture"""
        return OCRServiceClient(
            service_url="http://localhost:8080/v1/ocr/process_pdf",
            output_dir="data/output"
        )
    
    @patch("os.makedirs")
    def test_init(self, mock_makedirs, client):
        """Test client initialization"""
        # Verify that output directories are created
        mock_makedirs.assert_any_call("data/output/images", exist_ok=True)
        mock_makedirs.assert_any_call("data/output/ocr_results", exist_ok=True)
        
        # Verify client properties
        assert client.service_url == "http://localhost:8080/v1/ocr/process_pdf"
        assert client.output_dir == "data/output"
    
    @patch("requests.get")
    def test_check_health_success(self, mock_get, client):
        """Test health check - successful response"""
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "healthy", "service": "paddleocr"}
        mock_get.return_value = mock_response
        
        # Call health check
        result = client.check_health()
        
        # Verify result
        assert result is True
        mock_get.assert_called_once_with("http://localhost:8080/health", timeout=5)
    
    @patch("requests.get")
    def test_check_health_failure(self, mock_get, client):
        """Test health check - failed response"""
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"
        mock_get.return_value = mock_response
        
        # Call health check
        result = client.check_health()
        
        # Verify result
        assert result is False
        mock_get.assert_called_once_with("http://localhost:8080/health", timeout=5)
    
    @patch("requests.get")
    def test_check_health_exception(self, mock_get, client):
        """Test health check - exception"""
        # Mock exception
        mock_get.side_effect = Exception("Connection error")
        
        # Call health check
        result = client.check_health()
        
        # Verify result
        assert result is False
        mock_get.assert_called_once_with("http://localhost:8080/health", timeout=5)
    
    @patch("requests.post")
    def test_process_pdf_success(self, mock_post, client):
        """Test process PDF - successful response"""
        # Sample PDF path
        pdf_path = "data/input/sample.pdf"
        
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "file_id": "1234_sample",
            "original_path": "sample.pdf",
            "page_count": 2,
            "image_paths": [
                "/app/data/output/images/1234_sample_page_1.png",
                "/app/data/output/images/1234_sample_page_2.png"
            ],
            "total_text_elements": 50,
            "page_results": [
                {
                    "text_elements": [],
                    "full_text": "Sample text page 1",
                    "text_count": 20
                },
                {
                    "text_elements": [],
                    "full_text": "Sample text page 2",
                    "text_count": 30
                }
            ],
            "combined_text": "Sample text page 1 Sample text page 2"
        }
        mock_post.return_value = mock_response
        
        # Mock file open
        mock_file = mock.mock_open()
        with patch("builtins.open", mock_file):
            # Call process PDF
            result = client.process_pdf(
                pdf_path=pdf_path,
                use_gpu=False,
                language="en",
                min_confidence=0.5,
                dpi=300
            )
        
        # Verify result
        assert result["result"]["file_id"] == "1234_sample"
        assert result["result"]["page_count"] == 2
        assert result["result"]["total_text_elements"] == 50
        assert result["result"]["combined_text"] == "Sample text page 1 Sample text page 2"
        
        # Verify image paths are converted
        assert result["result"]["image_paths"] == [
            "data/output/images/1234_sample_page_1.png",
            "data/output/images/1234_sample_page_2.png"
        ]
        
        # Verify result path is converted
        assert result["result_path"] == "data/output/ocr_results/1234_sample_ocr.json"
        
        # Verify API call
        mock_post.assert_called_once()
        call_args = mock_post.call_args[1]
        assert call_args["timeout"] == 300
        
        # Verify form data
        form_data = call_args["data"]
        assert form_data["use_gpu"] == "false"
        assert form_data["language"] == "en"
        assert form_data["min_confidence"] == "0.5"
        assert form_data["dpi"] == "300"
    
    @patch("requests.post")
    def test_process_pdf_error(self, mock_post, client):
        """Test process PDF - error response"""
        # Sample PDF path
        pdf_path = "data/input/sample.pdf"
        
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"
        mock_post.return_value = mock_response
        
        # Mock file open
        mock_file = mock.mock_open()
        with patch("builtins.open", mock_file):
            # Call process PDF and expect exception
            with pytest.raises(Exception) as exc_info:
                client.process_pdf(pdf_path=pdf_path)
        
        # Verify exception
        assert "OCR service error: 500" in str(exc_info.value)
    
    @patch("requests.post")
    def test_process_image_success(self, mock_post, client):
        """Test process image - successful response"""
        # Sample image path
        image_path = "data/input/sample.png"
        
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "file_id": "1234_sample",
            "original_path": "sample.png",
            "page_count": 1,
            "image_paths": [
                "/app/data/output/images/1234_sample.png"
            ],
            "total_text_elements": 30,
            "page_results": [
                {
                    "text_elements": [],
                    "full_text": "Sample text image",
                    "text_count": 30
                }
            ],
            "combined_text": "Sample text image"
        }
        mock_post.return_value = mock_response
        
        # Mock file open
        mock_file = mock.mock_open()
        with patch("builtins.open", mock_file):
            # Call process image
            result = client.process_image(
                image_path=image_path,
                use_gpu=False,
                language="en",
                min_confidence=0.5
            )
        
        # Verify result
        assert result["result"]["file_id"] == "1234_sample"
        assert result["result"]["page_count"] == 1
        assert result["result"]["total_text_elements"] == 30
        assert result["result"]["combined_text"] == "Sample text image"
        
        # Verify image paths are converted
        assert result["result"]["image_paths"] == [
            "data/output/images/1234_sample.png"
        ]
        
        # Verify API call
        mock_post.assert_called_once()
        call_args = mock_post.call_args[1]
        assert call_args["timeout"] == 120
        
        # Verify correct endpoint is used
        assert "process_image" in mock_post.call_args[0][0]