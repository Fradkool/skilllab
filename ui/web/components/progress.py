"""
Web progress component implementation
"""

import time
from typing import Dict, List, Any, Optional
import streamlit as st

from ui.base import ProgressComponent

class WebProgressComponent(ProgressComponent):
    """Web implementation of progress component using Streamlit"""
    
    def __init__(self, name: str = "progress", description: str = "Progress display"):
        """Initialize web progress component"""
        super().__init__(name, description)
        self.progress_placeholder = None
        self.status_placeholder = None
        self.current_value = 0
        self.total_value = 100
    
    def render(self, data: Any = None) -> None:
        """
        Render the progress component
        
        Args:
            data: Progress data (dict with current, total, message)
        """
        # Create placeholders if not already created
        if self.progress_placeholder is None:
            self.progress_placeholder = st.empty()
        
        if self.status_placeholder is None:
            self.status_placeholder = st.empty()
        
        # Update values from data if provided
        if data:
            if "current" in data:
                self.current_value = data["current"]
            
            if "total" in data:
                self.total_value = data["total"]
            
            if "message" in data:
                self.status_placeholder.text(data["message"])
        
        # Calculate progress percentage (avoid division by zero)
        if self.total_value > 0:
            progress_value = min(1.0, self.current_value / self.total_value)
        else:
            progress_value = 0
        
        # Update progress bar
        self.progress_placeholder.progress(progress_value)
    
    def update(self, current: int, total: int, message: str = "") -> None:
        """
        Update progress
        
        Args:
            current: Current progress value
            total: Total progress value
            message: Optional message
        """
        self.current_value = current
        self.total_value = total
        
        # Create placeholders if not already created
        if self.progress_placeholder is None:
            self.progress_placeholder = st.empty()
        
        if self.status_placeholder is None:
            self.status_placeholder = st.empty()
        
        # Calculate progress percentage (avoid division by zero)
        if total > 0:
            progress_value = min(1.0, current / total)
        else:
            progress_value = 0
        
        # Update progress bar and message
        self.progress_placeholder.progress(progress_value)
        
        if message:
            self.status_placeholder.text(message)
    
    def complete(self, message: str = "Completed") -> None:
        """
        Mark progress as complete
        
        Args:
            message: Completion message
        """
        if self.progress_placeholder is not None:
            self.progress_placeholder.progress(1.0)
        
        if self.status_placeholder is not None:
            self.status_placeholder.text(message)
            
        # Clear placeholders after a short delay
        time.sleep(0.5)
        if self.progress_placeholder is not None:
            self.progress_placeholder.empty()
        
        if self.status_placeholder is not None:
            self.status_placeholder.empty()