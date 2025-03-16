"""
Unit tests for the training API
"""

import os
import sys
import json
import pytest
from unittest.mock import patch, MagicMock, mock_open

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from api.training import (
    build_training_dataset,
    train_donut_model,
    evaluate_model,
    run_training_pipeline,
    get_training_progress,
    get_available_models,
    get_dataset_metadata,
    get_training_history,
    export_model,
    delete_model
)


class TestTrainingAPI:
    """Test the training API functions"""
    
    @patch('api.training.DonutDatasetBuilder')
    def test_build_training_dataset(self, mock_builder_class):
        """Test building a dataset"""
        # Setup mocks
        mock_builder = MagicMock()
        mock_builder.build_dataset.return_value = {
            "train_samples": 80,
            "val_samples": 20
        }
        mock_builder_class.return_value = mock_builder
        
        # Mock file existence check
        with patch('os.path.exists', return_value=True):
            # Call function
            result = build_training_dataset(
                input_dir="/test/input",
                output_dir="/test/output",
                train_val_split=0.8
            )
            
            # Check results
            assert "train_samples" in result
            assert result["train_samples"] == 80
            assert "val_samples" in result
            assert result["val_samples"] == 20
            assert "time" in result
            
            # Check builder setup
            mock_builder_class.assert_called_once_with(
                validated_json_dir="/test/input",
                donut_dataset_dir="/test/output",
                train_val_split=0.8,
                task_name=mock_builder_class.call_args[1]["task_name"]
            )
    
    @patch('api.training.DonutTrainer')
    def test_train_donut_model(self, mock_trainer_class):
        """Test training a model"""
        # Setup mocks
        mock_trainer = MagicMock()
        mock_trainer.train.return_value = {
            "train_metrics": {"train_loss": 0.5},
            "eval_metrics": {"eval_loss": 0.4}
        }
        mock_trainer_class.return_value = mock_trainer
        
        # Mock file existence check
        with patch('os.path.exists', return_value=True):
            # Call function
            result = train_donut_model(
                dataset_dir="/test/dataset",
                output_dir="/test/model",
                epochs=5,
                batch_size=4,
                learning_rate=0.0001
            )
            
            # Check results
            assert "train_metrics" in result
            assert "eval_metrics" in result
            assert result["train_metrics"]["train_loss"] == 0.5
            assert result["eval_metrics"]["eval_loss"] == 0.4
            assert "training_time" in result
            
            # Check trainer setup
            mock_trainer_class.assert_called_once()
            call_kwargs = mock_trainer_class.call_args[1]
            assert call_kwargs["dataset_dir"] == "/test/dataset"
            assert call_kwargs["output_dir"] == "/test/model"
            assert call_kwargs["max_epochs"] == 5
            assert call_kwargs["batch_size"] == 4
            assert call_kwargs["learning_rate"] == 0.0001
    
    @patch('api.training.run_training_pipeline')
    @patch('api.training.get_metrics_repository')
    @patch('api.training.MetricsRepository.record_metric')
    def test_metrics_recording(self, mock_record, mock_get_repo, mock_run_pipeline):
        """Test metrics recording during training"""
        # Setup mock repository
        mock_repo = MagicMock()
        mock_get_repo.return_value = mock_repo
        
        # Setup pipeline results
        mock_run_pipeline.return_value = {
            "status": "completed",
            "training": {
                "train_metrics": {"train_loss": 0.5},
                "eval_metrics": {"eval_loss": 0.4},
                "training_time": 3600
            }
        }
        
        # Mock file existence checks
        with patch('os.path.exists', return_value=True):
            # Call the pipeline
            run_training_pipeline(
                start_with_dataset=True,
                epochs=5,
                batch_size=4
            )
            
            # Check metrics recording
            mock_get_repo.assert_called()
    
    @patch('builtins.open', new_callable=mock_open, read_data='{"train_metrics": {"train_loss": 0.5}}')
    @patch('os.path.exists')
    @patch('os.path.getmtime')
    def test_get_training_progress(self, mock_getmtime, mock_exists, mock_file):
        """Test getting training progress"""
        # Setup mocks
        mock_exists.return_value = True
        mock_getmtime.return_value = 1625097600  # Example timestamp
        
        # Mock glob to return a specific file
        with patch('glob.glob', return_value=['/test/model/training_summary.json']):
            # Call function
            result = get_training_progress()
            
            # Check results
            assert result is not None
            assert result["status"] == "completed"
            assert "progress" in result
            assert "metrics" in result
    
    @patch('os.listdir')
    @patch('os.path.isdir')
    @patch('os.path.exists')
    @patch('api.training._get_directory_size')
    def test_get_available_models(self, mock_size, mock_exists, mock_isdir, mock_listdir):
        """Test getting available models"""
        # Setup mocks
        mock_listdir.return_value = ['model1', 'model2']
        mock_isdir.return_value = True
        mock_exists.return_value = True
        mock_size.return_value = 1073741824  # 1GB
        
        # Mock open for reading config files
        m = mock_open(read_data='{}')
        with patch('builtins.open', m):
            # Call function
            result = get_available_models()
            
            # Check results
            assert isinstance(result, list)
            assert len(result) >= 2  # Should have at least our local models
            
            # Check local models
            local_models = [m for m in result if m["type"] == "local"]
            assert len(local_models) == 2
            
            # Check pre-trained models
            pretrained_models = [m for m in result if m["type"] == "pretrained"]
            assert len(pretrained_models) >= 2
    
    @patch('os.path.exists')
    @patch('os.listdir')
    @patch('api.training._get_dataset_stats')
    def test_get_dataset_metadata(self, mock_stats, mock_listdir, mock_exists):
        """Test getting dataset metadata"""
        # Setup mocks
        mock_stats.return_value = {
            "total_samples": 100,
            "train_samples": 80,
            "val_samples": 20
        }
        mock_listdir.return_value = ['file1_validated.json', 'file2_validated.json']
        mock_exists.return_value = True
        
        # Call function
        result = get_dataset_metadata()
        
        # Check results
        assert "stats" in result
        assert result["stats"]["total_samples"] == 100
        assert "available_json" in result
        assert result["available_json"] == 2
    
    @patch('shutil.make_archive')
    @patch('os.makedirs')
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    @patch('shutil.copy2')
    @patch('shutil.rmtree')
    def test_export_model(self, mock_rmtree, mock_copy, mock_open, mock_exists, mock_makedirs, mock_archive):
        """Test exporting a model"""
        # Setup mocks
        mock_exists.return_value = True
        
        # Call function
        result = export_model("test_model", "/test/exports")
        
        # Check results
        assert result is True
        mock_makedirs.assert_called()
        mock_copy.assert_called()
        mock_archive.assert_called()
        mock_rmtree.assert_called()
    
    @patch('shutil.rmtree')
    @patch('os.path.exists')
    def test_delete_model(self, mock_exists, mock_rmtree):
        """Test deleting a model"""
        # Setup mocks
        mock_exists.return_value = True
        
        # Call function
        result = delete_model("test_model")
        
        # Check results
        assert result is True
        mock_rmtree.assert_called_once()
    
    @patch('api.training.get_metrics_repository')
    def test_get_training_history(self, mock_get_repo):
        """Test getting training history"""
        # Setup mock repository
        mock_repo = MagicMock()
        mock_repo.get_metrics_by_category.return_value = [
            {
                "id": "1",
                "timestamp": "2023-01-01T10:00:00",
                "name": "total_time",
                "value": 3600,
                "details": {
                    "eval_loss": 0.4,
                    "epochs": 5,
                    "batch_size": 4
                }
            }
        ]
        mock_get_repo.return_value = mock_repo
        
        # Call function
        result = get_training_history()
        
        # Check results
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["id"] == "1"
        assert "timestamp" in result[0]
        assert result[0]["name"] == "total_time"
        assert result[0]["value"] == 3600
        assert result[0]["eval_loss"] == 0.4