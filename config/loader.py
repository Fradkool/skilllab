"""
Configuration loader for SkillLab
Loads configuration from YAML files and environment variables
"""

import os
import yaml
import json
from typing import Dict, Any, Optional, Union
from pathlib import Path
import re

from .schema import AppConfig

# Constants
DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "default.yaml")
ENV_PREFIX = "SKILLLAB_"

class ConfigLoader:
    """Configuration loader class"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration loader
        
        Args:
            config_path: Path to configuration file (None to use default)
        """
        self.config_path = config_path or DEFAULT_CONFIG_PATH
        self.config_data = {}
        self.loaded = False
    
    def load(self) -> AppConfig:
        """
        Load configuration from file and environment variables
        
        Returns:
            Validated configuration object
        """
        if self.loaded:
            return AppConfig(**self.config_data)
        
        # Load default configuration
        default_config = self._load_yaml(DEFAULT_CONFIG_PATH)
        
        # Load user configuration if different from default
        user_config = {}
        if self.config_path != DEFAULT_CONFIG_PATH and os.path.exists(self.config_path):
            user_config = self._load_yaml(self.config_path)
        
        # Merge configurations (user config overrides default)
        config_data = self._merge_dicts(default_config, user_config)
        
        # Override with environment variables
        config_data = self._apply_env_overrides(config_data)
        
        # Cache the config data
        self.config_data = config_data
        self.loaded = True
        
        # Validate configuration
        return AppConfig(**config_data)
    
    def reload(self) -> AppConfig:
        """
        Reload configuration
        
        Returns:
            Validated configuration object
        """
        self.loaded = False
        return self.load()
    
    def save(self, config_path: Optional[str] = None) -> None:
        """
        Save current configuration to file
        
        Args:
            config_path: Path to save configuration to (None to use current path)
        """
        save_path = config_path or self.config_path
        
        with open(save_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.config_data, f, default_flow_style=False, sort_keys=False)
    
    def _load_yaml(self, path: str) -> Dict[str, Any]:
        """
        Load YAML configuration from file
        
        Args:
            path: Path to YAML file
            
        Returns:
            Configuration dictionary
            
        Raises:
            FileNotFoundError: If configuration file doesn't exist
            yaml.YAMLError: If YAML file is invalid
        """
        if not os.path.exists(path):
            raise FileNotFoundError(f"Configuration file not found: {path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _merge_dicts(self, dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively merge two dictionaries
        
        Args:
            dict1: Base dictionary
            dict2: Dictionary to merge (overrides dict1)
            
        Returns:
            Merged dictionary
        """
        result = dict1.copy()
        
        for key, value in dict2.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_dicts(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _apply_env_overrides(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply environment variable overrides to configuration
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Updated configuration dictionary
        """
        result = config.copy()
        
        # Get all environment variables with prefix
        for key, value in os.environ.items():
            if key.startswith(ENV_PREFIX):
                # Remove prefix
                config_key = key[len(ENV_PREFIX):]
                
                # Convert to nested keys
                keys = config_key.lower().split('__')
                
                # Convert value to appropriate type
                typed_value = self._convert_env_value(value)
                
                # Update configuration
                self._set_nested_value(result, keys, typed_value)
        
        return result
    
    def _convert_env_value(self, value: str) -> Any:
        """
        Convert environment variable string to appropriate Python type
        
        Args:
            value: String value from environment variable
            
        Returns:
            Converted value (bool, int, float, or string)
        """
        # Check for boolean
        if value.lower() in ("true", "yes", "1"):
            return True
        if value.lower() in ("false", "no", "0"):
            return False
        
        # Check for None/null
        if value.lower() in ("none", "null"):
            return None
        
        # Check for integer
        try:
            return int(value)
        except ValueError:
            pass
        
        # Check for float
        try:
            return float(value)
        except ValueError:
            pass
        
        # Check for JSON
        if (value.startswith('{') and value.endswith('}')) or \
           (value.startswith('[') and value.endswith(']')):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                pass
        
        # Default to string
        return value
    
    def _set_nested_value(self, config: Dict[str, Any], keys: list, value: Any) -> None:
        """
        Set a value in a nested dictionary using a list of keys
        
        Args:
            config: Configuration dictionary to update
            keys: List of keys representing the path in the dict
            value: Value to set
        """
        current = config
        
        # Navigate to the correct level
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            elif not isinstance(current[key], dict):
                current[key] = {}
            
            current = current[key]
        
        # Set the value
        current[keys[-1]] = value

# Global configuration instance
_config_instance = None

def get_config(config_path: Optional[str] = None) -> AppConfig:
    """
    Get configuration instance
    
    Args:
        config_path: Optional path to configuration file
        
    Returns:
        Validated configuration object
    """
    global _config_instance
    
    if _config_instance is None or config_path is not None:
        loader = ConfigLoader(config_path)
        _config_instance = loader.load()
    
    return _config_instance

def reload_config() -> AppConfig:
    """
    Reload configuration
    
    Returns:
        Reloaded configuration object
    """
    global _config_instance
    
    if _config_instance is None:
        return get_config()
    
    loader = ConfigLoader()
    _config_instance = loader.reload()
    
    return _config_instance