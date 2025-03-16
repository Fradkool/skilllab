"""
Test configuration for SkillLab
Provides fixtures and utilities for testing
"""

import os
import sys
import tempfile
import json
import shutil
import pytest
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

# Import SkillLab modules
from config import AppConfig
from database import DatabaseConnection, MetricsRepository
from pipeline import PipelineContext, PipelineExecutor

@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir

@pytest.fixture
def test_config():
    """Create a test configuration"""
    # Create a test configuration based on the defaults
    from config.schema import (
        PathsConfig, PipelineConfig, GPUConfig, OCRConfig, 
        JSONGenerationConfig, CorrectionConfig, DatasetConfig,
        TrainingConfig, ReviewConfig, MonitoringConfig,
        DatabaseConfig, LoggingConfig
    )
    
    # Create temp directories
    temp_data_dir = tempfile.mkdtemp()
    temp_models_dir = tempfile.mkdtemp()
    temp_logs_dir = tempfile.mkdtemp()
    
    # Create paths configuration
    paths_config = PathsConfig(
        input_dir=os.path.join(temp_data_dir, "input"),
        output_dir=os.path.join(temp_data_dir, "output"),
        model_dir=temp_models_dir,
        logs_dir=temp_logs_dir
    )
    
    # Create subdirectories
    os.makedirs(paths_config.input_dir, exist_ok=True)
    os.makedirs(paths_config.output_dir, exist_ok=True)
    os.makedirs(os.path.join(paths_config.output_dir, "images"), exist_ok=True)
    os.makedirs(os.path.join(paths_config.output_dir, "ocr_results"), exist_ok=True)
    os.makedirs(os.path.join(paths_config.output_dir, "json_results"), exist_ok=True)
    os.makedirs(os.path.join(paths_config.output_dir, "validated_json"), exist_ok=True)
    
    # Create database configuration
    db_config = DatabaseConfig(
        main_db_path=":memory:",
        pool_size=1,
        timeout=5
    )
    
    # Create monitoring configuration
    monitoring_config = MonitoringConfig(
        enabled=True,
        metrics_db=":memory:",
        update_interval=0.1
    )
    
    # Create test configuration
    config = AppConfig(
        paths=paths_config,
        pipeline=PipelineConfig(
            start_step="ocr",
            end_step="training",
            limit=5
        ),
        gpu=GPUConfig(
            monitor=False,
            use_gpu_ocr=False
        ),
        ocr=OCRConfig(
            language="en",
            dpi=150,  # Lower resolution for faster tests
            min_confidence=0.5
        ),
        json_generation=JSONGenerationConfig(
            ollama_url="http://localhost:11434/api/generate",
            model_name="mistral:7b-instruct-v0.2-q8_0",
            temperature=0.1,
            max_tokens=1024  # Smaller for faster tests
        ),
        correction=CorrectionConfig(
            min_coverage_threshold=0.8,
            max_correction_attempts=2
        ),
        dataset=DatasetConfig(
            train_val_split=0.8,
            task_name="resume_extraction"
        ),
        training=TrainingConfig(
            epochs=1,  # Just one epoch for testing
            batch_size=2,
            learning_rate=5e-5,
            weight_decay=0.01,
            pretrained_model="naver-clova-ix/donut-base"
        ),
        review=ReviewConfig(
            enabled=False,
            db_path=":memory:"
        ),
        monitoring=monitoring_config,
        database=db_config,
        logging=LoggingConfig(
            level="DEBUG",
            file=os.path.join(temp_logs_dir, "test.log"),
            max_size_mb=1,
            backup_count=1
        )
    )
    
    yield config
    
    # Cleanup
    shutil.rmtree(temp_data_dir, ignore_errors=True)
    shutil.rmtree(temp_models_dir, ignore_errors=True)
    shutil.rmtree(temp_logs_dir, ignore_errors=True)

@pytest.fixture
def test_db_connection(test_config):
    """Create a test database connection"""
    conn = DatabaseConnection(test_config.database.main_db_path)
    yield conn
    conn.close()

@pytest.fixture
def test_metrics_repo(test_config):
    """Create a test metrics repository"""
    repo = MetricsRepository(test_config.monitoring.metrics_db)
    yield repo
    repo.db.close()

@pytest.fixture
def test_pipeline_context(test_config):
    """Create a test pipeline context"""
    context = PipelineContext(config=test_config)
    yield context

@pytest.fixture
def test_pipeline_executor(test_config):
    """Create a test pipeline executor"""
    executor = PipelineExecutor(config=test_config)
    yield executor

@pytest.fixture
def sample_resume_data():
    """Create sample resume data for testing"""
    return {
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
    }

@pytest.fixture
def sample_ocr_result(sample_resume_data):
    """Create a sample OCR result for testing"""
    resume_text = f"""
    {sample_resume_data['Name']}
    {sample_resume_data['Email']} | {sample_resume_data['Phone']}
    {sample_resume_data['Current_Position']}
    
    SKILLS
    {', '.join(sample_resume_data['Skills'])}
    
    EXPERIENCE
    {sample_resume_data['Experience'][0]['company']} - {sample_resume_data['Experience'][0]['title']}
    {sample_resume_data['Experience'][0]['years']}
    
    {sample_resume_data['Experience'][1]['company']} - {sample_resume_data['Experience'][1]['title']}
    {sample_resume_data['Experience'][1]['years']}
    """
    
    return {
        "file_id": "test_resume",
        "original_path": "test_resume.pdf",
        "page_count": 1,
        "image_paths": ["test_resume_page_1.png"],
        "total_text_elements": 15,
        "page_results": [
            {
                "text_elements": [
                    {"text": f"{sample_resume_data['Name']}", "confidence": 0.95},
                    {"text": f"{sample_resume_data['Email']}", "confidence": 0.98},
                    {"text": f"{sample_resume_data['Phone']}", "confidence": 0.97},
                    {"text": f"{sample_resume_data['Current_Position']}", "confidence": 0.96},
                    {"text": "SKILLS", "confidence": 0.99},
                    {"text": f"{', '.join(sample_resume_data['Skills'])}", "confidence": 0.94},
                    {"text": "EXPERIENCE", "confidence": 0.99},
                    {"text": f"{sample_resume_data['Experience'][0]['company']}", "confidence": 0.92},
                    {"text": f"{sample_resume_data['Experience'][0]['title']}", "confidence": 0.93},
                    {"text": f"{sample_resume_data['Experience'][0]['years']}", "confidence": 0.91},
                    {"text": f"{sample_resume_data['Experience'][1]['company']}", "confidence": 0.90},
                    {"text": f"{sample_resume_data['Experience'][1]['title']}", "confidence": 0.89},
                    {"text": f"{sample_resume_data['Experience'][1]['years']}", "confidence": 0.88}
                ],
                "full_text": resume_text,
                "text_count": 13
            }
        ],
        "combined_text": resume_text
    }