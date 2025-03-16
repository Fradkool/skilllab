"""
OCR Service Client
Client for interacting with the containerized PaddleOCR service
"""

import os
import json
import time
import requests
from typing import Dict, List, Any, Optional
from pathlib import Path

from utils.logger import setup_logger

logger = setup_logger("ocr_service_client")

class OCRServiceClient:
    """Client for interacting with the containerized PaddleOCR service"""
    
    def __init__(self, service_url: str, output_dir: str = "data/output"):
        """
        Initialize OCR service client
        
        Args:
            service_url: URL for PaddleOCR service API
            output_dir: Directory to save output images and extracted text
        """
        logger.info(f"Initializing OCR Service Client (Service URL: {service_url})")
        self.service_url = service_url
        self.output_dir = output_dir
        
        # Create output directories if they don't exist
        os.makedirs(os.path.join(output_dir, "images"), exist_ok=True)
        os.makedirs(os.path.join(output_dir, "ocr_results"), exist_ok=True)
    
    def check_health(self) -> bool:
        """
        Check if the OCR service is healthy
        
        Returns:
            True if the service is healthy, False otherwise
        """
        try:
            health_url = self.service_url.replace("/v1/ocr/process_pdf", "/health")
            response = requests.get(health_url, timeout=5)
            if response.status_code == 200 and response.json().get("status") == "healthy":
                logger.info("OCR service is healthy")
                return True
            else:
                logger.warning(f"OCR service health check failed: {response.text}")
                return False
        except Exception as e:
            logger.error(f"OCR service health check failed: {str(e)}")
            return False
    
    def process_pdf(
        self, 
        pdf_path: str, 
        output_prefix: Optional[str] = None,
        use_gpu: bool = False,
        language: str = "en",
        min_confidence: float = 0.5,
        dpi: int = 300
    ) -> Dict[str, Any]:
        """
        Process a PDF using the OCR service
        
        Args:
            pdf_path: Path to PDF file
            output_prefix: Prefix for output files (defaults to filename without extension)
            use_gpu: Whether to use GPU for OCR
            language: Language for OCR
            min_confidence: Minimum confidence score for OCR results
            dpi: DPI for PDF to image conversion
            
        Returns:
            Dictionary with processing results and paths to output files
        """
        logger.info(f"Processing PDF with OCR service: {pdf_path}")
        start_time = time.time()
        
        # Generate output prefix if not provided
        if output_prefix is None:
            output_prefix = os.path.splitext(os.path.basename(pdf_path))[0]
        
        # Register with monitoring if available
        try:
            from monitor.integration import get_monitoring
            monitoring = get_monitoring()
            if monitoring:
                monitoring.register_document(output_prefix, os.path.basename(pdf_path))
        except ImportError:
            pass
        
        # Prepare files and form data
        files = {"file": (os.path.basename(pdf_path), open(pdf_path, "rb"), "application/pdf")}
        form_data = {
            "use_gpu": str(use_gpu).lower(),
            "language": language,
            "min_confidence": str(min_confidence),
            "dpi": str(dpi)
        }
        
        try:
            # Send PDF to OCR service
            response = requests.post(
                self.service_url,
                files=files,
                data=form_data,
                timeout=300  # 5 minutes timeout for large files
            )
            
            # Check for errors
            if response.status_code != 200:
                logger.error(f"OCR service error: {response.text}")
                raise Exception(f"OCR service error: {response.status_code} - {response.text}")
            
            # Parse response
            ocr_result = response.json()
            
            # Update image paths to be relative to the local filesystem
            saved_image_paths = []
            for container_path in ocr_result["image_paths"]:
                # Convert container path to local path
                # Example: /app/data/output/images/1234_document_page_1.png -> data/output/images/1234_document_page_1.png
                local_path = container_path.replace("/app/", "")
                saved_image_paths.append(local_path)
            
            # Create result structure with local paths
            result = {
                "file_id": ocr_result["file_id"],
                "original_path": pdf_path,
                "page_count": ocr_result["page_count"],
                "image_paths": saved_image_paths,
                "total_text_elements": ocr_result["total_text_elements"],
                "page_results": ocr_result["page_results"],
                "combined_text": ocr_result["combined_text"]
            }
            
            # Get result path from container result path
            container_result_path = f"/app/data/output/ocr_results/{ocr_result['file_id']}_ocr.json"
            result_path = container_result_path.replace("/app/", "")
            
            elapsed = time.time() - start_time
            logger.info(f"PDF processing completed in {elapsed:.2f}s - {result['total_text_elements']} text elements extracted")
            
            return {
                "result": result,
                "result_path": result_path,
                "image_paths": saved_image_paths
            }
            
        except Exception as e:
            logger.error(f"Error calling OCR service: {str(e)}")
            raise
        finally:
            # Close the file
            files["file"][1].close()
    
    def process_image(
        self,
        image_path: str,
        output_prefix: Optional[str] = None,
        use_gpu: bool = False,
        language: str = "en",
        min_confidence: float = 0.5
    ) -> Dict[str, Any]:
        """
        Process an image using the OCR service
        
        Args:
            image_path: Path to image file
            output_prefix: Prefix for output files (defaults to filename without extension)
            use_gpu: Whether to use GPU for OCR
            language: Language for OCR
            min_confidence: Minimum confidence score for OCR results
            
        Returns:
            Dictionary with processing results and paths to output files
        """
        logger.info(f"Processing image with OCR service: {image_path}")
        start_time = time.time()
        
        # Generate output prefix if not provided
        if output_prefix is None:
            output_prefix = os.path.splitext(os.path.basename(image_path))[0]
            
        # Prepare service URL
        service_url = self.service_url.replace("process_pdf", "process_image")
            
        # Prepare files and form data
        files = {"file": (os.path.basename(image_path), open(image_path, "rb"))}
        form_data = {
            "use_gpu": str(use_gpu).lower(),
            "language": language,
            "min_confidence": str(min_confidence)
        }
        
        try:
            # Send image to OCR service
            response = requests.post(
                service_url,
                files=files,
                data=form_data,
                timeout=120  # 2 minutes timeout
            )
            
            # Check for errors
            if response.status_code != 200:
                logger.error(f"OCR service error: {response.text}")
                raise Exception(f"OCR service error: {response.status_code} - {response.text}")
            
            # Parse response
            ocr_result = response.json()
            
            # Update image paths to be relative to the local filesystem
            saved_image_paths = []
            for container_path in ocr_result["image_paths"]:
                # Convert container path to local path
                local_path = container_path.replace("/app/", "")
                saved_image_paths.append(local_path)
                
            # Create result structure with local paths
            result = {
                "file_id": ocr_result["file_id"],
                "original_path": image_path,
                "page_count": ocr_result["page_count"],
                "image_paths": saved_image_paths,
                "total_text_elements": ocr_result["total_text_elements"],
                "page_results": ocr_result["page_results"],
                "combined_text": ocr_result["combined_text"]
            }
            
            # Get result path from container result path
            container_result_path = f"/app/data/output/ocr_results/{ocr_result['file_id']}_ocr.json"
            result_path = container_result_path.replace("/app/", "")
            
            elapsed = time.time() - start_time
            logger.info(f"Image processing completed in {elapsed:.2f}s - {result['total_text_elements']} text elements extracted")
            
            return {
                "result": result,
                "result_path": result_path,
                "image_paths": saved_image_paths
            }
            
        except Exception as e:
            logger.error(f"Error calling OCR service: {str(e)}")
            raise
        finally:
            # Close the file
            files["file"][1].close()