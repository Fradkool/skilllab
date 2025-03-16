"""
Unit tests for Ollama client
"""

import os
import pytest
import unittest.mock as mock
from unittest.mock import patch, MagicMock
import json

from extraction.ollama_client import OllamaClient

class TestOllamaClient:
    """Test Ollama client functionality"""
    
    @pytest.fixture
    def client(self):
        """Create Ollama client fixture"""
        return OllamaClient(
            ollama_url="http://localhost:11434/api/generate",
            model_name="mistral:7b-instruct-v0.2-q8_0"
        )
    
    def test_init(self, client):
        """Test client initialization"""
        # Verify client properties
        assert client.ollama_url == "http://localhost:11434/api/generate"
        assert client.model_name == "mistral:7b-instruct-v0.2-q8_0"
    
    @patch("requests.get")
    def test_check_health_success(self, mock_get, client):
        """Test health check - successful response"""
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [
                {"name": "mistral:7b-instruct-v0.2-q8_0", "modified_at": "2023-01-01T00:00:00Z"}
            ]
        }
        mock_get.return_value = mock_response
        
        # Call health check
        result = client.check_health()
        
        # Verify result
        assert result is True
        mock_get.assert_called_once_with("http://localhost:11434/api/tags", timeout=5)
    
    @patch("requests.get")
    def test_check_health_missing_model(self, mock_get, client):
        """Test health check - missing model"""
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [
                {"name": "other-model", "modified_at": "2023-01-01T00:00:00Z"}
            ]
        }
        mock_get.return_value = mock_response
        
        # Call health check
        result = client.check_health()
        
        # Verify result
        assert result is False
        mock_get.assert_called_once_with("http://localhost:11434/api/tags", timeout=5)
    
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
        mock_get.assert_called_once_with("http://localhost:11434/api/tags", timeout=5)
    
    @patch("requests.get")
    def test_check_health_exception(self, mock_get, client):
        """Test health check - exception"""
        # Mock exception
        mock_get.side_effect = Exception("Connection error")
        
        # Call health check
        result = client.check_health()
        
        # Verify result
        assert result is False
        mock_get.assert_called_once_with("http://localhost:11434/api/tags", timeout=5)
    
    @patch("requests.get")
    def test_list_available_models(self, mock_get, client):
        """Test list available models"""
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [
                {"name": "mistral:7b-instruct-v0.2-q8_0", "modified_at": "2023-01-01T00:00:00Z"},
                {"name": "mistral:7b", "modified_at": "2023-01-01T00:00:00Z"}
            ]
        }
        mock_get.return_value = mock_response
        
        # Call list models
        result = client.list_available_models()
        
        # Verify result
        assert len(result) == 2
        assert result[0]["name"] == "mistral:7b-instruct-v0.2-q8_0"
        assert result[1]["name"] == "mistral:7b"
        mock_get.assert_called_once_with("http://localhost:11434/api/tags", timeout=5)
    
    @patch("requests.post")
    def test_generate_text(self, mock_post, client):
        """Test generate text"""
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "model": "mistral:7b-instruct-v0.2-q8_0",
            "response": "Generated text",
            "done": True
        }
        mock_post.return_value = mock_response
        
        # Call generate text
        result = client.generate_text(
            prompt="Test prompt",
            temperature=0.5,
            max_tokens=100
        )
        
        # Verify result
        assert result["model"] == "mistral:7b-instruct-v0.2-q8_0"
        assert result["response"] == "Generated text"
        assert result["done"] is True
        
        # Verify API call
        mock_post.assert_called_once()
        call_args = mock_post.call_args[1]
        assert call_args["timeout"] == 300
        
        # Verify payload
        payload = mock_post.call_args[1]["json"]
        assert payload["model"] == "mistral:7b-instruct-v0.2-q8_0"
        assert payload["prompt"] == "Test prompt"
        assert payload["temperature"] == 0.5
        assert payload["max_tokens"] == 100
        assert payload["stream"] is False
    
    @patch("requests.post")
    def test_generate_text_error(self, mock_post, client):
        """Test generate text - error response"""
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"
        mock_post.return_value = mock_response
        
        # Call generate text and expect exception
        with pytest.raises(Exception) as exc_info:
            client.generate_text(prompt="Test prompt")
        
        # Verify exception
        assert "Ollama API error: 500" in str(exc_info.value)
    
    def test_extract_json_from_text_valid(self, client):
        """Test extract JSON from text - valid JSON"""
        text = 'Some text before {"name": "John", "age": 30} and after'
        result = client.extract_json_from_text(text)
        
        assert result == {"name": "John", "age": 30}
    
    def test_extract_json_from_text_invalid(self, client):
        """Test extract JSON from text - invalid JSON"""
        text = 'Some text without valid JSON'
        result = client.extract_json_from_text(text)
        
        assert result == {}
    
    @patch("extraction.ollama_client.OllamaClient.generate_text")
    @patch("extraction.ollama_client.OllamaClient.extract_json_from_text")
    @patch("extraction.ollama_client.OllamaClient.check_health")
    def test_generate_json_success(self, mock_check_health, mock_extract_json, mock_generate_text, client):
        """Test generate JSON - success"""
        # Mock health check
        mock_check_health.return_value = True
        
        # Mock generate text
        mock_generate_text.return_value = {"response": "JSON text"}
        
        # Mock extract JSON
        mock_extract_json.return_value = {"name": "John", "age": 30}
        
        # Call generate JSON
        template = {"name": None, "age": None}
        result, time_taken = client.generate_json(
            prompt="Test prompt",
            template=template,
            temperature=0.5,
            max_tokens=100
        )
        
        # Verify result
        assert result == {"name": "John", "age": 30}
        assert isinstance(time_taken, float)
        
        # Verify calls
        mock_check_health.assert_called_once()
        mock_generate_text.assert_called_once_with("Test prompt", 0.5, 100)
        mock_extract_json.assert_called_once_with("JSON text")
    
    @patch("extraction.ollama_client.OllamaClient.check_health")
    def test_generate_json_health_check_failure(self, mock_check_health, client):
        """Test generate JSON - health check failure"""
        # Mock health check
        mock_check_health.return_value = False
        
        # Call generate JSON
        template = {"name": None, "age": None}
        with pytest.raises(Exception) as exc_info:
            client.generate_json(
                prompt="Test prompt",
                template=template
            )
        
        # Verify exception
        assert "Ollama service is not available" in str(exc_info.value)
        
        # Verify calls
        assert mock_check_health.call_count == 2  # Initial check + retry