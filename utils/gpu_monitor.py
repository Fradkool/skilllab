"""
GPU Monitor module for SkillLab
Monitors GPU usage during training and inference
"""

import time
import threading
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
import os

from utils.logger import setup_logger

# Try to import GPU monitoring libraries
try:
    import torch
    import pynvml
    HAS_GPU_LIBRARIES = True
except ImportError:
    HAS_GPU_LIBRARIES = False

logger = setup_logger("gpu_monitor")

class GPUMonitor:
    """Monitors GPU memory and utilization during training and inference"""
    
    def __init__(self, log_dir: str = "logs", interval: float = 2.0):
        """
        Initialize GPU Monitor
        
        Args:
            log_dir: Directory to save GPU logs
            interval: Monitoring interval in seconds
        """
        self.log_dir = log_dir
        self.interval = interval
        self.monitoring = False
        self.monitor_thread = None
        self.current_activity = "idle"
        self.stats = {}
        self.has_gpu = False
        
        # Create log directory if it doesn't exist
        os.makedirs(log_dir, exist_ok=True)
        
        # Initialize NVML if available
        if HAS_GPU_LIBRARIES and torch.cuda.is_available():
            try:
                pynvml.nvmlInit()
                self.has_gpu = True
                self.device_count = pynvml.nvmlDeviceGetCount()
                logger.info(f"GPU monitoring initialized for {self.device_count} device(s)")
                
                # Get device info
                self.device_info = {}
                for i in range(self.device_count):
                    handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                    name = pynvml.nvmlDeviceGetName(handle)
                    self.device_info[i] = {
                        "name": name.decode("utf-8") if isinstance(name, bytes) else name,
                        "handle": handle
                    }
            except Exception as e:
                logger.error(f"Error getting GPU {i} stats: {str(e)}")
                stats[i] = {
                    "timestamp": datetime.now().isoformat(),
                    "activity": self.current_activity,
                    "error": str(e)
                }
                logger.info(f"GPU {i}: {self.device_info[i]['name']}")
            except Exception as e:
                logger.error(f"Failed to initialize GPU monitoring: {str(e)}")
                self.has_gpu = False
        else:
            logger.warning("GPU monitoring libraries not available or GPU not detected")
    
    def _get_gpu_stats(self) -> Dict[int, Dict[str, Any]]:
        """
        Get GPU statistics
        
        Returns:
            Dictionary with GPU statistics
        """
        stats = {}
        
        if not self.has_gpu:
            return stats
    
    def _monitor_loop(self) -> None:
        """Monitoring loop for GPU usage"""
        logger.info(f"Starting GPU monitoring for activity: {self.current_activity}")
        
        # Create log file for this monitoring session
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(self.log_dir, f"gpu_monitor_{self.current_activity}_{timestamp}.json")
        
        self.stats[self.current_activity] = {
            "start_time": datetime.now().isoformat(),
            "log_file": log_file,
            "samples": []
        }
        
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write("[\n")  # Start JSON array
            
            sample_count = 0
            while self.monitoring:
                try:
                    # Get GPU stats
                    gpu_stats = self._get_gpu_stats()
                    
                    # Append to in-memory statistics
                    self.stats[self.current_activity]["samples"].append(gpu_stats)
                    
                    # Write to log file with proper JSON formatting
                    if sample_count > 0:
                        f.write(",\n")
                    f.write(json.dumps(gpu_stats, indent=2))
                    f.flush()
                    
                    sample_count += 1
                except Exception as e:
                    logger.error(f"Error in GPU monitoring loop: {str(e)}")
                
                # Wait for next sample
                time.sleep(self.interval)
            
            # End JSON array
            f.write("\n]")
        
        # Update end time
        self.stats[self.current_activity]["end_time"] = datetime.now().isoformat()
        self.stats[self.current_activity]["sample_count"] = sample_count
        
        logger.info(f"GPU monitoring stopped for {self.current_activity} after {sample_count} samples")
    
    def start_monitoring(self, activity: str) -> bool:
        """
        Start GPU monitoring for a specific activity
        
        Args:
            activity: Activity name for logging
            
        Returns:
            True if monitoring started, False otherwise
        """
        if not self.has_gpu:
            logger.warning(f"Cannot start GPU monitoring for {activity}: No GPU available")
            return False
        
        if self.monitoring:
            logger.warning(f"GPU monitoring already active for {self.current_activity}")
            return False
        
        # Set activity and start monitoring
        self.current_activity = activity
        self.monitoring = True
        
        # Start monitoring thread
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        return True
    
    def stop_monitoring(self, activity: Optional[str] = None) -> bool:
        """
        Stop GPU monitoring
        
        Args:
            activity: Optional activity name to verify (if None, stop regardless of activity)
            
        Returns:
            True if monitoring stopped, False otherwise
        """
        if not self.monitoring:
            logger.warning("GPU monitoring not active")
            return False
        
        if activity is not None and activity != self.current_activity:
            logger.warning(f"Current activity ({self.current_activity}) doesn't match requested activity ({activity})")
            return False
        
        # Stop monitoring
        self.monitoring = False
        
        # Wait for monitoring thread to complete
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=self.interval * 2)
        
        return True
    
    def get_summary(self, activity: Optional[str] = None) -> Dict[str, Any]:
        """
        Get summary of GPU usage for a specific activity or all activities
        
        Args:
            activity: Optional activity name (if None, return all activities)
            
        Returns:
            Dictionary with GPU usage summary
        """
        if activity is not None:
            if activity not in self.stats:
                return {"error": f"No data for activity: {activity}"}
            return self._generate_summary(activity)
        
        # Generate summary for all activities
        summary = {}
        for act in self.stats.keys():
            summary[act] = self._generate_summary(act)
        
        return summary
    
    def _generate_summary(self, activity: str) -> Dict[str, Any]:
        """
        Generate summary statistics for a specific activity
        
        Args:
            activity: Activity name
            
        Returns:
            Dictionary with summary statistics
        """
        if activity not in self.stats or not self.stats[activity].get("samples"):
            return {"error": "No data available"}
        
        samples = self.stats[activity]["samples"]
        
        # Initialize summary
        summary = {
            "activity": activity,
            "start_time": self.stats[activity]["start_time"],
            "end_time": self.stats[activity].get("end_time", datetime.now().isoformat()),
            "sample_count": len(samples),
            "devices": {}
        }
        
        # Process samples for each device
        for device_idx in range(self.device_count):
            device_samples = []
            
            for sample in samples:
                if device_idx in sample:
                    device_samples.append(sample[device_idx])
            
            if not device_samples:
                continue
            
            # Calculate statistics
            memory_used = [s["memory"]["used_mb"] for s in device_samples if "memory" in s]
            memory_percent = [s["memory"]["used_percent"] for s in device_samples if "memory" in s]
            gpu_util = [s["utilization"]["gpu_percent"] for s in device_samples if "utilization" in s]
            temperatures = [s["temperature_c"] for s in device_samples if "temperature_c" in s]
            
            # Add to summary
            summary["devices"][device_idx] = {
                "name": self.device_info[device_idx]["name"],
                "memory": {
                    "peak_mb": max(memory_used) if memory_used else 0,
                    "average_mb": sum(memory_used) / len(memory_used) if memory_used else 0,
                    "peak_percent": max(memory_percent) if memory_percent else 0,
                    "average_percent": sum(memory_percent) / len(memory_percent) if memory_percent else 0
                },
                "utilization": {
                    "peak_percent": max(gpu_util) if gpu_util else 0,
                    "average_percent": sum(gpu_util) / len(gpu_util) if gpu_util else 0
                },
                "temperature": {
                    "peak_c": max(temperatures) if temperatures else 0,
                    "average_c": sum(temperatures) / len(temperatures) if temperatures else 0
                }
            }
        
        return summary
    
    def __del__(self):
        """Cleanup when the monitor is deleted"""
        if self.monitoring:
            self.stop_monitoring()
        
        if self.has_gpu:
            try:
                pynvml.nvmlShutdown()
                logger.info("GPU monitoring shutdown complete")
            except Exception as e:
                logger.error(f"Error shutting down GPU monitoring: {str(e)}")

if __name__ == "__main__":
    # Test the GPU monitor
    monitor = GPUMonitor()
    
    if monitor.has_gpu:
        print("Starting GPU monitoring test")
        monitor.start_monitoring("test")
        
        # Simulate some GPU activity
        if torch.cuda.is_available():
            # Create some tensors to use GPU memory
            tensors = [torch.ones(1000, 1000).cuda() for _ in range(5)]
            
            # Do some operations
            for _ in range(10):
                result = torch.matmul(tensors[0], tensors[1])
                time.sleep(0.5)
            
            # Clean up
            del tensors
            torch.cuda.empty_cache()
        
        # Stop monitoring
        time.sleep(5)
        monitor.stop_monitoring("test")
        
        # Print summary
        summary = monitor.get_summary("test")
        print(json.dumps(summary, indent=2))
    else:
        print("No GPU available for monitoring")
        
        for i in range(self.device_count):
            try:
                handle = self.device_info[i]["handle"]
                
                # Get memory info
                mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                total_mem = mem_info.total / (1024 ** 2)  # Convert to MB
                used_mem = mem_info.used / (1024 ** 2)
                free_mem = mem_info.free / (1024 ** 2)
                
                # Get utilization
                util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                gpu_util = util.gpu
                mem_util = util.memory
                
                # Get temperature
                temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                
                # Get power usage
                try:
                    power = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0  # Convert to W
                except pynvml.NVMLError:
                    power = 0
                
                stats[i] = {
                    "timestamp": datetime.now().isoformat(),
                    "activity": self.current_activity,
                    "memory": {
                        "total_mb": round(total_mem, 2),
                        "used_mb": round(used_mem, 2),
                        "free_mb": round(free_mem, 2),
                        "used_percent": round(used_mem / total_mem * 100, 2)
                    },
                    "utilization": {
                        "gpu_percent": gpu_util,
                        "memory_percent": mem_util
                    },
                    "temperature_c": temp,
                    "power_watts": round(power, 2)
                }
            except Exception as e:
                logger.error(f"Error getting GPU {i} stats: {str(e)}")
        
         