"""
CLI dashboard component implementation
"""

from typing import Dict, List, Any, Optional

from ui.base import UIComponent, DashboardComponent
from ui.cli.components.progress import CLIProgressComponent
from ui.cli.components.table import CLITableComponent
from ui.cli.components.alert import CLIAlertComponent
from ui.cli.components.chart import CLIChartComponent
from ui.cli.components.form import CLIFormComponent

class CLIDashboardComponent(DashboardComponent):
    """CLI implementation of dashboard component"""
    
    def __init__(self, name: str = "dashboard", description: str = "Dashboard component"):
        """Initialize CLI dashboard component"""
        super().__init__(name, description)
    
    def render(self, data: Any = None) -> None:
        """
        Render the dashboard component
        
        Args:
            data: Dashboard data
        """
        if data:
            if "widgets" in data:
                for widget_id, widget_data in data["widgets"].items():
                    component_type = widget_data.get("type")
                    component_data = widget_data.get("data")
                    
                    # Create component based on type
                    if component_type == "progress":
                        component = CLIProgressComponent()
                    elif component_type == "table":
                        component = CLITableComponent()
                    elif component_type == "chart":
                        component = CLIChartComponent()
                    elif component_type == "form":
                        component = CLIFormComponent()
                    elif component_type == "alert":
                        component = CLIAlertComponent()
                    else:
                        print(f"Unknown widget type: {component_type}")
                        continue
                    
                    self.add_widget(widget_id, component)
                    self.update_widget(widget_id, component_data)
        
        # Display dashboard title
        print(f"\n{self.description}")
        print("=" * len(self.description))
        
        # Render widgets
        for widget_id, widget in self.widgets.items():
            widget["component"].render(widget.get("data"))
            print()  # Add separator between widgets
    
    def add_widget(self, widget_id: str, component: UIComponent, 
                  position: Optional[Dict[str, Any]] = None) -> None:
        """
        Add a widget to the dashboard
        
        Args:
            widget_id: Widget identifier
            component: Widget component
            position: Widget position (not used in CLI)
        """
        self.widgets[widget_id] = {
            "component": component,
            "position": position,
            "data": None
        }
    
    def update_widget(self, widget_id: str, data: Any) -> None:
        """
        Update a dashboard widget
        
        Args:
            widget_id: Widget identifier
            data: Widget data
        """
        if widget_id in self.widgets:
            self.widgets[widget_id]["data"] = data
    
    def remove_widget(self, widget_id: str) -> None:
        """
        Remove a dashboard widget
        
        Args:
            widget_id: Widget identifier
        """
        if widget_id in self.widgets:
            del self.widgets[widget_id]