"""
OCR Extractor module for SkillLab
Uses PaddleOCR for text and bounding box extraction from resumes
Supports both direct PaddleOCR usage and containerized PaddleOCR service
"""

import os
import time
import json
import pdf2image
import numpy as np
from typing import Dict, List, Tuple, Any, Optional
from paddleocr import PaddleOCR
from PIL import Image
import requests

from utils.logger import setup_logger
from extraction.ocr_service_client import OCRServiceClient

logger = setup_logger("ocr_extractor")

class OCRExtractor:
    """
    Extract text and bounding boxes from resume PDFs using PaddleOCR
    Supports both direct PaddleOCR usage and containerized PaddleOCR service
    """
    
    def __init__(
        self, 
        use_gpu: bool = False, 
        lang: str = "en", 
        output_dir: str = "data/output",
        use_service: bool = False,
        service_url: Optional[str] = None
    ):
        """
        Initialize OCR extractor
        
        Args:
            use_gpu: Whether to use GPU for OCR
            lang: Language for OCR
            output_dir: Directory to save output images and extracted text
            use_service: Whether to use the containerized PaddleOCR service
            service_url: URL for PaddleOCR service API (required if use_service is True)
        """
        self.use_gpu = use_gpu
        self.lang = lang
        self.output_dir = output_dir
        self.use_service = use_service
        
        # Create output directories if they don't exist
        os.makedirs(os.path.join(output_dir, "images"), exist_ok=True)
        os.makedirs(os.path.join(output_dir, "ocr_results"), exist_ok=True)
        
        if use_service:
            if not service_url:
                raise ValueError("service_url must be provided when use_service is True")
            
            logger.info(f"Initializing OCR Extractor with Service (Service URL: {service_url})")
            self.service_client = OCRServiceClient(service_url, output_dir)
            
            # Verify service connectivity
            if not self.service_client.check_health():
                logger.warning("OCR service is not healthy. Will retry when processing.")
        else:
            logger.info(f"Initializing OCR Extractor with direct PaddleOCR (GPU: {use_gpu}, Language: {lang})")
            self.ocr = PaddleOCR(use_angle_cls=True, lang=lang, use_gpu=use_gpu)
    
    def convert_pdf_to_image(self, pdf_path: str, dpi: int = 300) -> List[Image.Image]:
        """
        Convert PDF to high-resolution images
        
        Args:
            pdf_path: Path to PDF file
            dpi: DPI for conversion (higher means better quality but larger files)
            
        Returns:
            List of PIL Image objects
        """
        logger.info(f"Converting PDF to image: {pdf_path} (DPI: {dpi})")
        start_time = time.time()
        
        # Convert PDF to images
        images = pdf2image.convert_from_path(pdf_path, dpi=dpi)
        
        elapsed = time.time() - start_time
        logger.info(f"PDF conversion completed in {elapsed:.2f}s - {len(images)} pages extracted")
        return images
    
    def extract_text_and_boxes(self, image: Image.Image, min_confidence: float = 0.5) -> Dict[str, Any]:
        """
        Extract text and bounding boxes from an image
        
        Args:
            image: PIL Image object
            min_confidence: Minimum confidence score for OCR results
            
        Returns:
            Dictionary with extracted text and bounding boxes
        """
        start_time = time.time()
        
        # Convert PIL image to numpy array
        img_np = np.array(image)
        
        # Run OCR
        result = self.ocr.ocr(img_np, cls=True)
        
        # Process and filter results
        processed_result = []
        full_text = []
        
        if result and len(result) > 0 and result[0]:
            for line in result[0]:
                box, (text, confidence) = line
                if confidence >= min_confidence:
                    processed_result.append({
                        "text": text,
                        "bbox": box,
                        "confidence": float(confidence)
                    })
                    full_text.append(text)
        
        elapsed = time.time() - start_time
        logger.info(f"OCR extraction completed in {elapsed:.2f}s - {len(processed_result)} text elements extracted")
        
        return {
            "text_elements": processed_result,
            "full_text": " ".join(full_text),
            "text_count": len(processed_result)
        }
    
    def process_resume(
        self, 
        pdf_path: str, 
        output_prefix: Optional[str] = None, 
        min_confidence: float = 0.5,
        dpi: int = 300
    ) -> Dict[str, Any]:
        """
        Process a resume PDF to extract text and save results
        
        Args:
            pdf_path: Path to PDF file
            output_prefix: Prefix for output files (defaults to filename without extension)
            min_confidence: Minimum confidence score for OCR results
            dpi: DPI for PDF to image conversion
            
        Returns:
            Dictionary with processing results and paths to output files
        """
        logger.info(f"Processing resume: {pdf_path}")
        
        # Generate output prefix if not provided
        if output_prefix is None:
            output_prefix = os.path.splitext(os.path.basename(pdf_path))[0]
        
        # If using OCR service, delegate to the service client
        if self.use_service:
            try:
                # Check if service is healthy (retry connection if needed)
                if not hasattr(self, '_service_checked') or not self._service_checked:
                    healthy = self.service_client.check_health()
                    if not healthy:
                        logger.warning("OCR service is not responding. Will retry once.")
                        # Wait 2 seconds and retry
                        time.sleep(2)
                        healthy = self.service_client.check_health()
                        if not healthy:
                            raise Exception("OCR service is not available. Please ensure the Docker container is running.")
                    self._service_checked = True
                
                # Process the PDF using the OCR service
                return self.service_client.process_pdf(
                    pdf_path=pdf_path,
                    output_prefix=output_prefix,
                    use_gpu=self.use_gpu,
                    language=self.lang,
                    min_confidence=min_confidence,
                    dpi=dpi
                )
            except Exception as e:
                logger.error(f"Error using OCR service: {str(e)}")
                logger.info("Falling back to direct PaddleOCR usage")
                # If service fails, initialize direct PaddleOCR as fallback
                if not hasattr(self, 'ocr'):
                    logger.info(f"Initializing fallback OCR engine (GPU: {self.use_gpu}, Language: {self.lang})")
                    self.ocr = PaddleOCR(use_angle_cls=True, lang=self.lang, use_gpu=self.use_gpu)
        
        # Direct PaddleOCR usage
        start_time = time.time()
        
        # Register with monitoring if available
        try:
            from monitor.integration import get_monitoring
            monitoring = get_monitoring()
            if monitoring:
                monitoring.register_document(output_prefix, os.path.basename(pdf_path))
        except ImportError:
            pass
        
        # Convert PDF to images
        images = self.convert_pdf_to_image(pdf_path, dpi)
        
        all_results = []
        all_text = []
        saved_image_paths = []
        
        # Process each page
        for i, image in enumerate(images):
            # Save the high-res image
            image_path = os.path.join(self.output_dir, "images", f"{output_prefix}_page_{i+1}.png")
            image.save(image_path)
            saved_image_paths.append(image_path)
            
            # Extract text and boxes
            ocr_result = self.extract_text_and_boxes(image, min_confidence)
            all_results.append(ocr_result)
            all_text.append(ocr_result["full_text"])
        
        # Combine results from all pages
        combined_text = " ".join(all_text)
        combined_result = {
            "file_id": output_prefix,
            "original_path": pdf_path,
            "page_count": len(images),
            "image_paths": saved_image_paths,
            "total_text_elements": sum(r["text_count"] for r in all_results),
            "page_results": all_results,
            "combined_text": combined_text
        }
        
        # Save OCR results
        result_path = os.path.join(self.output_dir, "ocr_results", f"{output_prefix}_ocr.json")
        with open(result_path, 'w', encoding='utf-8') as f:
            json.dump(combined_result, f, ensure_ascii=False, indent=2)
        
        elapsed = time.time() - start_time
        logger.info(f"Resume processing completed in {elapsed:.2f}s - {len(combined_text)} characters extracted")
        
        return {
            "result": combined_result,
            "result_path": result_path,
            "image_paths": saved_image_paths
        }
    
    def batch_process(
        self, 
        pdf_dir: str, 
        limit: Optional[int] = None,
        min_confidence: float = 0.5,
        dpi: int = 300
    ) -> List[Dict[str, Any]]:
        """
        Process multiple resume PDFs in a directory
        
        Args:
            pdf_dir: Directory containing PDF files
            limit: Maximum number of PDFs to process (None for all)
            min_confidence: Minimum confidence score for OCR results
            dpi: DPI for PDF to image conversion
            
        Returns:
            List of processing results
        """
        pdf_files = [f for f in os.listdir(pdf_dir) if f.lower().endswith('.pdf')]
        
        if limit is not None:
            pdf_files = pdf_files[:limit]
        
        logger.info(f"Batch processing {len(pdf_files)} resume PDFs from {pdf_dir}")
        
        # If using OCR service, check health once before batch processing
        if self.use_service:
            healthy = self.service_client.check_health()
            if not healthy:
                logger.warning("OCR service is not responding. Will retry during processing.")
        
        results = []
        for pdf_file in pdf_files:
            pdf_path = os.path.join(pdf_dir, pdf_file)
            try:
                result = self.process_resume(
                    pdf_path=pdf_path,
                    min_confidence=min_confidence,
                    dpi=dpi
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Error processing {pdf_path}: {str(e)}")
        
        logger.info(f"Batch processing completed - {len(results)} resumes processed successfully")
        return results

if __name__ == "__main__":
    # Test the OCR extractor
    extractor = OCRExtractor()
    result = extractor.process_resume("data/input/sample_resume.pdf")
    print(f"Extracted {result['result']['total_text_elements']} text elements")