"""
Health check API for SkillLab
Provides endpoints to check the health of the application and its dependencies
"""

import os
import time
import platform
import sys
import json
import logging
import requests
from typing import Dict, List, Any, Optional

from config import get_config
from extraction.ocr_service_client import OCRServiceClient
from extraction.ollama_client import OllamaClient
from database import get_metrics_repository, get_review_repository

logger = logging.getLogger(__name__)

class HealthCheckAPI:
    """API for checking the health of SkillLab and its dependencies"""
    
    def __init__(self):
        """Initialize the health check API"""
        self.config = get_config()
    
    def get_system_info(self) -> Dict[str, Any]:
        """
        Get system information
        
        Returns:
            Dictionary with system information
        """
        return {
            "platform": platform.platform(),
            "python_version": sys.version,
            "processor": platform.processor(),
            "cpu_count": os.cpu_count(),
            "memory": self._get_memory_info()
        }
    
    def _get_memory_info(self) -> Dict[str, Any]:
        """
        Get memory information if available
        
        Returns:
            Dictionary with memory information
        """
        try:
            import psutil
            mem = psutil.virtual_memory()
            return {
                "total": self._format_bytes(mem.total),
                "available": self._format_bytes(mem.available),
                "percent_used": mem.percent
            }
        except ImportError:
            return {"status": "psutil not installed, memory info unavailable"}
    
    def _format_bytes(self, bytes_value: int) -> str:
        """
        Format bytes as human-readable string
        
        Args:
            bytes_value: Bytes value
            
        Returns:
            Human-readable string
        """
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.2f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.2f} PB"
    
    def check_gpu_availability(self) -> Dict[str, Any]:
        """
        Check GPU availability
        
        Returns:
            Dictionary with GPU information
        """
        try:
            import torch
            gpu_available = torch.cuda.is_available()
            gpu_info = {
                "available": gpu_available,
                "count": torch.cuda.device_count() if gpu_available else 0
            }
            
            if gpu_available:
                gpus = []
                for i in range(torch.cuda.device_count()):
                    gpus.append({
                        "index": i,
                        "name": torch.cuda.get_device_name(i),
                        "memory_total": torch.cuda.get_device_properties(i).total_memory
                    })
                gpu_info["devices"] = gpus
                
            return gpu_info
        except ImportError:
            return {"status": "torch not installed, GPU info unavailable"}
        except Exception as e:
            return {"error": str(e)}
    
    def check_database_health(self) -> Dict[str, Any]:
        """
        Check database health
        
        Returns:
            Dictionary with database health status
        """
        result = {
            "metrics_db": {"status": "unknown"},
            "review_db": {"status": "unknown"}
        }
        
        # Check metrics repository
        start_time = time.time()
        try:
            metrics_repo = get_metrics_repository()
            if metrics_repo:
                # Try to get some data
                stats = metrics_repo.get_dashboard_stats()
                result["metrics_db"] = {
                    "status": "ok",
                    "response_time": f"{(time.time() - start_time) * 1000:.2f}ms",
                    "path": self.config.monitoring.metrics_db
                }
        except Exception as e:
            result["metrics_db"] = {
                "status": "error",
                "error": str(e),
                "path": self.config.monitoring.metrics_db
            }
        
        # Check review repository
        start_time = time.time()
        try:
            review_repo = get_review_repository()
            if review_repo:
                # Try to get some data
                count = review_repo.get_document_count()
                result["review_db"] = {
                    "status": "ok",
                    "response_time": f"{(time.time() - start_time) * 1000:.2f}ms",
                    "document_count": count,
                    "path": self.config.review.db_path
                }
        except Exception as e:
            result["review_db"] = {
                "status": "error",
                "error": str(e),
                "path": self.config.review.db_path
            }
        
        return result
    
    def check_ocr_service_health(self) -> Dict[str, Any]:
        """
        Check OCR service health
        
        Returns:
            Dictionary with OCR service health status
        """
        if not self.config.ocr.use_service:
            return {"status": "disabled", "message": "OCR service is not enabled in configuration"}
        
        try:
            start_time = time.time()
            client = OCRServiceClient(self.config.ocr.service_url)
            healthy = client.check_health()
            
            return {
                "status": "ok" if healthy else "error",
                "url": self.config.ocr.service_url,
                "response_time": f"{(time.time() - start_time) * 1000:.2f}ms",
                "message": "Service is healthy" if healthy else "Service is not responding"
            }
        except Exception as e:
            return {
                "status": "error",
                "url": self.config.ocr.service_url,
                "error": str(e)
            }
    
    def check_ollama_service_health(self) -> Dict[str, Any]:
        """
        Check Ollama service health
        
        Returns:
            Dictionary with Ollama service health status
        """
        try:
            start_time = time.time()
            client = OllamaClient(
                ollama_url=self.config.json_generation.ollama_url,
                model_name=self.config.json_generation.model_name
            )
            healthy = client.check_health()
            
            result = {
                "status": "ok" if healthy else "error",
                "url": self.config.json_generation.ollama_url,
                "model": self.config.json_generation.model_name,
                "response_time": f"{(time.time() - start_time) * 1000:.2f}ms",
                "message": "Service is healthy and model is available" if healthy else "Service is not responding or model is unavailable"
            }
            
            # Get available models if service is healthy
            if healthy:
                models = client.list_available_models()
                result["available_models"] = [model.get("name") for model in models]
            
            return result
        except Exception as e:
            return {
                "status": "error",
                "url": self.config.json_generation.ollama_url,
                "error": str(e)
            }
    
    def check_file_system(self) -> Dict[str, Any]:
        """
        Check file system status
        
        Returns:
            Dictionary with file system status
        """
        result = {}
        
        # Check input directory
        input_dir = self.config.paths.input_dir
        result["input_dir"] = {
            "path": input_dir,
            "exists": os.path.exists(input_dir),
            "is_dir": os.path.isdir(input_dir) if os.path.exists(input_dir) else False
        }
        
        # Check output directory
        output_dir = self.config.paths.output_dir
        result["output_dir"] = {
            "path": output_dir,
            "exists": os.path.exists(output_dir),
            "is_dir": os.path.isdir(output_dir) if os.path.exists(output_dir) else False
        }
        
        # Check model directory
        model_dir = self.config.paths.model_dir
        result["model_dir"] = {
            "path": model_dir,
            "exists": os.path.exists(model_dir),
            "is_dir": os.path.isdir(model_dir) if os.path.exists(model_dir) else False
        }
        
        # Check disk space
        try:
            import shutil
            for dir_name, dir_info in result.items():
                path = dir_info["path"]
                if os.path.exists(path):
                    total, used, free = shutil.disk_usage(path)
                    result[dir_name]["disk"] = {
                        "total": self._format_bytes(total),
                        "used": self._format_bytes(used),
                        "free": self._format_bytes(free),
                        "percent_used": used / total * 100
                    }
        except ImportError:
            result["disk_info"] = "shutil not available, disk information unavailable"
        
        return result
    
    def get_full_health_report(self) -> Dict[str, Any]:
        """
        Get full health report
        
        Returns:
            Dictionary with complete health report
        """
        start_time = time.time()
        
        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "system": self.get_system_info(),
            "gpu": self.check_gpu_availability(),
            "database": self.check_database_health(),
            "file_system": self.check_file_system(),
            "services": {
                "ocr": self.check_ocr_service_health(),
                "ollama": self.check_ollama_service_health()
            }
        }
        
        # Calculate overall status
        status = "ok"
        issues = []
        
        # Check database status
        for db_name, db_info in report["database"].items():
            if db_info.get("status") != "ok":
                status = "warning"
                issues.append(f"{db_name} issue: {db_info.get('error', 'unknown error')}")
        
        # Check services status
        for service_name, service_info in report["services"].items():
            if service_info.get("status") == "error":
                status = "warning"
                issues.append(f"{service_name} service issue: {service_info.get('error', service_info.get('message', 'unknown error'))}")
        
        # Check file system
        for dir_name, dir_info in report["file_system"].items():
            if not dir_info.get("exists", False):
                status = "warning"
                issues.append(f"{dir_name} does not exist: {dir_info.get('path')}")
        
        report["status"] = status
        report["issues"] = issues
        report["response_time"] = f"{(time.time() - start_time) * 1000:.2f}ms"
        
        return report


# Global API instance
_health_api_instance = None

def get_health_api() -> HealthCheckAPI:
    """
    Get global health check API instance
    
    Returns:
        Health check API
    """
    global _health_api_instance
    
    if _health_api_instance is None:
        _health_api_instance = HealthCheckAPI()
    
    return _health_api_instance