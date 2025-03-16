"""
CLI alert component implementation
"""

from typing import Any

from ui.base import AlertComponent

class CLIAlertComponent(AlertComponent):
    """CLI implementation of alert component"""
    
    def __init__(self, name: str = "alert", description: str = "Alert display"):
        """Initialize CLI alert component"""
        super().__init__(name, description)
    
    def render(self, data: Any = None) -> None:
        """
        Render the alert component
        
        Args:
            data: Alert data (dict with type and message)
        """
        if data:
            alert_type = data.get("type", "info")
            message = data.get("message", "")
            
            if alert_type == "info":
                self.info(message)
            elif alert_type == "success":
                self.success(message)
            elif alert_type == "warning":
                self.warning(message)
            elif alert_type == "error":
                self.error(message)
    
    def info(self, message: str) -> None:
        """
        Display info alert
        
        Args:
            message: Alert message
        """
        print(f"[INFO] {message}")
    
    def success(self, message: str) -> None:
        """
        Display success alert
        
        Args:
            message: Alert message
        """
        print(f"[SUCCESS] {message}")
    
    def warning(self, message: str) -> None:
        """
        Display warning alert
        
        Args:
            message: Alert message
        """
        print(f"[WARNING] {message}")
    
    def error(self, message: str) -> None:
        """
        Display error alert
        
        Args:
            message: Alert message
        """
        print(f"[ERROR] {message}")