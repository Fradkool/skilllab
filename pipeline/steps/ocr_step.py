"""
OCR extraction step for SkillLab pipeline
Extracts text and structure from PDF resumes
"""

import os
import time
import glob
from typing import Dict, List, Any, Optional

from ..base import PipelineStep, PipelineContext
from extraction.ocr_extractor import OCRExtractor
from database import get_metrics_repository

class OCRExtractionStep(PipelineStep):
    """OCR extraction pipeline step"""
    
    def __init__(self, name: str = "ocr"):
        """
        Initialize OCR extraction step
        
        Args:
            name: Step name
        """
        super().__init__(name)
    
    def execute(self, context: PipelineContext) -> bool:
        """
        Execute OCR extraction step
        
        Args:
            context: Pipeline context
            
        Returns:
            True if step executed successfully, False otherwise
        """
        self.logger.info("Starting OCR extraction step")
        start_time = time.time()
        
        # Record step start
        step_id = self.record_start(context)
        
        try:
            # Get configuration
            config = context.config
            input_dir = config.paths.input_dir
            output_dir = config.paths.output_dir
            limit = config.pipeline.limit
            use_gpu = config.gpu.use_gpu_ocr
            
            # Initialize OCR extractor with service config
            extractor = OCRExtractor(
                use_gpu=use_gpu,
                lang=config.ocr.language,
                output_dir=output_dir,
                use_service=config.ocr.use_service,
                service_url=config.ocr.service_url
            )
            
            # Check input directory
            if not os.path.exists(input_dir):
                self.logger.error(f"Input directory not found: {input_dir}")
                context.add_error(self.name, f"Input directory not found: {input_dir}")
                return False
            
            # Get PDF files
            pdf_files = glob.glob(os.path.join(input_dir, "*.pdf"))
            if not pdf_files:
                self.logger.warning(f"No PDF files found in {input_dir}")
                
                # Record step completion
                self.record_completion(
                    context=context,
                    step_id=step_id,
                    success=True,
                    count=0,
                    details={"message": f"No PDF files found in {input_dir}"}
                )
                
                # Set empty result
                context.set_result(self.name, {"results": [], "count": 0, "time": 0})
                return True
            
            # Apply limit if specified
            if limit is not None and limit > 0:
                pdf_files = pdf_files[:limit]
                self.logger.info(f"Limited to {limit} PDF files")
            
            # Process files
            results = []
            metrics_repo = get_metrics_repository()
            
            for pdf_file in pdf_files:
                file_name = os.path.basename(pdf_file)
                
                try:
                    # Generate document ID from filename
                    doc_id = os.path.splitext(file_name)[0]
                    
                    # Register document for metrics
                    if metrics_repo:
                        metrics_repo.register_document(doc_id, file_name)
                    
                    # Process the file
                    self.logger.info(f"Processing {file_name}")
                    result = extractor.process_resume(
                        pdf_path=pdf_file,
                        min_confidence=config.ocr.min_confidence,
                        dpi=config.ocr.dpi
                    )
                    
                    # Update metrics
                    if metrics_repo:
                        ocr_result = result.get("result", {})
                        
                        # Calculate average OCR confidence
                        confidences = []
                        for page_result in ocr_result.get("page_results", []):
                            for element in page_result.get("text_elements", []):
                                if "confidence" in element:
                                    confidences.append(element["confidence"])
                        
                        if confidences:
                            ocr_confidence = sum(confidences) / len(confidences) * 100
                            metrics_repo.update_document_confidence(doc_id, ocr_confidence=ocr_confidence)
                            
                            # Flag if OCR confidence is below threshold
                            if ocr_confidence < 75:
                                metrics_repo.flag_for_review(
                                    doc_id,
                                    "low_ocr_confidence",
                                    f"OCR confidence score ({ocr_confidence:.1f}%) below threshold"
                                )
                        
                        # Update document status
                        metrics_repo.update_document_status(doc_id, "ocr_complete")
                    
                    results.append(result)
                except Exception as e:
                    self.logger.error(f"Error processing {file_name}: {e}")
                    # Continue with next file
            
            # Set result in context
            context.documents_processed = len(results)
            context.set_result(self.name, {
                "results": results,
                "count": len(results),
                "time": time.time() - start_time
            })
            
            elapsed_time = time.time() - start_time
            self.logger.info(
                f"OCR extraction completed in {elapsed_time:.2f}s - {len(results)} documents processed"
            )
            
            # Record step completion
            self.record_completion(
                context=context,
                step_id=step_id,
                success=True,
                count=len(results),
                details={
                    "time": elapsed_time,
                    "resumes_processed": len(results),
                    "input_dir": input_dir,
                    "output_dir": output_dir
                }
            )
            
            return True
        except Exception as e:
            elapsed_time = time.time() - start_time
            self.logger.error(f"OCR extraction step failed after {elapsed_time:.2f}s: {e}")
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