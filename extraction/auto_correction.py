"""
Auto-correction module for SkillLab
Verifies and auto-corrects JSONs generated from resume OCR
"""

import os
import time
import json
import re
from typing import Dict, List, Any, Tuple, Set, Optional

from utils.logger import setup_logger
from utils.gpu_monitor import GPUMonitor
from extraction.json_generator import JSONGenerator

logger = setup_logger("auto_correction")

class JSONAutoCorrector:
    """Verifies and auto-corrects JSONs generated from resume OCR"""
    
    def __init__(
        self, 
        json_generator: JSONGenerator,
        output_dir: str = "data/output/validated_json",
        min_coverage_threshold: float = 0.9,
        max_correction_attempts: int = 3,
        gpu_monitor: Optional[GPUMonitor] = None
    ):
        """
        Initialize JSON Auto-corrector
        
        Args:
            json_generator: JSONGenerator instance for corrections
            output_dir: Directory to save validated JSONs
            min_coverage_threshold: Minimum text coverage threshold (0.0-1.0)
            max_correction_attempts: Maximum number of correction attempts
            gpu_monitor: Optional GPU monitor for tracking GPU usage
        """
        logger.info(f"Initializing JSON Auto-corrector (Coverage threshold: {min_coverage_threshold})")
        self.json_generator = json_generator
        self.output_dir = output_dir
        self.min_coverage_threshold = min_coverage_threshold
        self.max_correction_attempts = max_correction_attempts
        self.gpu_monitor = gpu_monitor
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
    
    def _extract_significant_words(self, text: str) -> Set[str]:
        """
        Extract significant words from text for comparison
        
        Args:
            text: Text to extract words from
            
        Returns:
            Set of significant words
        """
        # Convert to lowercase and remove special characters
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        
        # Split into words, filter out short words and numbers
        words = [w for w in text.split() if len(w) > 2 and not w.isdigit()]
        
        return set(words)
    
    def _calculate_coverage(self, json_data: Dict[str, Any], resume_text: str) -> float:
        """
        Calculate the coverage of resume text represented in the JSON
        
        Args:
            json_data: Generated JSON data
            resume_text: Original resume text
            
        Returns:
            Coverage ratio (0.0-1.0)
        """
        # Extract significant words from resume text
        resume_words = self._extract_significant_words(resume_text)
        if not resume_words:
            return 0.0
        
        # Flatten JSON into text
        json_text = json.dumps(json_data)
        json_words = self._extract_significant_words(json_text)
        
        # Calculate intersection
        common_words = resume_words.intersection(json_words)
        
        # Calculate coverage ratio
        coverage = len(common_words) / len(resume_words)
        
        logger.info(f"JSON coverage: {coverage:.2f} ({len(common_words)}/{len(resume_words)} words)")
        return coverage
    
    def _build_correction_prompt(self, resume_text: str, json_data: Dict[str, Any], issues: List[str]) -> str:
        """
        Build prompt for correction
        
        Args:
            resume_text: Original resume text
            json_data: Current JSON data
            issues: List of identified issues
            
        Returns:
            Correction prompt
        """
        # Format current JSON for the prompt
        current_json = json.dumps(json_data, indent=2)
        
        prompt = f"""
You are a specialized model focusing on resume data correction.
The following JSON was extracted from a resume, but has some issues:

{current_json}

Issues identified:
- {"\n- ".join(issues)}

Original resume text:
{resume_text}

Please provide a corrected version of the JSON with these guidelines:
1. Focus only on factual information present in the text
2. Do NOT hallucinate data - use null for missing fields (except Skills and Experience which should be empty lists if missing)
3. Extract as many relevant skills as possible from the text
4. Ensure Experience entries have company, title, and years fields
5. Fix any formatting or structural issues

The output must be in valid JSON format with this structure:
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

Only return the corrected JSON and nothing else.
"""
        return prompt
    
    def check_and_correct_json(
        self, 
        json_data: Dict[str, Any], 
        resume_text: str
    ) -> Tuple[Dict[str, Any], bool, int, float]:
        """
        Check and correct JSON if needed
        
        Args:
            json_data: JSON data to check
            resume_text: Original resume text
            
        Returns:
            Tuple of (corrected JSON, is valid, correction attempts, final coverage)
        """
        logger.info("Checking and correcting JSON")
        start_time = time.time()
        
        current_json = json_data
        is_valid = False
        attempts = 0
        coverage = 0.0
        
        while attempts < self.max_correction_attempts and not is_valid:
            # Calculate coverage
            coverage = self._calculate_coverage(current_json, resume_text)
            
            # Check if coverage meets threshold
            if coverage >= self.min_coverage_threshold:
                is_valid = True
                break
            
            # Identify issues
            issues = [f"Low text coverage ({coverage:.2f} < {self.min_coverage_threshold})"]
            
            # Check for empty required fields
            if not current_json.get("Name"):
                issues.append("Missing Name field")
            if not current_json.get("Email") and "@" in resume_text:
                issues.append("Missing Email field")
            if not current_json.get("Phone") and re.search(r'\d{3}[-.\s]?\d{3}[-.\s]?\d{4}', resume_text):
                issues.append("Missing Phone field")
            if len(current_json.get("Skills", [])) < 3 and len(resume_text) > 500:
                issues.append("Few or no Skills extracted")
            if len(current_json.get("Experience", [])) == 0 and len(resume_text) > 500:
                issues.append("No Experience entries extracted")
            
            # If no specific issues found, add general guidance
            if len(issues) == 1:
                issues.append("Extract more information from the resume text")
            
            logger.info(f"Correction attempt {attempts+1}/{self.max_correction_attempts}: {len(issues)} issues found")
            
            # Generate correction prompt
            correction_prompt = self._build_correction_prompt(resume_text, current_json, issues)
            
            # Get corrected JSON
            corrected_json, _ = self.json_generator.generate_json(correction_prompt)
            current_json = corrected_json
            attempts += 1
        
        elapsed = time.time() - start_time
        logger.info(f"JSON correction completed in {elapsed:.2f}s after {attempts} attempts (valid: {is_valid})")
        
        return current_json, is_valid, attempts, coverage
    
    def validate_json_structure(self, json_data: Dict[str, Any]) -> bool:
        """
        Validate JSON structure
        
        Args:
            json_data: JSON data to validate
            
        Returns:
            True if structure is valid, False otherwise
        """
        # Check required fields existence
        required_fields = ["Name", "Email", "Phone", "Current_Position", "Skills", "Experience"]
        for field in required_fields:
            if field not in json_data:
                logger.error(f"Missing required field in JSON: {field}")
                return False
        
        # Validate types
        if not isinstance(json_data.get("Skills", []), list):
            logger.error("Skills field is not a list")
            return False
        
        if not isinstance(json_data.get("Experience", []), list):
            logger.error("Experience field is not a list")
            return False
        
        # Validate Experience entries
        for i, exp in enumerate(json_data.get("Experience", [])):
            if not isinstance(exp, dict):
                logger.error(f"Experience entry {i} is not a dictionary")
                return False
            
            for field in ["company", "title", "years"]:
                if field not in exp:
                    logger.error(f"Missing field '{field}' in Experience entry {i}")
                    return False
        
        return True
    
    def process_resume(self, ocr_result: Dict[str, Any], json_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a resume to validate and correct JSON
        
        Args:
            ocr_result: OCR extraction result
            json_result: Initial JSON generation result
            
        Returns:
            Dictionary with processing results
        """
        file_id = ocr_result.get("file_id", "unknown")
        logger.info(f"Processing resume for validation: {file_id}")
        
        resume_text = ocr_result.get("combined_text", "")
        initial_json = json_result.get("json_data", {})
        
        # Validate and correct JSON
        corrected_json, is_valid, attempts, coverage = self.check_and_correct_json(
            initial_json, resume_text
        )
        
        # Validate structure
        is_structure_valid = self.validate_json_structure(corrected_json)
        
        # Only consider valid if both coverage and structure are valid
        is_valid = is_valid and is_structure_valid
        
        # Save the validated JSON
        output_path = os.path.join(self.output_dir, f"{file_id}_validated.json")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump({
                "resume_id": file_id,
                "json_data": corrected_json,
                "validation": {
                    "is_valid": is_valid,
                    "coverage": coverage,
                    "correction_attempts": attempts,
                    "structure_valid": is_structure_valid
                },
                "image_paths": ocr_result.get("image_paths", [])
            }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved validated JSON to {output_path} (valid: {is_valid})")
        
        result = {
            "file_id": file_id,
            "json_data": corrected_json,
            "is_valid": is_valid,
            "coverage": coverage,
            "correction_attempts": attempts,
            "output_path": output_path
        }
        
        # Update monitoring with correction results
        try:
            from monitor.integration import get_monitoring
            monitoring = get_monitoring()
            if monitoring:
                monitoring.update_correction_results(file_id, result)
        except ImportError:
            pass
        
        return result

if __name__ == "__main__":
    # Test the auto-corrector
    import json
    from extraction.json_generator import JSONGenerator
    
    with open("data/output/ocr_results/sample_resume_ocr.json", 'r') as f:
        ocr_result = json.load(f)
    
    with open("data/output/json_results/sample_resume_structured.json", 'r') as f:
        json_data = json.load(f)
    
    json_result = {"json_data": json_data}
    
    generator = JSONGenerator()
    corrector = JSONAutoCorrector(generator)
    result = corrector.process_resume(ocr_result, json_result)
    
    print(f"Corrected JSON valid: {result['is_valid']}, coverage: {result['coverage']:.2f}")