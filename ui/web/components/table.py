"""
Web table component implementation
"""

from typing import Dict, List, Any, Optional
import pandas as pd
import streamlit as st

from ui.base import TableComponent

class WebTableComponent(TableComponent):
    """Web implementation of table component using Streamlit"""
    
    def __init__(self, name: str = "table", description: str = "Table display"):
        """Initialize web table component"""
        super().__init__(name, description)
        self.headers = []
        self.rows = []
        self.options = {
            "use_container_width": True,
            "column_config": {},
            "hide_index": True
        }
    
    def render(self, data: Any = None) -> None:
        """
        Render the table component
        
        Args:
            data: Table data (dict with headers and rows)
        """
        if data:
            if "headers" in data:
                self.set_headers(data["headers"])
            
            if "rows" in data:
                self.rows = []  # Clear existing rows
                for row in data["rows"]:
                    self.add_row(row)
            
            if "options" in data:
                self.options.update(data["options"])
        
        if not self.rows:
            st.info("No data available for display")
            return
        
        # Create DataFrame from rows
        df = pd.DataFrame(self.rows, columns=self.headers)
        
        # Apply column configuration
        column_config = {}
        for header in self.headers:
            if header in self.options.get("column_config", {}):
                column_config[header] = self.options["column_config"][header]
        
        # Display table
        st.dataframe(
            df,
            use_container_width=self.options.get("use_container_width", True),
            column_config=column_config,
            hide_index=self.options.get("hide_index", True)
        )
    
    def set_headers(self, headers: List[str]) -> None:
        """
        Set table headers
        
        Args:
            headers: List of header names
        """
        self.headers = headers
    
    def add_row(self, row: List[Any]) -> None:
        """
        Add a row to the table
        
        Args:
            row: Row data
        """
        self.rows.append(row)