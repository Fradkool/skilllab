# SkillLab UI Component System Guide

This document provides guidance on using the new UI component system that has been implemented as part of the SkillLab refactoring.

## Quick Start

The UI component system can be used through the centralized launcher:

```bash
# Launch any UI using the centralized launcher
python launch_ui.py [dashboard|monitor|review|training|extraction] --ui-type [cli|web]

# Or through the CLI command
skilllab ui [dashboard|monitor|review|training|extraction] --ui-type [cli|web]
```

For more details on available commands, see the [CLI Guide](CLI_GUIDE.md).

## Overview

The UI component system provides a flexible, modular approach to building user interfaces for both CLI and web applications. It uses a combination of design patterns:

1. **Factory Pattern** - Creates UI components appropriate for the selected UI type (CLI or Web)
2. **Adapter Pattern** - Connects API data with UI components
3. **Component Pattern** - Breaks down complex UIs into reusable pieces

## Directory Structure

```
ui/
├── __init__.py
├── base.py                # Base component classes and interfaces
├── cli/                   # CLI-specific implementations
│   ├── __init__.py
│   ├── cli_app.py
│   └── components/
│       ├── alert.py
│       ├── chart.py
│       ├── dashboard.py
│       ├── form.py
│       ├── navigation.py
│       ├── progress.py
│       └── table.py
├── common/                # Shared functionality 
│   ├── __init__.py
│   ├── adapter.py         # API to UI adapters
│   ├── factory.py         # Component factory
│   └── manager.py         # UI manager for orchestration
└── web/                   # Web-specific implementations
    ├── __init__.py
    ├── components/
    │   ├── alert.py
    │   ├── chart.py
    │   ├── dashboard.py
    │   ├── form.py
    │   ├── navigation.py
    │   ├── progress.py
    │   └── table.py
    ├── exports.py
    └── web_app.py
```

## Key Components

### 1. Component Interfaces

The `ui/base.py` file defines abstract base classes for all UI components:

- `UIComponent` - Base class for all components
- `ProgressComponent` - For displaying progress bars/indicators
- `TableComponent` - For displaying tabular data
- `ChartComponent` - For displaying charts and graphs
- `FormComponent` - For data input forms
- `AlertComponent` - For notifications and alerts
- `NavComponent` - For navigation elements
- `DashboardComponent` - For combining multiple components

### 2. Component Factory

The `ui/common/factory.py` file provides a factory for creating components based on UI type:

```python
from ui.common.factory import UIComponentFactory, UIType

# Create a web table component
table = UIComponentFactory.create_component(
    "table", UIType.WEB, "my_table", "My Table"
)

# Create a CLI progress component
progress = UIComponentFactory.create_component(
    "progress", UIType.CLI, "my_progress", "My Progress"
)
```

### 3. API Adapters

The `ui/common/adapter.py` file provides adapters that connect API data to UI components:

- `MonitoringAdapter` - For monitoring dashboards
- `ReviewAdapter` - For document review interfaces
- `TrainingAdapter` - For model training interfaces

### 4. UI Manager

The `ui/common/manager.py` file provides a central manager for UI operations:

```python
from ui.common.manager import UIManager, UIType, UIMode

# Create a manager for web UI
manager = UIManager(UIType.WEB)

# Set UI mode
manager.set_mode(UIMode.DASHBOARD)

# Render the UI
manager.render_ui()
```

## Usage Examples

### Creating a Simple Dashboard

```python
from ui.common.factory import UIComponentFactory, UIType

# Create a dashboard component
dashboard = UIComponentFactory.create_component(
    "dashboard", UIType.WEB, "my_dashboard", "My Dashboard"
)

# Create child components
table = UIComponentFactory.create_component(
    "table", UIType.WEB, "my_table", "My Table"
)
chart = UIComponentFactory.create_component(
    "chart", UIType.WEB, "my_chart", "My Chart"
)

# Add components to dashboard
dashboard.add_widget("table", table, {"row": 0, "col": 0})
dashboard.add_widget("chart", chart, {"row": 0, "col": 1})

# Update component with data
table_data = {
    "headers": ["Column 1", "Column 2"],
    "rows": [
        ["Value 1", "Value 2"],
        ["Value 3", "Value 4"]
    ]
}
dashboard.update_widget("table", table_data)

# Render the dashboard
dashboard.render()
```

### Using Adapters with APIs

```python
from ui.common.adapter import MonitoringAdapter
from ui.common.factory import UIType

# Create an adapter
monitoring = MonitoringAdapter(UIType.CLI)

# Refresh data from APIs
monitoring.refresh()

# Get the dashboard
dashboard = monitoring.get_dashboard()

# Render the dashboard
if dashboard:
    dashboard.render()
```

### Creating a Full Application

```python
from ui.common.manager import UIManager, UIType, UIMode

# Create UI manager
manager = UIManager(UIType.WEB)

# Set mode
manager.set_mode(UIMode.DASHBOARD)

# Render UI
manager.render_ui()
```

## Adding New Components

To add a new component type:

1. Add a new abstract base class in `ui/base.py`
2. Implement CLI version in `ui/cli/components/`
3. Implement web version in `ui/web/components/`
4. Register component in `ui/common/factory.py`

Example:

```python
# In ui/base.py
class MyNewComponent(UIComponent):
    """Abstract base class for my new component"""
    
    def __init__(self, name: str = "mynew", description: str = "My new component"):
        """Initialize component"""
        super().__init__(name, description)
    
    @abstractmethod
    def some_method(self, data: Any) -> None:
        """Component-specific method"""
        pass

# In ui/cli/components/mynew.py
class CLIMyNewComponent(MyNewComponent):
    """CLI implementation of my new component"""
    
    def render(self, data: Any = None) -> None:
        """Render the component"""
        # CLI-specific rendering
        
    def some_method(self, data: Any) -> None:
        """Implement component-specific method"""
        # CLI-specific implementation

# In ui/web/components/mynew.py
class WebMyNewComponent(MyNewComponent):
    """Web implementation of my new component"""
    
    def render(self, data: Any = None) -> None:
        """Render the component"""
        # Web-specific rendering
        
    def some_method(self, data: Any) -> None:
        """Implement component-specific method"""
        # Web-specific implementation

# In ui/common/factory.py
# Update _component_map
_component_map = {
    UIType.CLI: {
        # ... existing components
        "mynew": CLIMyNewComponent,
    },
    UIType.WEB: {
        # ... existing components
        "mynew": WebMyNewComponent,
    }
}
```

## Best Practices

1. **Component Isolation**: Components should not directly access APIs or external data
2. **Use Adapters**: Always use adapters to connect components with APIs
3. **Consistent Data**: Use consistent data structures for communication
4. **Fallback Rendering**: Always include fallback rendering for when components aren't available
5. **Keep Logic Separate**: Business logic belongs in APIs, not UI components

## Testing UI Components

UI components should be tested using the following approach:

1. **Unit Tests**: Test individual component rendering and behavior
2. **Integration Tests**: Test component interactions and data flow
3. **Mock Adapters**: Use mock adapters to test UI without real APIs
4. **Visual Testing**: Manual testing for complex UI elements

## Migration Guide

When migrating existing code to use the new UI component system:

1. **Identify UI Elements**: Identify distinct UI elements in your code
2. **Map to Components**: Determine which component types match these elements
3. **Create Adapter**: Create an adapter to connect APIs with components
4. **Replace Rendering**: Replace direct rendering with component rendering
5. **Add Fallbacks**: Ensure backward compatibility with fallback rendering

## Conclusion

The UI component system provides a powerful, flexible way to build consistent user interfaces across different platforms. By following these guidelines, you can create maintainable, extensible UIs that can easily adapt to changing requirements.