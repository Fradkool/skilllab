"""
Ollama Client
Client for interacting with the containerized Ollama service
"""

import os
import json
import time
import requests
from typing import Dict, List, Any, Optional, Tuple
import backoff

from utils.logger import setup_logger

logger = setup_logger("ollama_client")

class OllamaClient:
    """Client for interacting with the containerized Ollama service"""
    
    def __init__(
        self, 
        ollama_url: str = "http://localhost:11434/api/generate",
        model_name: str = "mistral:7b-instruct-v0.2-q8_0"
    ):
        """
        Initialize Ollama client
        
        Args:
            ollama_url: URL for Ollama API
            model_name: Model to use for generation
        """
        logger.info(f"Initializing Ollama Client (Service URL: {ollama_url}, Model: {model_name})")
        self.ollama_url = ollama_url
        self.model_name = model_name
    
    def check_health(self) -> bool:
        """
        Check if the Ollama service is healthy
        
        Returns:
            True if the service is healthy, False otherwise
        """
        try:
            # Get the base URL by removing the API endpoint
            base_url = self.ollama_url.rsplit('/', 2)[0]
            tags_url = f"{base_url}/api/tags"
            
            response = requests.get(tags_url, timeout=5)
            if response.status_code == 200:
                # Check if the required model is available
                tags = response.json().get("models", [])
                if any(self.model_name in tag.get("name", "") for tag in tags):
                    logger.info(f"Ollama service is healthy and model '{self.model_name}' is available")
                    return True
                else:
                    logger.warning(f"Ollama service is healthy but model '{self.model_name}' is not available")
                    return False
            else:
                logger.warning(f"Ollama service health check failed: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Ollama service health check failed: {str(e)}")
            return False
    
    def list_available_models(self) -> List[Dict[str, Any]]:
        """
        List available models in the Ollama service
        
        Returns:
            List of available models with metadata
        """
        try:
            # Get the base URL by removing the API endpoint
            base_url = self.ollama_url.rsplit('/', 2)[0]
            tags_url = f"{base_url}/api/tags"
            
            response = requests.get(tags_url, timeout=5)
            if response.status_code == 200:
                return response.json().get("models", [])
            else:
                logger.warning(f"Failed to list Ollama models: {response.text}")
                return []
        except Exception as e:
            logger.error(f"Error listing Ollama models: {str(e)}")
            return []
    
    @backoff.on_exception(
        backoff.expo,
        (requests.exceptions.RequestException, json.JSONDecodeError, KeyError),
        max_tries=5,
        max_time=60,
        on_backoff=lambda details: logger.warning(
            f"Retrying Ollama API call: attempt {details['tries']} after {details['wait']:.1f}s"
        )
    )
    def generate_text(
        self,
        prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 2048,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Generate text using the Ollama model
        
        Args:
            prompt: Prompt for generation
            temperature: Temperature for generation (lower = more deterministic)
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response
            
        Returns:
            Dictionary with generation results
        """
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream
        }
        
        start_time = time.time()
        logger.info(f"Generating text with {self.model_name} (Temperature: {temperature})")
        
        response = requests.post(
            self.ollama_url,
            json=payload,
            timeout=300  # 5 minutes timeout for large prompts
        )
        
        elapsed = time.time() - start_time
        logger.info(f"Generation completed in {elapsed:.2f}s")
        
        # Check for errors
        if response.status_code != 200:
            error_msg = f"Ollama API error: {response.status_code} - {response.text}"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        return response.json()
    
    def extract_json_from_text(self, text: str) -> Dict[str, Any]:
        """
        Extract JSON from the generated text
        
        Args:
            text: Generated text that should contain JSON
            
        Returns:
            Extracted JSON data
        """
        try:
            # Find JSON boundaries if not clean JSON
            json_start = text.find('{')
            json_end = text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = text[json_start:json_end]
                return json.loads(json_str)
            else:
                logger.error("No valid JSON found in response")
                return {}
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from response: {str(e)}")
            logger.debug(f"Raw response: {text}")
            return {}
    
    def generate_json(
        self,
        prompt: str,
        template: Dict[str, Any],
        temperature: float = 0.1,
        max_tokens: int = 2048
    ) -> Tuple[Dict[str, Any], float]:
        """
        Generate structured JSON using the Ollama model
        
        Args:
            prompt: Prompt for generation
            template: Template for JSON structure (used if generation fails)
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            
        Returns:
            Tuple of (JSON data, generation time in seconds)
        """
        start_time = time.time()
        
        try:
            # First, check if the service is healthy
            if not hasattr(self, '_service_checked') or not self._service_checked:
                healthy = self.check_health()
                if not healthy:
                    logger.warning("Ollama service is not responding or model is not available. Will retry once.")
                    # Wait 2 seconds and retry
                    time.sleep(2)
                    healthy = self.check_health()
                    if not healthy:
                        raise Exception("Ollama service is not available. Please ensure the Docker container is running and the model is installed.")
                self._service_checked = True
            
            # Generate text
            result = self.generate_text(prompt, temperature, max_tokens)
            response_text = result.get("response", "")
            
            # Extract JSON from the response text
            json_data = self.extract_json_from_text(response_text)
            
            # Check if JSON data was successfully extracted
            if not json_data:
                logger.warning("Failed to extract valid JSON, using template")
                json_data = template.copy()
                
        except Exception as e:
            logger.error(f"Error generating JSON: {str(e)}")
            json_data = template.copy()
        
        elapsed = time.time() - start_time
        return json_data, elapsed