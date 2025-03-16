"""
Base pipeline classes for SkillLab
Defines interfaces for pipeline steps and components
"""

import time
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union, Tuple

from config import get_config
from database import get_metrics_repository

# Setup logger
logger = logging.getLogger(__name__)

class PipelineContext:
    """Context object passed between pipeline steps"""
    
    def __init__(self, config=None, pipeline_run_id: Optional[int] = None):
        """
        Initialize pipeline context
        
        Args:
            config: Configuration (None to load from default)
            pipeline_run_id: ID of the current pipeline run
        """
        self.config = config or get_config()
        self.pipeline_run_id = pipeline_run_id
        self.step_results = {}
        self.start_time = time.time()
        self.metrics = get_metrics_repository()
        self.errors = []
        self.documents_processed = 0
    
    def set_result(self, step_name: str, result: Any) -> None:
        """
        Store result from a step
        
        Args:
            step_name: Name of the step
            result: Result data
        """
        self.step_results[step_name] = result
    
    def get_result(self, step_name: str) -> Any:
        """
        Get result from a previous step
        
        Args:
            step_name: Name of the step
            
        Returns:
            Result data or None if not found
        """
        return self.step_results.get(step_name)
    
    def add_error(self, step_name: str, error: str) -> None:
        """
        Add error to the context
        
        Args:
            step_name: Name of the step where error occurred
            error: Error message
        """
        self.errors.append({
            "step": step_name,
            "error": error,
            "time": time.time()
        })
    
    def has_errors(self) -> bool:
        """
        Check if context has errors
        
        Returns:
            True if errors exist, False otherwise
        """
        return len(self.errors) > 0
    
    def elapsed_time(self) -> float:
        """
        Get elapsed time since pipeline start
        
        Returns:
            Elapsed time in seconds
        """
        return time.time() - self.start_time
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get pipeline execution summary
        
        Returns:
            Dictionary with summary information
        """
        return {
            "elapsed_time": self.elapsed_time(),
            "documents_processed": self.documents_processed,
            "errors": len(self.errors),
            "steps_completed": list(self.step_results.keys())
        }

class PipelineStep(ABC):
    """Base class for pipeline steps"""
    
    def __init__(self, name: str):
        """
        Initialize pipeline step
        
        Args:
            name: Step name
        """
        self.name = name
        self.logger = logging.getLogger(f"pipeline.{name}")
    
    @abstractmethod
    def execute(self, context: PipelineContext) -> bool:
        """
        Execute the pipeline step
        
        Args:
            context: Pipeline context
            
        Returns:
            True if step executed successfully, False otherwise
        """
        pass
    
    def record_start(self, context: PipelineContext) -> int:
        """
        Record step execution start
        
        Args:
            context: Pipeline context
            
        Returns:
            Step execution ID
        """
        if context.pipeline_run_id and context.metrics:
            return context.metrics.record_step_execution(
                pipeline_run_id=context.pipeline_run_id,
                step_name=self.name,
                status="running",
                document_count=0
            )
        return -1
    
    def record_completion(
        self, 
        context: PipelineContext, 
        step_id: int, 
        success: bool, 
        count: int, 
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Record step execution completion
        
        Args:
            context: Pipeline context
            step_id: Step execution ID
            success: Whether step was successful
            count: Number of documents processed
            details: Optional execution details
        """
        if step_id > 0 and context.metrics:
            context.metrics.update_step_execution(
                step_id=step_id,
                status="completed" if success else "failed",
                document_count=count,
                details=details
            )

class Pipeline:
    """Pipeline executor"""
    
    def __init__(self, steps: List[PipelineStep]):
        """
        Initialize pipeline
        
        Args:
            steps: List of pipeline steps in execution order
        """
        self.steps = steps
        self.logger = logging.getLogger("pipeline")
    
    def execute(self, context: Optional[PipelineContext] = None) -> PipelineContext:
        """
        Execute the pipeline
        
        Args:
            context: Pipeline context (None to create new context)
            
        Returns:
            Updated pipeline context
        """
        # Create context if not provided
        if context is None:
            context = PipelineContext()
        
        # Record pipeline start
        if context.metrics:
            context.pipeline_run_id = context.metrics.start_pipeline_run(
                start_step=self.steps[0].name if self.steps else "unknown",
                end_step=self.steps[-1].name if self.steps else "unknown"
            )
        
        # Execute steps
        for step in self.steps:
            self.logger.info(f"Executing step: {step.name}")
            
            try:
                success = step.execute(context)
                
                if not success:
                    self.logger.error(f"Step {step.name} failed")
                    break
            except Exception as e:
                self.logger.error(f"Error in step {step.name}: {e}", exc_info=True)
                context.add_error(step.name, str(e))
                break
        
        # Record pipeline completion
        if context.pipeline_run_id and context.metrics:
            context.metrics.end_pipeline_run(
                run_id=context.pipeline_run_id,
                status="completed" if not context.has_errors() else "failed",
                document_count=context.documents_processed,
                details=context.get_summary()
            )
        
        return context

def create_step(name: str, step_cls, **kwargs) -> PipelineStep:
    """
    Create a pipeline step with the specified name and class
    
    Args:
        name: Step name
        step_cls: Step class
        **kwargs: Additional arguments for step constructor
        
    Returns:
        Initialized pipeline step
    """
    step = step_cls(name, **kwargs)
    return step