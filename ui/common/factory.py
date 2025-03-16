
"""
UI Factory module for SkillLab
Provides a factory for creating UI components based on the interface type
"""

from enum import Enum
from typing import Dict, Any, Optional, Type

from ui.base import (
    UIComponent, ProgressComponent, TableComponent, 
    ChartComponent, FormComponent, AlertComponent,
    NavComponent, DashboardComponent
)

from ui.cli.components.progress import CLIProgressComponent
from ui.cli.components.table import CLITableComponent
from ui.cli.components.chart import CLIChartComponent
from ui.cli.components.form import CLIFormComponent
from ui.cli.components.alert import CLIAlertComponent
from ui.cli.components.navigation import CLINavComponent
from ui.cli.components.dashboard import CLIDashboardComponent

from ui.web.components.progress import WebProgressComponent
from ui.web.components.table import WebTableComponent
from ui.web.components.chart import WebChartComponent
from ui.web.components.form import WebFormComponent
from ui.web.components.alert import WebAlertComponent
from ui.web.components.navigation import WebNavComponent
from ui.web.components.dashboard import WebDashboardComponent

class UIType(Enum):
    """UI type enumeration"""
    CLI = "cli"
    WEB = "web"

class UIComponentFactory:
    """Factory for creating UI components"""
    
    # Component mappings
    _component_map = {
        UIType.CLI: {
            "progress": CLIProgressComponent,
            "table": CLITableComponent,
            "chart": CLIChartComponent,
            "form": CLIFormComponent,
            "alert": CLIAlertComponent,
            "navigation": CLINavComponent,
            "dashboard": CLIDashboardComponent
        },
        UIType.WEB: {
            "progress": WebProgressComponent,
            "table": WebTableComponent,
            "chart": WebChartComponent,
            "form": WebFormComponent,
            "alert": WebAlertComponent,
            "navigation": WebNavComponent,
            "dashboard": WebDashboardComponent
        }
    }
    
    @classmethod
    def create_component(cls, component_type: str, ui_type: UIType, name: str = "", description: str = "") -> Optional[UIComponent]:
        """
        Create a UI component
        
        Args:
            component_type: Type of component to create
            ui_type: Type of UI (CLI or Web)
            name: Component name
            description: Component description
            
        Returns:
            UI component instance or None if type not found
        """
        if ui_type not in cls._component_map:
            return None
        
        component_class = cls._component_map[ui_type].get(component_type)
        if not component_class:
            return None
        
        return component_class(name=name, description=description)
    
    @classmethod
    def register_component(cls, component_type: str, ui_type: UIType, component_class: Type[UIComponent]) -> None:
        """
        Register a custom component type
        
        Args:
            component_type: Type of component to register
            ui_type: Type of UI (CLI or Web)
            component_class: Component class
        """
        if ui_type not in cls._component_map:
            cls._component_map[ui_type] = {}
        
        cls._component_map[ui_type][component_type] = component_class