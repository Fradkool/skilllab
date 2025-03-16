"""
Tests for extraction API
"""

import os
import json
import pytest
from unittest.mock import patch, MagicMock

from api.extraction import (
    generate_json_from_text,
    validate_and_correct_json,
    run_full_extraction_pipeline
)

class TestExtractionAPI:
    """Tests for extraction API functions"""
    
    def test_generate_json_from_text(self, sample_ocr_result, test_config, temp_dir):
        """Test generating JSON from OCR text"""
        # Create a mock JSONGenerator
        with patch('api.extraction.JSONGenerator') as mock_generator_cls:
            # Configure the mock
            mock_generator = MagicMock()
            mock_generator_cls.return_value = mock_generator
            
            # Set up the mock to return sample data
            expected_json = {
                "file_id": "test_resume",
                "json_data": {
                    "Name": "John Doe",
                    "Email": "john.doe@example.com",
                    "Phone": "123-456-7890",
                    "Current_Position": "Software Engineer",
                    "Skills": ["Python", "Machine Learning", "SQL", "Docker"],
                    "Experience": [
                        {
                            "company": "Tech Inc.",
                            "title": "Software Engineer",
                            "years": "2020-Present"
                        },
                        {
                            "company": "Data Corp",
                            "title": "Data Analyst",
                            "years": "2018-2020"
                        }
                    ]
                },
                "json_path": os.path.join(temp_dir, "test_resume_structured.json"),
                "generation_time": 1.5
            }
            
            mock_generator.process_ocr_result.return_value = expected_json
            
            # Call the function
            with patch('api.extraction.get_metrics_repository'):
                result = generate_json_from_text(
                    ocr_result=sample_ocr_result,
                    output_dir=temp_dir
                )
            
            # Verify the result
            assert result == expected_json
            
            # Verify that JSONGenerator was initialized correctly
            mock_generator_cls.assert_called_once()
            assert mock_generator_cls.call_args[1]['output_dir'] == temp_dir
            
            # Verify that process_ocr_result was called
            mock_generator.process_ocr_result.assert_called_once_with(sample_ocr_result)
    
    def test_validate_and_correct_json(self, sample_ocr_result, sample_resume_data, test_config, temp_dir):
        """Test validating and correcting JSON"""
        # Create mock objects
        with patch('api.extraction.JSONGenerator') as mock_generator_cls, \
             patch('api.extraction.JSONAutoCorrector') as mock_corrector_cls:
            
            # Set up mocks
            mock_generator = MagicMock()
            mock_generator_cls.return_value = mock_generator
            
            mock_corrector = MagicMock()
            mock_corrector_cls.return_value = mock_corrector
            
            # Sample JSON result
            json_result = {
                "file_id": "test_resume",
                "json_data": sample_resume_data
            }
            
            # Set up expected result
            expected_result = {
                "file_id": "test_resume",
                "json_data": sample_resume_data,
                "is_valid": True,
                "coverage": 0.95,
                "correction_attempts": 1,
                "output_path": os.path.join(temp_dir, "test_resume_validated.json")
            }
            
            mock_corrector.process_resume.return_value = expected_result
            
            # Call the function
            with patch('api.extraction.get_metrics_repository'):
                result = validate_and_correct_json(
                    ocr_result=sample_ocr_result,
                    json_result=json_result,
                    output_dir=temp_dir,
                    min_coverage_threshold=0.8,
                    max_correction_attempts=2
                )
            
            # Verify the result
            assert result == expected_result
            
            # Verify that JSONAutoCorrector was initialized correctly
            mock_corrector_cls.assert_called_once()
            assert mock_corrector_cls.call_args[1]['output_dir'] == temp_dir
            assert mock_corrector_cls.call_args[1]['min_coverage_threshold'] == 0.8
            assert mock_corrector_cls.call_args[1]['max_correction_attempts'] == 2
            
            # Verify that process_resume was called
            mock_corrector.process_resume.assert_called_once_with(sample_ocr_result, json_result)
    
    def test_run_full_extraction_pipeline(self, test_config, temp_dir):
        """Test running the full extraction pipeline"""
        # Create a mock executor
        with patch('api.extraction.get_executor') as mock_get_executor:
            mock_executor = MagicMock()
            mock_get_executor.return_value = mock_executor
            
            # Create a mock context with results
            mock_context = MagicMock()
            mock_context.elapsed_time.return_value = 5.0
            mock_context.documents_processed = 3
            mock_context.errors = []
            
            mock_context.get_result.side_effect = lambda step: {
                "ocr": {"results": ["ocr1", "ocr2", "ocr3"], "count": 3, "time": 2.0},
                "json": {"results": ["json1", "json2", "json3"], "count": 3, "time": 1.5},
                "correction": {"results": ["corr1", "corr2", "corr3"], "count": 3, "valid_count": 2, "time": 1.0}
            }.get(step)
            
            mock_executor.run_pipeline.return_value = mock_context
            
            # Create test input directory
            input_dir = os.path.join(temp_dir, "input")
            os.makedirs(input_dir, exist_ok=True)
            
            # Call the function
            result = run_full_extraction_pipeline(
                input_dir=input_dir,
                output_dir=os.path.join(temp_dir, "output"),
                limit=5
            )
            
            # Verify the executor was called correctly
            mock_executor.run_pipeline.assert_called_once()
            assert mock_executor.run_pipeline.call_args[1]['name'] == "full"
            assert mock_executor.run_pipeline.call_args[1]['start_step'] == "ocr"
            assert mock_executor.run_pipeline.call_args[1]['end_step'] == "correction"
            
            # Verify the result
            assert "ocr" in result
            assert "json" in result
            assert "correction" in result
            assert result["elapsed_time"] == 5.0
            assert result["documents_processed"] == 3
            assert result["errors"] == []