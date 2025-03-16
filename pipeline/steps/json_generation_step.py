"""
JSON Generation step for SkillLab pipeline
Generates structured JSON from OCR-extracted text using Mistral 7B
"""

import os
import time
import json
from typing import Dict, List, Any, Optional

from ..base import PipelineStep, PipelineContext
from extraction.json_generator import JSONGenerator
from utils.gpu_monitor import GPUMonitor, HAS_GPU_LIBRARIES
from database import get_metrics_repository

class JSONGenerationStep(PipelineStep):
    """JSON generation pipeline step"""
    
    def __init__(self, name: str = "json"):
        """
        Initialize JSON generation step
        
        Args:
            name: Step name
        """
        super().__init__(name)
    
    def execute(self, context: PipelineContext) -> bool:
        """
        Execute JSON generation step
        
        Args:
            context: Pipeline context
            
        Returns:
            True if step executed successfully, False otherwise
        """
        self.logger.info("Starting JSON generation step")
        start_time = time.time()
        
        # Record step start
        step_id = self.record_start(context)
        
        try:
            # Get configuration
            config = context.config
            output_dir = os.path.join(config.paths.output_dir, "json_results")
            
            # Get OCR results from previous step
            ocr_results = context.get_result("ocr")
            if not ocr_results or "results" not in ocr_results:
                self.logger.error("No OCR results found in context")
                context.add_error(self.name, "No OCR results found in context")
                return False
            
            ocr_data = ocr_results["results"]
            if not ocr_data:
                self.logger.warning("No OCR data available for JSON generation")
                
                # Record step completion
                self.record_completion(
                    context=context,
                    step_id=step_id,
                    success=True,
                    count=0,
                    details={"message": "No OCR data available for JSON generation"}
                )
                
                # Set empty result
                context.set_result(self.name, {"results": [], "count": 0, "time": 0})
                return True
            
            # Setup GPU monitoring if enabled
            gpu_monitor = None
            if config.gpu.monitor and HAS_GPU_LIBRARIES:
                gpu_monitor = GPUMonitor()
            
            # Initialize JSON generator with config options
            generator = JSONGenerator(
                ollama_url=config.json_generation.ollama_url,
                model_name=config.json_generation.model_name,
                output_dir=output_dir,
                gpu_monitor=gpu_monitor,
                max_retries=config.json_generation.max_retries
            )
            
            # Process each OCR result
            json_results = []
            metrics_repo = get_metrics_repository()
            
            for ocr_item in ocr_data:
                file_id = ocr_item.get("result", {}).get("file_id", "unknown")
                
                try:
                    # Process the OCR result
                    self.logger.info(f"Generating structured JSON for {file_id}")
                    
                    result = generator.process_ocr_result(
                        ocr_item.get("result", {}),
                    )
                    
                    # Update metrics
                    if metrics_repo:
                        # Check if there's reasonable data in the JSON
                        json_data = result.get("json_data", {})
                        has_name = json_data.get("Name") not in (None, "")
                        has_skills = len(json_data.get("Skills", [])) > 0
                        has_experience = len(json_data.get("Experience", [])) > 0
                        
                        # Calculate completeness percentage
                        fields = ["Name", "Email", "Phone", "Current_Position", "Skills", "Experience"]
                        filled = sum(1 for f in fields if json_data.get(f) not in (None, "", []))
                        completeness = filled / len(fields) * 100
                        
                        # Update metrics
                        metrics_repo.update_json_completeness(file_id, completeness)
                        
                        # Flag if completeness is low
                        if completeness < 50:
                            metrics_repo.flag_for_review(
                                file_id,
                                "low_json_completeness",
                                f"JSON completeness score ({completeness:.1f}%) below threshold"
                            )
                        
                        # Update document status
                        metrics_repo.update_document_status(file_id, "json_complete")
                    
                    json_results.append(result)
                except Exception as e:
                    self.logger.error(f"Error processing {file_id}: {e}")
                    # Continue with next file
            
            # Set result in context
            context.set_result(self.name, {
                "results": json_results,
                "count": len(json_results),
                "time": time.time() - start_time
            })
            
            elapsed_time = time.time() - start_time
            self.logger.info(
                f"JSON generation completed in {elapsed_time:.2f}s - {len(json_results)} documents processed"
            )
            
            # Record step completion
            self.record_completion(
                context=context,
                step_id=step_id,
                success=True,
                count=len(json_results),
                details={
                    "time": elapsed_time,
                    "jsons_generated": len(json_results),
                    "output_dir": output_dir
                }
            )
            
            return True
        except Exception as e:
            elapsed_time = time.time() - start_time
            self.logger.error(f"JSON generation step failed after {elapsed_time:.2f}s: {e}")
            context.add_error(self.name, str(e))
            
            # Record step completion
            self.record_completion(
                context=context,
                step_id=step_id,
                success=False,
                count=0,
                details={"error": str(e), "time": elapsed_time}
            )
            
            return False