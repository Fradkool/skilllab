"""
Base UI components for SkillLab
Provides abstract base classes for UI implementations
"""

from typing import Dict, List, Any, Optional, Callable, Union, Tuple
from abc import ABC, abstractmethod

class UIComponent(ABC):
    """Abstract base class for UI components"""
    
    def __init__(self, name: str, description: str = ""):
        """
        Initialize UI component
        
        Args:
            name: Component name
            description: Component description
        """
        self.name = name
        self.description = description
    
    @abstractmethod
    def render(self, data: Any = None) -> None:
        """
        Render the component
        
        Args:
            data: Component data
        """
        pass

class ProgressComponent(UIComponent):
    """Abstract base class for progress components"""
    
    def __init__(self, name: str = "progress", description: str = "Progress display"):
        """Initialize progress component"""
        super().__init__(name, description)
    
    @abstractmethod
    def update(self, current: int, total: int, message: str = "") -> None:
        """
        Update progress
        
        Args:
            current: Current progress value
            total: Total progress value
            message: Optional message
        """
        pass
    
    @abstractmethod
    def complete(self, message: str = "Completed") -> None:
        """
        Mark progress as complete
        
        Args:
            message: Completion message
        """
        pass

class TableComponent(UIComponent):
    """Abstract base class for table components"""
    
    def __init__(self, name: str = "table", description: str = "Table display"):
        """Initialize table component"""
        super().__init__(name, description)
        self.headers = []
        self.rows = []
    
    @abstractmethod
    def set_headers(self, headers: List[str]) -> None:
        """
        Set table headers
        
        Args:
            headers: List of header names
        """
        pass
    
    @abstractmethod
    def add_row(self, row: List[Any]) -> None:
        """
        Add a row to the table
        
        Args:
            row: Row data
        """
        pass

class ChartComponent(UIComponent):
    """Abstract base class for chart components"""
    
    def __init__(self, name: str = "chart", description: str = "Chart display"):
        """Initialize chart component"""
        super().__init__(name, description)
    
    @abstractmethod
    def set_data(self, data: Dict[str, Any]) -> None:
        """
        Set chart data
        
        Args:
            data: Chart data
        """
        pass
    
    @abstractmethod
    def set_options(self, options: Dict[str, Any]) -> None:
        """
        Set chart options
        
        Args:
            options: Chart options
        """
        pass

class FormComponent(UIComponent):
    """Abstract base class for form components"""
    
    def __init__(self, name: str = "form", description: str = "Input form"):
        """Initialize form component"""
        super().__init__(name, description)
        self.fields = {}
        self.values = {}
    
    @abstractmethod
    def add_field(self, field_id: str, field_type: str, label: str, 
                 required: bool = False, default: Any = None,
                 options: List[Any] = None) -> None:
        """
        Add a field to the form
        
        Args:
            field_id: Field identifier
            field_type: Field type
            label: Field label
            required: Whether field is required
            default: Default value
            options: Options for select fields
        """
        pass
    
    @abstractmethod
    def get_values(self) -> Dict[str, Any]:
        """
        Get form values
        
        Returns:
            Dictionary with form values
        """
        pass
    
    @abstractmethod
    def set_values(self, values: Dict[str, Any]) -> None:
        """
        Set form values
        
        Args:
            values: Dictionary with form values
        """
        pass
    
    @abstractmethod
    def validate(self) -> Tuple[bool, List[str]]:
        """
        Validate form values
        
        Returns:
            Tuple of (is_valid, error_messages)
        """
        pass
    
    @abstractmethod
    def is_submitted(self) -> bool:
        """
        Check if form was submitted
        
        Returns:
            True if form was submitted, False otherwise
        """
        pass

class AlertComponent(UIComponent):
    """Abstract base class for alert components"""
    
    def __init__(self, name: str = "alert", description: str = "Alert display"):
        """Initialize alert component"""
        super().__init__(name, description)
    
    @abstractmethod
    def info(self, message: str) -> None:
        """
        Display info alert
        
        Args:
            message: Alert message
        """
        pass
    
    @abstractmethod
    def success(self, message: str) -> None:
        """
        Display success alert
        
        Args:
            message: Alert message
        """
        pass
    
    @abstractmethod
    def warning(self, message: str) -> None:
        """
        Display warning alert
        
        Args:
            message: Alert message
        """
        pass
    
    @abstractmethod
    def error(self, message: str) -> None:
        """
        Display error alert
        
        Args:
            message: Alert message
        """
        pass

class NavComponent(UIComponent):
    """Abstract base class for navigation components"""
    
    def __init__(self, name: str = "navigation", description: str = "Navigation component"):
        """Initialize navigation component"""
        super().__init__(name, description)
        self.items = []
    
    @abstractmethod
    def add_item(self, item_id: str, label: str, url: Optional[str] = None,
                action: Optional[Callable] = None, parent: Optional[str] = None) -> None:
        """
        Add a navigation item
        
        Args:
            item_id: Item identifier
            label: Item label
            url: Item URL
            action: Item action
            parent: Parent item ID for hierarchical navigation
        """
        pass
    
    @abstractmethod
    def set_active(self, item_id: str) -> None:
        """
        Set active navigation item
        
        Args:
            item_id: Item identifier
        """
        pass

class DashboardComponent(UIComponent):
    """Abstract base class for dashboard components"""
    
    def __init__(self, name: str = "dashboard", description: str = "Dashboard component"):
        """Initialize dashboard component"""
        super().__init__(name, description)
        self.widgets = {}
    
    @abstractmethod
    def add_widget(self, widget_id: str, component: UIComponent, 
                  position: Optional[Dict[str, Any]] = None) -> None:
        """
        Add a widget to the dashboard
        
        Args:
            widget_id: Widget identifier
            component: Widget component
            position: Widget position
        """
        pass
    
    @abstractmethod
    def update_widget(self, widget_id: str, data: Any) -> None:
        """
        Update a dashboard widget
        
        Args:
            widget_id: Widget identifier
            data: Widget data
        """
        pass
    
    @abstractmethod
    def remove_widget(self, widget_id: str) -> None:
        """
        Remove a dashboard widget
        
        Args:
            widget_id: Widget identifier
        """
        pass