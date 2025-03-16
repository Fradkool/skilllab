#!/usr/bin/env python3
"""
Health check utility for SkillLab
Checks the health of the application and its dependencies
"""

import os
import sys
import json
import argparse
import logging
from typing import Dict, List, Any, Optional

from api.health import get_health_api
from utils.logger import setup_logger

logger = setup_logger("healthcheck")

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="SkillLab Health Check Utility")
    
    # Output format
    parser.add_argument("--json", action="store_true",
                        help="Output in JSON format")
    
    # Check specific components
    parser.add_argument("--check-all", action="store_true",
                        help="Check all components (default)")
    parser.add_argument("--check-system", action="store_true",
                        help="Check system information")
    parser.add_argument("--check-gpu", action="store_true",
                        help="Check GPU availability")
    parser.add_argument("--check-database", action="store_true",
                        help="Check database health")
    parser.add_argument("--check-file-system", action="store_true",
                        help="Check file system status")
    parser.add_argument("--check-services", action="store_true",
                        help="Check OCR and Ollama services")
    
    # Output file
    parser.add_argument("--output", type=str, default=None,
                        help="Output file path (default: stdout)")
    
    return parser.parse_args()

def format_status(status: str) -> str:
    """
    Format status string with color
    
    Args:
        status: Status string
        
    Returns:
        Formatted status string
    """
    if status == "ok":
        return "\033[92mOK\033[0m"  # Green
    elif status == "warning":
        return "\033[93mWARNING\033[0m"  # Yellow
    elif status == "error":
        return "\033[91mERROR\033[0m"  # Red
    elif status == "disabled":
        return "\033[90mDISABLED\033[0m"  # Gray
    else:
        return status

def print_system_info(info: Dict[str, Any]):
    """
    Print system information
    
    Args:
        info: System information
    """
    print("System Information:")
    print(f"  Platform: {info['platform']}")
    print(f"  Python: {info['python_version'].split()[0]}")
    print(f"  Processor: {info['processor']}")
    print(f"  CPU Count: {info['cpu_count']}")
    
    if 'memory' in info and isinstance(info['memory'], dict):
        if 'status' in info['memory']:
            print(f"  Memory: {info['memory']['status']}")
        else:
            print(f"  Memory:")
            print(f"    Total: {info['memory'].get('total', 'N/A')}")
            print(f"    Available: {info['memory'].get('available', 'N/A')}")
            print(f"    Used: {info['memory'].get('percent_used', 'N/A')}%")

def print_gpu_info(info: Dict[str, Any]):
    """
    Print GPU information
    
    Args:
        info: GPU information
    """
    print("GPU Information:")
    
    if 'error' in info:
        print(f"  Error: {info['error']}")
        return
        
    if 'status' in info:
        print(f"  Status: {info['status']}")
        return
        
    print(f"  Available: {info['available']}")
    print(f"  Count: {info['count']}")
    
    if info['available'] and 'devices' in info:
        print("  Devices:")
        for device in info['devices']:
            print(f"    [{device['index']}] {device['name']}")
            if 'memory_total' in device:
                memory_gb = device['memory_total'] / (1024 * 1024 * 1024)
                print(f"        Memory: {memory_gb:.2f} GB")

def print_database_info(info: Dict[str, Any]):
    """
    Print database information
    
    Args:
        info: Database information
    """
    print("Database Information:")
    
    # Metrics DB
    metrics_db = info.get('metrics_db', {})
    status = metrics_db.get('status', 'unknown')
    print(f"  Metrics DB: {format_status(status)}")
    print(f"    Path: {metrics_db.get('path', 'N/A')}")
    if 'response_time' in metrics_db:
        print(f"    Response Time: {metrics_db['response_time']}")
    if 'error' in metrics_db:
        print(f"    Error: {metrics_db['error']}")
    
    # Review DB
    review_db = info.get('review_db', {})
    status = review_db.get('status', 'unknown')
    print(f"  Review DB: {format_status(status)}")
    print(f"    Path: {review_db.get('path', 'N/A')}")
    if 'document_count' in review_db:
        print(f"    Documents: {review_db['document_count']}")
    if 'response_time' in review_db:
        print(f"    Response Time: {review_db['response_time']}")
    if 'error' in review_db:
        print(f"    Error: {review_db['error']}")

def print_file_system_info(info: Dict[str, Any]):
    """
    Print file system information
    
    Args:
        info: File system information
    """
    print("File System Information:")
    
    for dir_name, dir_info in info.items():
        if dir_name == 'disk_info':
            print(f"  Disk Info: {dir_info}")
            continue
            
        exists = dir_info.get('exists', False)
        status = "ok" if exists else "error"
        print(f"  {dir_name}: {format_status(status)}")
        print(f"    Path: {dir_info.get('path', 'N/A')}")
        
        if 'disk' in dir_info:
            disk = dir_info['disk']
            print(f"    Disk Space:")
            print(f"      Total: {disk.get('total', 'N/A')}")
            print(f"      Used: {disk.get('used', 'N/A')} ({disk.get('percent_used', 0):.1f}%)")
            print(f"      Free: {disk.get('free', 'N/A')}")

def print_services_info(info: Dict[str, Any]):
    """
    Print services information
    
    Args:
        info: Services information
    """
    print("Services Information:")
    
    # OCR Service
    ocr = info.get('ocr', {})
    status = ocr.get('status', 'unknown')
    print(f"  OCR Service: {format_status(status)}")
    if 'url' in ocr:
        print(f"    URL: {ocr['url']}")
    if 'response_time' in ocr:
        print(f"    Response Time: {ocr['response_time']}")
    if 'message' in ocr:
        print(f"    Message: {ocr['message']}")
    if 'error' in ocr:
        print(f"    Error: {ocr['error']}")
    
    # Ollama Service
    ollama = info.get('ollama', {})
    status = ollama.get('status', 'unknown')
    print(f"  Ollama Service: {format_status(status)}")
    if 'url' in ollama:
        print(f"    URL: {ollama['url']}")
    if 'model' in ollama:
        print(f"    Model: {ollama['model']}")
    if 'response_time' in ollama:
        print(f"    Response Time: {ollama['response_time']}")
    if 'message' in ollama:
        print(f"    Message: {ollama['message']}")
    if 'available_models' in ollama:
        models = ollama['available_models']
        if len(models) > 3:
            print(f"    Available Models: {', '.join(models[:3])} and {len(models) - 3} more")
        else:
            print(f"    Available Models: {', '.join(models)}")
    if 'error' in ollama:
        print(f"    Error: {ollama['error']}")

def main():
    """Main entry point"""
    args = parse_args()
    
    # Get health API
    health_api = get_health_api()
    
    # Determine which components to check
    check_all = args.check_all or not any([
        args.check_system,
        args.check_gpu,
        args.check_database,
        args.check_file_system,
        args.check_services
    ])
    
    # Get full report if checking all components
    if check_all:
        report = health_api.get_full_health_report()
    else:
        # Build custom report
        report = {"timestamp": "", "status": "ok", "issues": []}
        
        if args.check_system:
            report["system"] = health_api.get_system_info()
        
        if args.check_gpu:
            report["gpu"] = health_api.check_gpu_availability()
        
        if args.check_database:
            report["database"] = health_api.check_database_health()
        
        if args.check_file_system:
            report["file_system"] = health_api.check_file_system()
        
        if args.check_services:
            report["services"] = {
                "ocr": health_api.check_ocr_service_health(),
                "ollama": health_api.check_ollama_service_health()
            }
    
    # Output in JSON format if requested
    if args.json:
        output = json.dumps(report, indent=2)
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(output)
        else:
            print(output)
    else:
        # Print human-readable report
        print(f"SkillLab Health Check Report ({report.get('timestamp', '')})")
        print(f"Overall Status: {format_status(report.get('status', 'unknown'))}")
        
        # Print issues if any
        issues = report.get('issues', [])
        if issues:
            print("\nIssues:")
            for issue in issues:
                print(f"  - {issue}")
        print()
        
        # Print component information
        if check_all or args.check_system:
            if "system" in report:
                print_system_info(report["system"])
                print()
        
        if check_all or args.check_gpu:
            if "gpu" in report:
                print_gpu_info(report["gpu"])
                print()
        
        if check_all or args.check_database:
            if "database" in report:
                print_database_info(report["database"])
                print()
        
        if check_all or args.check_file_system:
            if "file_system" in report:
                print_file_system_info(report["file_system"])
                print()
        
        if check_all or args.check_services:
            if "services" in report:
                print_services_info(report["services"])
                print()
        
        # Print response time if available
        if "response_time" in report:
            print(f"Report generated in: {report['response_time']}")
        
        # Write to file if requested
        if args.output:
            with open(args.output, 'w') as f:
                f.write(f"SkillLab Health Check Report ({report.get('timestamp', '')})\n")
                f.write(f"Overall Status: {report.get('status', 'unknown')}\n\n")
                
                # Write issues if any
                issues = report.get('issues', [])
                if issues:
                    f.write("Issues:\n")
                    for issue in issues:
                        f.write(f"  - {issue}\n")
                f.write("\n")
                
                # Write component information (plain text without colors)
                # ... (similar to console output but without formatting)

if __name__ == "__main__":
    main()