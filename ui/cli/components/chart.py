"""
CLI chart component implementation
"""

from typing import Dict, List, Any, Optional

from ui.base import ChartComponent

class CLIChartComponent(ChartComponent):
    """CLI implementation of chart component"""
    
    def __init__(self, name: str = "chart", description: str = "Chart display"):
        """Initialize CLI chart component"""
        super().__init__(name, description)
        self.data = {}
        self.options = {
            "type": "bar",
            "width": 80,
            "height": 15
        }
    
    def render(self, data: Any = None) -> None:
        """
        Render the chart component
        
        Args:
            data: Chart data
        """
        if data:
            self.set_data(data)
        
        if not self.data:
            print(f"{self.description}: No data available for chart")
            return
        
        # Extract chart type
        chart_type = self.options.get("type", "bar")
        
        # Create chart based on type
        try:
            if chart_type == "bar":
                self._render_bar_chart()
            elif chart_type == "line":
                self._render_line_chart()
            else:
                print(f"Chart type '{chart_type}' not supported in CLI")
        except Exception as e:
            print(f"Error rendering chart: {str(e)}")
    
    def _render_bar_chart(self) -> None:
        """Render bar chart using ASCII"""
        if "labels" in self.data and "values" in self.data:
            labels = self.data["labels"]
            values = self.data["values"]
            
            max_value = max(values) if values else 0
            max_label_len = max(len(str(label)) for label in labels) if labels else 0
            
            print(f"{self.description}:")
            
            for i, (label, value) in enumerate(zip(labels, values)):
                # Calculate bar length
                bar_len = int(value / max_value * 30) if max_value > 0 else 0
                bar = "#" * bar_len
                
                # Format label with padding
                padded_label = str(label).ljust(max_label_len)
                
                # Print bar
                print(f"  {padded_label} | {bar} {value}")
        else:
            print(f"{self.description}: Invalid data format for bar chart")
    
    def _render_line_chart(self) -> None:
        """Render simple line chart using ASCII"""
        if "values" in self.data:
            values = self.data["values"]
            
            # Simple line chart with * for each point
            print(f"{self.description}:")
            
            max_value = max(values) if values else 0
            num_values = len(values)
            
            if max_value <= 0:
                print("  No data to display")
                return
            
            # Create chart with 10 rows
            height = 10
            for y in range(height, 0, -1):
                row = "  "
                for x in range(num_values):
                    if values[x] / max_value * height >= y:
                        row += "* "
                    else:
                        row += "  "
                print(row)
            
            # Print x-axis
            print("  " + "-" * (num_values * 2))
            
            # Print x labels if available
            if "labels" in self.data:
                labels = self.data["labels"]
                if len(labels) == num_values:
                    row = "  "
                    for label in labels:
                        row += str(label)[:2] + " "
                    print(row)
        else:
            print(f"{self.description}: Invalid data format for line chart")
    
    def set_data(self, data: Dict[str, Any]) -> None:
        """
        Set chart data
        
        Args:
            data: Chart data
        """
        self.data = data
    
    def set_options(self, options: Dict[str, Any]) -> None:
        """
        Set chart options
        
        Args:
            options: Chart options
        """
        self.options.update(options)