"""
PaddleOCR Service Wrapper
Provides a REST API for PaddleOCR
"""

import os
import time
import json
import logging
import numpy as np
import pdf2image
import tempfile
import uvicorn
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from paddleocr import PaddleOCR
from PIL import Image

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("paddleocr_service")

# Initialize FastAPI
app = FastAPI(
    title="PaddleOCR Service",
    description="REST API for PaddleOCR",
    version="1.0.0"
)

# Create output directories
os.makedirs("/app/data/output/images", exist_ok=True)
os.makedirs("/app/data/output/ocr_results", exist_ok=True)

class OCRRequest(BaseModel):
    """Request model for OCR endpoints"""
    use_gpu: bool = False
    language: str = "en"
    min_confidence: float = 0.5
    dpi: int = 300

class OCRResponse(BaseModel):
    """Response model for OCR endpoints"""
    file_id: str
    original_path: str
    page_count: int
    image_paths: List[str]
    total_text_elements: int
    page_results: List[Dict[str, Any]]
    combined_text: str
    processing_time: float

# Global variable for OCR engines
ocr_engines = {}

def get_ocr_engine(lang: str = "en", use_gpu: bool = False) -> PaddleOCR:
    """
    Get or create an OCR engine for the specified language
    
    Args:
        lang: Language for OCR
        use_gpu: Whether to use GPU
        
    Returns:
        PaddleOCR engine
    """
    key = f"{lang}_{use_gpu}"
    if key not in ocr_engines:
        logger.info(f"Initializing OCR engine (Language: {lang}, GPU: {use_gpu})")
        ocr_engines[key] = PaddleOCR(use_angle_cls=True, lang=lang, use_gpu=use_gpu)
    return ocr_engines[key]

def extract_text_and_boxes(ocr_engine: PaddleOCR, image: Image.Image, min_confidence: float = 0.5) -> Dict[str, Any]:
    """
    Extract text and bounding boxes from an image
    
    Args:
        ocr_engine: PaddleOCR engine
        image: PIL Image object
        min_confidence: Minimum confidence score for OCR results
        
    Returns:
        Dictionary with extracted text and bounding boxes
    """
    # Convert PIL image to numpy array
    img_np = np.array(image)
    
    # Run OCR
    result = ocr_engine.ocr(img_np, cls=True)
    
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
    
    return {
        "text_elements": processed_result,
        "full_text": " ".join(full_text),
        "text_count": len(processed_result)
    }

@app.post("/v1/ocr/process_pdf", response_model=OCRResponse)
async def process_pdf(
    file: UploadFile = File(...),
    use_gpu: bool = Form(False),
    language: str = Form("en"),
    min_confidence: float = Form(0.5),
    dpi: int = Form(300)
):
    """
    Process a PDF file and extract text using OCR
    
    Args:
        file: PDF file
        use_gpu: Whether to use GPU
        language: Language for OCR
        min_confidence: Minimum confidence score
        dpi: DPI for PDF to image conversion
    
    Returns:
        OCR results
    """
    start_time = time.time()
    logger.info(f"Processing PDF: {file.filename} (Language: {language}, GPU: {use_gpu})")
    
    # Create a unique file ID
    file_id = f"{int(time.time())}_{os.path.splitext(file.filename)[0]}"
    
    try:
        # Save the uploaded file to a temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_file.write(await file.read())
            pdf_path = temp_file.name
        
        # Get OCR engine
        ocr_engine = get_ocr_engine(language, use_gpu)
        
        # Convert PDF to images
        images = pdf2image.convert_from_path(pdf_path, dpi=dpi)
        
        all_results = []
        all_text = []
        saved_image_paths = []
        
        # Process each page
        for i, image in enumerate(images):
            # Save the high-res image
            image_path = f"/app/data/output/images/{file_id}_page_{i+1}.png"
            image.save(image_path)
            saved_image_paths.append(image_path)
            
            # Extract text and boxes
            ocr_result = extract_text_and_boxes(ocr_engine, image, min_confidence)
            all_results.append(ocr_result)
            all_text.append(ocr_result["full_text"])
        
        # Combine results from all pages
        combined_text = " ".join(all_text)
        combined_result = {
            "file_id": file_id,
            "original_path": file.filename,
            "page_count": len(images),
            "image_paths": saved_image_paths,
            "total_text_elements": sum(r["text_count"] for r in all_results),
            "page_results": all_results,
            "combined_text": combined_text,
            "processing_time": time.time() - start_time
        }
        
        # Save OCR results
        result_path = f"/app/data/output/ocr_results/{file_id}_ocr.json"
        with open(result_path, 'w', encoding='utf-8') as f:
            json.dump(combined_result, f, ensure_ascii=False, indent=2)
        
        # Clean up temporary file
        os.unlink(pdf_path)
        
        logger.info(f"PDF processing completed in {combined_result['processing_time']:.2f}s")
        return combined_result
    
    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")

@app.post("/v1/ocr/process_image", response_model=OCRResponse)
async def process_image(
    file: UploadFile = File(...),
    use_gpu: bool = Form(False),
    language: str = Form("en"),
    min_confidence: float = Form(0.5)
):
    """
    Process an image file and extract text using OCR
    
    Args:
        file: Image file (PNG, JPG, etc.)
        use_gpu: Whether to use GPU
        language: Language for OCR
        min_confidence: Minimum confidence score
    
    Returns:
        OCR results
    """
    start_time = time.time()
    logger.info(f"Processing image: {file.filename} (Language: {language}, GPU: {use_gpu})")
    
    # Create a unique file ID
    file_id = f"{int(time.time())}_{os.path.splitext(file.filename)[0]}"
    
    try:
        # Save the uploaded file to a temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
            temp_file.write(await file.read())
            image_path = temp_file.name
        
        # Get OCR engine
        ocr_engine = get_ocr_engine(language, use_gpu)
        
        # Open image
        image = Image.open(image_path)
        
        # Save the image
        saved_image_path = f"/app/data/output/images/{file_id}{os.path.splitext(file.filename)[1]}"
        image.save(saved_image_path)
        
        # Extract text and boxes
        ocr_result = extract_text_and_boxes(ocr_engine, image, min_confidence)
        
        # Create result structure
        combined_result = {
            "file_id": file_id,
            "original_path": file.filename,
            "page_count": 1,
            "image_paths": [saved_image_path],
            "total_text_elements": ocr_result["text_count"],
            "page_results": [ocr_result],
            "combined_text": ocr_result["full_text"],
            "processing_time": time.time() - start_time
        }
        
        # Save OCR results
        result_path = f"/app/data/output/ocr_results/{file_id}_ocr.json"
        with open(result_path, 'w', encoding='utf-8') as f:
            json.dump(combined_result, f, ensure_ascii=False, indent=2)
        
        # Clean up temporary file
        os.unlink(image_path)
        
        logger.info(f"Image processing completed in {combined_result['processing_time']:.2f}s")
        return combined_result
    
    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "paddleocr"}

if __name__ == "__main__":
    # Run the API server
    uvicorn.run(app, host="0.0.0.0", port=8080)