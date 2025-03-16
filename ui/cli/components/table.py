"""
CLI table component implementation
"""

from typing import Dict, List, Any, Optional
from texttable import Texttable

from ui.base import TableComponent

class CLITableComponent(TableComponent):
    """CLI implementation of table component"""
    
    def __init__(self, name: str = "table", description: str = "Table display"):
        """Initialize CLI table component"""
        super().__init__(name, description)
        self.headers = []
        self.rows = []
        self.max_width = 120
    
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
        
        if not self.rows:
            print(f"{self.description}: No data available for display")
            return
        
        # Create table
        table = Texttable(max_width=self.max_width)
        table.set_deco(Texttable.HEADER)
        table.set_cols_dtype(['t'] * len(self.headers))  # All columns are text
        table.set_cols_align(['l'] * len(self.headers))  # All columns are left-aligned
        
        # Add headers
        table.header(self.headers)
        
        # Add rows
        for row in self.rows:
            table.add_row(row)
        
        # Print table
        print(f"{self.description}:")
        print(table.draw())
    
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