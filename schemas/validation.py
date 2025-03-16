"""
Schema validation module for SkillLab
Provides utilities for validating data against JSON schemas
"""

import os
import json
from typing import Dict, List, Any, Union, Optional
import jsonschema
from jsonschema import validate, ValidationError

# Schema directory
SCHEMA_DIR = os.path.dirname(os.path.abspath(__file__))

# Cache for loaded schemas
_schema_cache = {}

def load_schema(schema_name: str) -> Dict[str, Any]:
    """
    Load a JSON schema from file
    
    Args:
        schema_name: Name of the schema file (without .json extension)
        
    Returns:
        Schema as a dictionary
    
    Raises:
        FileNotFoundError: If schema file doesn't exist
        json.JSONDecodeError: If schema file contains invalid JSON
    """
    if schema_name in _schema_cache:
        return _schema_cache[schema_name]
    
    schema_path = os.path.join(SCHEMA_DIR, f"{schema_name}.json")
    
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema = json.load(f)
    
    # Cache the schema
    _schema_cache[schema_name] = schema
    
    return schema

def validate_data(data: Dict[str, Any], schema_name: str) -> Tuple[bool, Optional[str]]:
    """
    Validate data against a schema
    
    Args:
        data: Data to validate
        schema_name: Name of the schema to validate against
        
    Returns:
        Tuple of (is_valid, error_message)
        is_valid: True if data is valid, False otherwise
        error_message: None if valid, error message if invalid
    """
    try:
        schema = load_schema(schema_name)
        validate(instance=data, schema=schema)
        return True, None
    except ValidationError as e:
        # Format error message
        error_path = "/".join(str(p) for p in e.path)
        error_msg = f"Validation error at {error_path}: {e.message}"
        return False, error_msg
    except Exception as e:
        return False, f"Validation error: {str(e)}"

def validate_resume(resume_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate resume data against the resume schema
    
    Args:
        resume_data: Resume data to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    return validate_data(resume_data, "resume")

def validate_metrics(metrics_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate metrics data against the metrics schema
    
    Args:
        metrics_data: Metrics data to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    return validate_data(metrics_data, "metrics")

def get_schema_as_dict(schema_name: str) -> Dict[str, Any]:
    """
    Get schema as a Python dictionary
    
    Args:
        schema_name: Name of the schema
        
    Returns:
        Schema as a dictionary
    """
    return load_schema(schema_name)

def get_field_constraints(schema_name: str, field_path: str) -> Dict[str, Any]:
    """
    Get constraints for a specific field in a schema
    
    Args:
        schema_name: Name of the schema
        field_path: Path to the field, e.g. "properties/Name"
        
    Returns:
        Dictionary with field constraints or empty dict if field not found
    """
    schema = load_schema(schema_name)
    
    # Navigate through the schema to find the field
    path_components = field_path.split('/')
    current = schema
    
    for component in path_components:
        if component in current:
            current = current[component]
        else:
            return {}
    
    return current