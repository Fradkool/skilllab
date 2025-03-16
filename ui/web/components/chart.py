"""
Web chart component implementation
"""

from typing import Dict, List, Any, Optional
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from ui.base import ChartComponent

class WebChartComponent(ChartComponent):
    """Web implementation of chart component using Streamlit with Plotly"""
    
    def __init__(self, name: str = "chart", description: str = "Chart display"):
        """Initialize web chart component"""
        super().__init__(name, description)
        self.data = {}
        self.options = {
            "type": "bar",
            "title": "",
            "x_label": "",
            "y_label": "",
            "height": 400,
            "color_discrete_sequence": None,
            "use_container_width": True
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
            st.info("No data available for chart")
            return
        
        # Extract chart type
        chart_type = self.options.get("type", "bar")
        
        # Create chart based on type
        try:
            if chart_type == "bar":
                self._render_bar_chart()
            elif chart_type == "line":
                self._render_line_chart()
            elif chart_type == "scatter":
                self._render_scatter_chart()
            elif chart_type == "pie":
                self._render_pie_chart()
            elif chart_type == "area":
                self._render_area_chart()
            else:
                st.warning(f"Chart type '{chart_type}' not recognized")
        except Exception as e:
            st.error(f"Error rendering chart: {str(e)}")
    
    def _render_bar_chart(self) -> None:
        """Render bar chart using Plotly"""
        # Create DataFrame from data
        if "labels" in self.data and "values" in self.data:
            df = pd.DataFrame({
                "x": self.data["labels"],
                "y": self.data["values"]
            })
        elif "dataframe" in self.data:
            df = self.data["dataframe"]
        else:
            st.warning("Invalid data format for bar chart")
            return
        
        # Create bar chart
        fig = px.bar(
            df,
            x="x" if "x" in df.columns else df.columns[0],
            y="y" if "y" in df.columns else df.columns[1],
            title=self.options.get("title", ""),
            labels={
                "x": self.options.get("x_label", ""),
                "y": self.options.get("y_label", "")
            },
            color_discrete_sequence=self.options.get("color_discrete_sequence"),
            height=self.options.get("height", 400)
        )
        
        # Update layout
        fig.update_layout(
            margin=dict(l=20, r=20, t=40, b=20),
        )
        
        # Display chart
        st.plotly_chart(fig, use_container_width=self.options.get("use_container_width", True))
    
    def _render_line_chart(self) -> None:
        """Render line chart using Plotly"""
        # Create DataFrame from data
        if "labels" in self.data and "values" in self.data:
            df = pd.DataFrame({
                "x": self.data["labels"],
                "y": self.data["values"]
            })
        elif "dataframe" in self.data:
            df = self.data["dataframe"]
        else:
            st.warning("Invalid data format for line chart")
            return
        
        # Create line chart
        fig = px.line(
            df,
            x="x" if "x" in df.columns else df.columns[0],
            y="y" if "y" in df.columns else df.columns[1],
            title=self.options.get("title", ""),
            labels={
                "x": self.options.get("x_label", ""),
                "y": self.options.get("y_label", "")
            },
            color_discrete_sequence=self.options.get("color_discrete_sequence"),
            height=self.options.get("height", 400)
        )
        
        # Update layout
        fig.update_layout(
            margin=dict(l=20, r=20, t=40, b=20),
        )
        
        # Display chart
        st.plotly_chart(fig, use_container_width=self.options.get("use_container_width", True))
    
    def _render_scatter_chart(self) -> None:
        """Render scatter chart using Plotly"""
        # Check if we have the right data format
        if "x" in self.data and "y" in self.data:
            df = pd.DataFrame({
                "x": self.data["x"],
                "y": self.data["y"]
            })
            
            # Add color data if available
            if "color" in self.data:
                df["color"] = self.data["color"]
                color = "color"
            else:
                color = None
            
            # Add size data if available
            if "size" in self.data:
                df["size"] = self.data["size"]
                size = "size"
            else:
                size = None
            
            # Create scatter chart
            fig = px.scatter(
                df,
                x="x",
                y="y",
                color=color,
                size=size,
                title=self.options.get("title", ""),
                labels={
                    "x": self.options.get("x_label", ""),
                    "y": self.options.get("y_label", "")
                },
                color_discrete_sequence=self.options.get("color_discrete_sequence"),
                height=self.options.get("height", 400)
            )
            
            # Update layout
            fig.update_layout(
                margin=dict(l=20, r=20, t=40, b=20),
            )
            
            # Display chart
            st.plotly_chart(fig, use_container_width=self.options.get("use_container_width", True))
        elif "dataframe" in self.data:
            df = self.data["dataframe"]
            
            if len(df.columns) < 2:
                st.warning("DataFrame must have at least 2 columns for scatter chart")
                return
            
            x_col = self.options.get("x_column", df.columns[0])
            y_col = self.options.get("y_column", df.columns[1])
            color_col = self.options.get("color_column", None)
            size_col = self.options.get("size_column", None)
            
            # Create scatter chart
            fig = px.scatter(
                df,
                x=x_col,
                y=y_col,
                color=color_col,
                size=size_col,
                title=self.options.get("title", ""),
                labels={
                    x_col: self.options.get("x_label", x_col),
                    y_col: self.options.get("y_label", y_col)
                },
                color_discrete_sequence=self.options.get("color_discrete_sequence"),
                height=self.options.get("height", 400)
            )
            
            # Update layout
            fig.update_layout(
                margin=dict(l=20, r=20, t=40, b=20),
            )
            
            # Display chart
            st.plotly_chart(fig, use_container_width=self.options.get("use_container_width", True))
        else:
            st.warning("Invalid data format for scatter chart")
    
    def _render_pie_chart(self) -> None:
        """Render pie chart using Plotly"""
        # Create DataFrame from data
        if "labels" in self.data and "values" in self.data:
            df = pd.DataFrame({
                "labels": self.data["labels"],
                "values": self.data["values"]
            })
        elif "dataframe" in self.data:
            df = self.data["dataframe"]
        else:
            st.warning("Invalid data format for pie chart")
            return
        
        # Create pie chart
        fig = px.pie(
            df,
            names="labels" if "labels" in df.columns else df.columns[0],
            values="values" if "values" in df.columns else df.columns[1],
            title=self.options.get("title", ""),
            color_discrete_sequence=self.options.get("color_discrete_sequence"),
            height=self.options.get("height", 400)
        )
        
        # Update layout
        fig.update_layout(
            margin=dict(l=20, r=20, t=40, b=20),
        )
        
        # Display chart
        st.plotly_chart(fig, use_container_width=self.options.get("use_container_width", True))
    
    def _render_area_chart(self) -> None:
        """Render area chart using Plotly"""
        # Create DataFrame from data
        if "labels" in self.data and "values" in self.data:
            df = pd.DataFrame({
                "x": self.data["labels"],
                "y": self.data["values"]
            })
        elif "dataframe" in self.data:
            df = self.data["dataframe"]
        else:
            st.warning("Invalid data format for area chart")
            return
        
        # Create area chart
        fig = px.area(
            df,
            x="x" if "x" in df.columns else df.columns[0],
            y="y" if "y" in df.columns else df.columns[1],
            title=self.options.get("title", ""),
            labels={
                "x": self.options.get("x_label", ""),
                "y": self.options.get("y_label", "")
            },
            color_discrete_sequence=self.options.get("color_discrete_sequence"),
            height=self.options.get("height", 400)
        )
        
        # Update layout
        fig.update_layout(
            margin=dict(l=20, r=20, t=40, b=20),
        )
        
        # Display chart
        st.plotly_chart(fig, use_container_width=self.options.get("use_container_width", True))
    
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