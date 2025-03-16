"""
Pipeline executor for SkillLab
Manages execution of the complete pipeline
"""

import time
import logging
from typing import Dict, List, Any, Optional, Union, Tuple

from config import get_config, AppConfig
from .base import Pipeline, PipelineStep, PipelineContext

# Import steps
from .steps.ocr_step import OCRExtractionStep
from .steps.json_generation_step import JSONGenerationStep
from .steps.correction_step import CorrectionStep
from .steps.dataset_step import DatasetStep
from .steps.training_step import TrainingStep

# Setup logger
logger = logging.getLogger(__name__)

class PipelineExecutor:
    """Manages execution of the SkillLab pipeline"""
    
    def __init__(self, config: Optional[AppConfig] = None):
        """
        Initialize pipeline executor
        
        Args:
            config: Configuration (None to load from default)
        """
        self.config = config or get_config()
        self.pipelines = {}
        
        # Register standard pipelines
        self._register_standard_pipelines()
    
    def _register_standard_pipelines(self) -> None:
        """Register standard pipelines"""
        # Full pipeline
        self.register_pipeline(
            "full",
            [
                OCRExtractionStep("ocr"),
                JSONGenerationStep("json"),
                CorrectionStep("correction"),
                DatasetStep("dataset"),
                TrainingStep("training")
            ]
        )
        
        # Extraction only (OCR)
        self.register_pipeline(
            "extract",
            [OCRExtractionStep("ocr")]
        )
        
        # Structure only (JSON generation and correction)
        self.register_pipeline(
            "structure",
            [
                JSONGenerationStep("json"),
                CorrectionStep("correction")
            ]
        )
        
        # Training only (dataset creation and training)
        self.register_pipeline(
            "train",
            [
                DatasetStep("dataset"),
                TrainingStep("training")
            ]
        )
    
    def register_pipeline(self, name: str, steps: List[PipelineStep]) -> None:
        """
        Register a pipeline
        
        Args:
            name: Pipeline name
            steps: List of pipeline steps
        """
        self.pipelines[name] = Pipeline(steps)
        logger.info(f"Registered pipeline '{name}' with {len(steps)} steps")
    
    def get_pipeline(self, name: str) -> Optional[Pipeline]:
        """
        Get a registered pipeline by name
        
        Args:
            name: Pipeline name
            
        Returns:
            Pipeline or None if not found
        """
        return self.pipelines.get(name)
    
    def run_pipeline(
        self, 
        name: str, 
        start_step: Optional[str] = None, 
        end_step: Optional[str] = None,
        context: Optional[PipelineContext] = None
    ) -> PipelineContext:
        """
        Run a pipeline
        
        Args:
            name: Pipeline name
            start_step: Step to start from (None to start from beginning)
            end_step: Step to end at (None to run to end)
            context: Optional pipeline context
            
        Returns:
            Pipeline context with results
            
        Raises:
            ValueError: If pipeline not found or invalid steps specified
        """
        pipeline = self.get_pipeline(name)
        if not pipeline:
            raise ValueError(f"Pipeline '{name}' not found")
        
        # Create filtered pipeline if start/end steps specified
        if start_step or end_step:
            filtered_steps = []
            
            # Get all step names
            step_names = [step.name for step in pipeline.steps]
            
            # Validate steps
            if start_step and start_step not in step_names:
                raise ValueError(f"Start step '{start_step}' not found in pipeline")
            if end_step and end_step not in step_names:
                raise ValueError(f"End step '{end_step}' not found in pipeline")
            
            # Get start and end indices
            start_idx = step_names.index(start_step) if start_step else 0
            end_idx = step_names.index(end_step) if end_step else len(step_names) - 1
            
            if start_idx > end_idx:
                raise ValueError(f"Start step '{start_step}' comes after end step '{end_step}'")
            
            # Create filtered pipeline
            filtered_steps = pipeline.steps[start_idx:end_idx + 1]
            pipeline = Pipeline(filtered_steps)
        
        # Create context if not provided
        if context is None:
            context = PipelineContext(config=self.config)
        
        # Run pipeline
        logger.info(f"Running pipeline '{name}'")
        start_time = time.time()
        
        try:
            context = pipeline.execute(context)
            
            elapsed_time = time.time() - start_time
            logger.info(f"Pipeline '{name}' completed in {elapsed_time:.2f}s")
            
            # Log any errors
            if context.has_errors():
                logger.error(f"Pipeline completed with {len(context.errors)} errors")
                for error in context.errors:
                    logger.error(f"Error in step {error['step']}: {error['error']}")
            
            return context
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(f"Pipeline '{name}' failed after {elapsed_time:.2f}s: {e}", exc_info=True)
            
            # Add error to context
            if context:
                context.add_error("executor", str(e))
            
            raise
    
    def run_from_config(self) -> PipelineContext:
        """
        Run pipeline based on configuration
        
        Returns:
            Pipeline context with results
        """
        # Get pipeline configuration
        start_step = self.config.pipeline.start_step
        end_step = self.config.pipeline.end_step
        
        # Create context
        context = PipelineContext(config=self.config)
        
        # Run pipeline
        return self.run_pipeline(
            name="full",
            start_step=start_step,
            end_step=end_step,
            context=context
        )

# Global executor instance
_executor_instance = None

def get_executor() -> PipelineExecutor:
    """
    Get global pipeline executor instance
    
    Returns:
        Pipeline executor
    """
    global _executor_instance
    
    if _executor_instance is None:
        _executor_instance = PipelineExecutor()
    
    return _executor_instance