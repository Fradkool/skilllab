"""
Configuration schema for SkillLab
Defines schema for validating configuration
"""

from typing import Dict, List, Any, Optional, Union
from pydantic import BaseModel, Field, validator, root_validator
import os
import re

class PathsConfig(BaseModel):
    """Paths configuration"""
    input_dir: str = Field("data/input", description="Directory containing input resume PDFs")
    output_dir: str = Field("data/output", description="Directory for output files")
    model_dir: str = Field("models/donut_finetuned", description="Directory to save fine-tuned model")
    logs_dir: str = Field("logs", description="Directory for log files")
    
    @validator('*')
    def validate_dirs_exist(cls, v, values, **kwargs):
        """Ensure directories exist, creating them if necessary"""
        if not os.path.exists(v):
            os.makedirs(v, exist_ok=True)
        return v

class PipelineConfig(BaseModel):
    """Pipeline configuration"""
    start_step: str = Field("ocr", description="Step to start from")
    end_step: str = Field("training", description="Step to end at")
    limit: Optional[int] = Field(None, description="Maximum number of resumes to process")
    
    @validator('start_step', 'end_step')
    def validate_step(cls, v):
        """Validate pipeline step name"""
        valid_steps = ["ocr", "json", "correction", "dataset", "training"]
        if v not in valid_steps:
            raise ValueError(f"Step must be one of {valid_steps}")
        return v
    
    @root_validator
    def validate_step_order(cls, values):
        """Validate step order"""
        steps = ["ocr", "json", "correction", "dataset", "training"]
        start_idx = steps.index(values.get('start_step'))
        end_idx = steps.index(values.get('end_step'))
        
        if start_idx > end_idx:
            raise ValueError(f"start_step ({values.get('start_step')}) must come before end_step ({values.get('end_step')})")
        
        return values

class GPUConfig(BaseModel):
    """GPU configuration"""
    monitor: bool = Field(False, description="Enable GPU monitoring")
    use_gpu_ocr: bool = Field(False, description="Use GPU for OCR (not recommended for pipeline)")

class OCRConfig(BaseModel):
    """OCR configuration"""
    language: str = Field("en", description="Language for OCR")
    dpi: int = Field(300, description="DPI for PDF to image conversion")
    min_confidence: float = Field(0.5, description="Minimum confidence score for OCR results")
    service_url: Optional[str] = Field(None, description="URL for PaddleOCR service API (if using containerized service)")
    use_service: bool = Field(False, description="Whether to use the OCR service instead of direct PaddleOCR calls")
    
    @validator('dpi')
    def validate_dpi(cls, v):
        """Validate DPI value"""
        if v < 72 or v > 600:
            raise ValueError("DPI must be between 72 and 600")
        return v
    
    @validator('min_confidence')
    def validate_min_confidence(cls, v):
        """Validate confidence threshold"""
        if v < 0.0 or v > 1.0:
            raise ValueError("min_confidence must be between 0.0 and 1.0")
        return v
        
    @validator('service_url')
    def validate_service_url(cls, v, values):
        """Validate service URL if use_service is True"""
        if values.get('use_service', False) and not v:
            raise ValueError("service_url must be provided when use_service is True")
        return v

class JSONGenerationConfig(BaseModel):
    """JSON generation configuration"""
    ollama_url: str = Field("http://localhost:11434/api/generate", 
                           description="URL for Ollama API")
    model_name: str = Field("mistral:7b-instruct-v0.2-q8_0", 
                           description="Model to use for generation")
    temperature: float = Field(0.1, description="Temperature for generation")
    max_tokens: int = Field(2048, description="Maximum tokens to generate")
    max_retries: int = Field(3, description="Maximum number of retries for Ollama API calls")
    timeout: int = Field(300, description="Timeout in seconds for Ollama API calls")
    
    @validator('temperature')
    def validate_temperature(cls, v):
        """Validate temperature value"""
        if v < 0.0 or v > 1.0:
            raise ValueError("temperature must be between 0.0 and 1.0")
        return v
        
    @validator('max_retries')
    def validate_max_retries(cls, v):
        """Validate max_retries"""
        if v < 0:
            raise ValueError("max_retries must be a non-negative integer")
        return v
        
    @validator('timeout')
    def validate_timeout(cls, v):
        """Validate timeout"""
        if v < 0:
            raise ValueError("timeout must be a non-negative integer")
        return v

class CorrectionConfig(BaseModel):
    """Auto-correction configuration"""
    min_coverage_threshold: float = Field(0.9, description="Minimum text coverage threshold")
    max_correction_attempts: int = Field(3, description="Maximum number of correction attempts")
    
    @validator('min_coverage_threshold')
    def validate_min_coverage_threshold(cls, v):
        """Validate coverage threshold"""
        if v < 0.0 or v > 1.0:
            raise ValueError("min_coverage_threshold must be between 0.0 and 1.0")
        return v

class DatasetConfig(BaseModel):
    """Dataset builder configuration"""
    train_val_split: float = Field(0.8, description="Train/validation split ratio")
    task_name: str = Field("resume_extraction", description="Task name for Donut training")
    
    @validator('train_val_split')
    def validate_train_val_split(cls, v):
        """Validate split ratio"""
        if v <= 0.0 or v >= 1.0:
            raise ValueError("train_val_split must be between 0.0 and 1.0")
        return v

class TrainingConfig(BaseModel):
    """Training configuration"""
    epochs: int = Field(5, description="Number of epochs for training")
    batch_size: int = Field(4, description="Batch size for training")
    learning_rate: float = Field(5e-5, description="Learning rate")
    weight_decay: float = Field(0.01, description="Weight decay")
    pretrained_model: str = Field("naver-clova-ix/donut-base", 
                                 description="Pre-trained model to use")
    
    @validator('epochs')
    def validate_epochs(cls, v):
        """Validate epochs"""
        if v < 1:
            raise ValueError("epochs must be at least 1")
        return v
    
    @validator('batch_size')
    def validate_batch_size(cls, v):
        """Validate batch size"""
        if v < 1:
            raise ValueError("batch_size must be at least 1")
        return v

class ReviewConfig(BaseModel):
    """Human review configuration"""
    enabled: bool = Field(False, description="Enable human review for flagged documents")
    db_path: str = Field("review/review.db", description="Path to review database")

class MonitoringConfig(BaseModel):
    """Monitoring configuration"""
    enabled: bool = Field(False, description="Enable metrics collection and monitoring")
    metrics_db: str = Field("data/metrics.db", description="Path to metrics database")
    update_interval: float = Field(2.0, description="Update interval in seconds")

class DatabaseConfig(BaseModel):
    """Database configuration"""
    main_db_path: str = Field("data/skilllab.db", description="Path to main database")
    pool_size: int = Field(5, description="Connection pool size")
    timeout: int = Field(30, description="Connection timeout in seconds")

class LoggingConfig(BaseModel):
    """Logging configuration"""
    level: str = Field("INFO", description="Logging level")
    file: str = Field("logs/skilllab.log", description="Log file path")
    max_size_mb: int = Field(10, description="Maximum log file size in MB")
    backup_count: int = Field(5, description="Number of backup log files to keep")
    
    @validator('level')
    def validate_level(cls, v):
        """Validate logging level"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v not in valid_levels:
            raise ValueError(f"level must be one of {valid_levels}")
        return v

class AppConfig(BaseModel):
    """Main application configuration"""
    paths: PathsConfig = Field(default_factory=PathsConfig)
    pipeline: PipelineConfig = Field(default_factory=PipelineConfig)
    gpu: GPUConfig = Field(default_factory=GPUConfig)
    ocr: OCRConfig = Field(default_factory=OCRConfig)
    json_generation: JSONGenerationConfig = Field(default_factory=JSONGenerationConfig)
    correction: CorrectionConfig = Field(default_factory=CorrectionConfig)
    dataset: DatasetConfig = Field(default_factory=DatasetConfig)
    training: TrainingConfig = Field(default_factory=TrainingConfig)
    review: ReviewConfig = Field(default_factory=ReviewConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)