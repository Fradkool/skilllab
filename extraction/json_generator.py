"""
JSON Generator module for SkillLab
Uses Mistral 7B via Ollama to generate structured JSON from OCR text
Supports both direct Ollama API calls and containerized Ollama service
"""

import os
import time
import json
import requests
from typing import Dict, List, Any, Optional, Tuple

from utils.logger import setup_logger
from utils.gpu_monitor import GPUMonitor, HAS_GPU_LIBRARIES
from extraction.ollama_client import OllamaClient
import torch

logger = setup_logger("json_generator")

class JSONGenerator:
    """
    Generate structured JSON from OCR-extracted text using Mistral 7B via Ollama
    Supports both direct Ollama API calls and containerized Ollama service
    """
    
    def __init__(
        self, 
        ollama_url: str = "http://localhost:11434/api/generate",
        model_name: str = "mistral:7b-instruct-v0.2-q8_0",
        output_dir: str = "data/output/json_results",
        gpu_monitor: Optional[GPUMonitor] = None,
        max_retries: int = 3
    ):
        """
        Initialize JSON Generator
        
        Args:
            ollama_url: URL for Ollama API
            model_name: Model to use for generation (8-bit quantized Mistral)
            output_dir: Directory to save generated JSONs
            gpu_monitor: Optional GPU monitor for tracking GPU usage
            max_retries: Maximum number of retries for Ollama API calls
        """
        logger.info(f"Initializing JSON Generator (Model: {model_name}, URL: {ollama_url})")
        self.output_dir = output_dir
        self.gpu_monitor = gpu_monitor
        self.max_retries = max_retries
        
        # Initialize Ollama client
        self.ollama_client = OllamaClient(
            ollama_url=ollama_url,
            model_name=model_name
        )
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Template for the structured JSON
        self.json_template = {
            "Name": None,
            "Email": None,
            "Phone": None,
            "Current_Position": None,
            "Skills": [],
            "Experience": []  # List of dicts with company, title, years
        }
    
    def _build_prompt(self, resume_text: str) -> str:
        """
        Build prompt for Mistral to generate JSON
        
        Args:
            resume_text: Extracted text from resume
            
        Returns:
            Formatted prompt for Mistral
        """
        prompt = f"""
You are a specialized model focusing on structured resume data extraction.
Extract information from the resume text below and organize it into a JSON format.
Focus only on factual information present in the text and avoid hallucination.

For missing fields where information cannot be clearly determined, use null.
Note that missing skills or experiences should be empty lists, not null.

Resume Text:
{resume_text}

The output must be in valid JSON format with the following structure:
{{
  "Name": string or null,
  "Email": string or null,
  "Phone": string or null,
  "Current_Position": string or null,
  "Skills": [list of skills as strings],
  "Experience": [
    {{
      "company": string,
      "title": string,
      "years": string
    }}
  ]
}}

Only return the JSON and nothing else.
"""
        return prompt
    
    def generate_json(self, resume_text: str, temperature: float = 0.1, max_tokens: int = 2048) -> Tuple[Dict[str, Any], float]:
        """
        Generate structured JSON from resume text
        
        Args:
            resume_text: Extracted text from resume
            temperature: Temperature for generation (lower = more deterministic)
            max_tokens: Maximum tokens to generate
            
        Returns:
            Tuple of (JSON dict, generation time in seconds)
        """
        logger.info("Generating JSON from resume text")
        start_time = time.time()
        
        if self.gpu_monitor:
            self.gpu_monitor.start_monitoring("json_generation")
        
        prompt = self._build_prompt(resume_text)
        
        try:
            # Generate JSON using the Ollama client
            json_data, generation_time = self.ollama_client.generate_json(
                prompt=prompt,
                template=self.json_template,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # Validate the structure
            if not self._validate_json_structure(json_data):
                logger.warning("Generated JSON has incorrect structure, using template")
                json_data = self.json_template.copy()
                
        except Exception as e:
            logger.error(f"Error generating JSON: {str(e)}")
            json_data = self.json_template.copy()
        
        if self.gpu_monitor:
            self.gpu_monitor.stop_monitoring("json_generation")
        
        elapsed = time.time() - start_time
        logger.info(f"JSON generation completed in {elapsed:.2f}s")
        
        return json_data, elapsed
        
    def _validate_json_structure(self, json_data: Dict[str, Any]) -> bool:
        """
        Validate the structure of the generated JSON
        
        Args:
            json_data: JSON data to validate
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ["Name", "Email", "Phone", "Current_Position", "Skills", "Experience"]
        
        # Check if all required fields are present
        for field in required_fields:
            if field not in json_data:
                logger.warning(f"Missing required field: {field}")
                return False
        
        # Check if Skills is a list
        if not isinstance(json_data.get("Skills", []), list):
            logger.warning("Skills field is not a list")
            return False
        
        # Check if Experience is a list
        if not isinstance(json_data.get("Experience", []), list):
            logger.warning("Experience field is not a list")
            return False
        
        # Check Experience item structure
        for exp in json_data.get("Experience", []):
            if not isinstance(exp, dict):
                logger.warning("Experience item is not a dictionary")
                return False
            
            if not all(k in exp for k in ["company", "title", "years"]):
                logger.warning("Experience item is missing required fields")
                return False
        
        return True
    
    def save_json(self, json_data: Dict[str, Any], file_id: str) -> str:
        """
        Save generated JSON to file
        
        Args:
            json_data: JSON data to save
            file_id: Identifier for the file
            
        Returns:
            Path to saved JSON file
        """
        output_path = os.path.join(self.output_dir, f"{file_id}_structured.json")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved structured JSON to {output_path}")
        return output_path
    
    def process_ocr_result(self, ocr_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process OCR result to generate structured JSON
        
        Args:
            ocr_result: Result from OCR extraction
            
        Returns:
            Dictionary with processing results
        """
        file_id = ocr_result.get("file_id", "unknown")
        logger.info(f"Processing OCR result for resume: {file_id}")
        
        resume_text = ocr_result.get("combined_text", "")
        json_data, generation_time = self.generate_json(resume_text)
        
        # Save the JSON
        json_path = self.save_json(json_data, file_id)
        
        result = {
            "file_id": file_id,
            "json_data": json_data,
            "json_path": json_path,
            "generation_time": generation_time
        }
        
        # Update monitoring with JSON results
        try:
            from monitor.integration import get_monitoring
            monitoring = get_monitoring()
            if monitoring:
                monitoring.update_json_results(file_id, json_data)
        except ImportError:
            pass
        
        return result

if __name__ == "__main__":
    # Test the JSON generator
    import json
    with open("data/output/ocr_results/sample_resume_ocr.json", 'r') as f:
        ocr_result = json.load(f)
    
    generator = JSONGenerator()
    result = generator.process_ocr_result(ocr_result)
    print(f"Generated JSON with {len(result['json_data'].get('Skills', []))} skills")