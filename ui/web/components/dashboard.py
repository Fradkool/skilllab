"""
Web dashboard component implementation
"""

from typing import Dict, List, Any, Optional
import streamlit as st

from ui.base import UIComponent, DashboardComponent
from ui.web.components.progress import WebProgressComponent
from ui.web.components.table import WebTableComponent
from ui.web.components.chart import WebChartComponent
from ui.web.components.form import WebFormComponent
from ui.web.components.alert import WebAlertComponent

class WebDashboardComponent(DashboardComponent):
    """Web implementation of dashboard component using Streamlit"""
    
    def __init__(self, name: str = "dashboard", description: str = "Dashboard component"):
        """Initialize web dashboard component"""
        super().__init__(name, description)
        self.layout = {
            "type": "grid",  # or "tabs"
            "columns": 2
        }
    
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
                    position = widget_data.get("position")
                    
                    # Create component based on type
                    if component_type == "progress":
                        component = WebProgressComponent()
                    elif component_type == "table":
                        component = WebTableComponent()
                    elif component_type == "chart":
                        component = WebChartComponent()
                    elif component_type == "form":
                        component = WebFormComponent()
                    elif component_type == "alert":
                        component = WebAlertComponent()
                    else:
                        st.warning(f"Unknown widget type: {component_type}")
                        continue
                    
                    self.add_widget(widget_id, component, position)
                    self.update_widget(widget_id, component_data)
            
            if "layout" in data:
                self.layout = data["layout"]
        
        # Display dashboard title
        if self.description:
            st.title(self.description)
        
        # Render widgets based on layout type
        if self.layout["type"] == "grid":
            self._render_grid_layout()
        elif self.layout["type"] == "tabs":
            self._render_tabs_layout()
        else:
            self._render_default_layout()
    
    def _render_grid_layout(self) -> None:
        """Render dashboard widgets in a grid layout"""
        num_columns = self.layout.get("columns", 2)
        
        # Group widgets by row
        widgets_by_row = {}
        
        for widget_id, widget in self.widgets.items():
            position = widget.get("position", {})
            row = position.get("row", 0)
            
            if row not in widgets_by_row:
                widgets_by_row[row] = []
            
            widgets_by_row[row].append((widget_id, widget))
        
        # Sort rows
        rows = sorted(widgets_by_row.keys())
        
        # Render each row
        for row in rows:
            row_widgets = widgets_by_row[row]
            
            # Sort widgets by column
            row_widgets.sort(key=lambda w: w[1].get("position", {}).get("col", 0))
            
            # Create columns
            columns = st.columns(num_columns)
            
            # Render widgets in columns
            for i, (widget_id, widget) in enumerate(row_widgets):
                col_index = i % num_columns
                with columns[col_index]:
                    st.markdown(f"**{widget_id}**")
                    widget["component"].render(widget.get("data"))
    
    def _render_tabs_layout(self) -> None:
        """Render dashboard widgets in tabs"""
        # Group widgets by tab
        widgets_by_tab = {}
        
        for widget_id, widget in self.widgets.items():
            position = widget.get("position", {})
            tab = position.get("tab", "Main")
            
            if tab not in widgets_by_tab:
                widgets_by_tab[tab] = []
            
            widgets_by_tab[tab].append((widget_id, widget))
        
        # Create tabs
        tabs = st.tabs(list(widgets_by_tab.keys()))
        
        # Render widgets in each tab
        for i, (tab_name, tab_widgets) in enumerate(widgets_by_tab.items()):
            with tabs[i]:
                for widget_id, widget in tab_widgets:
                    st.markdown(f"**{widget_id}**")
                    widget["component"].render(widget.get("data"))
    
    def _render_default_layout(self) -> None:
        """Render dashboard widgets in default layout (sequential)"""
        for widget_id, widget in self.widgets.items():
            st.markdown(f"**{widget_id}**")
            widget["component"].render(widget.get("data"))
    
    def add_widget(self, widget_id: str, component: UIComponent, 
                  position: Optional[Dict[str, Any]] = None) -> None:
        """
        Add a widget to the dashboard
        
        Args:
            widget_id: Widget identifier
            component: Widget component
            position: Widget position
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