# SkillLab UI Components

This directory contains the UI components for the SkillLab application, designed to support both CLI and web interfaces.

## Directory Structure

```
ui/
├── __init__.py              # Package entrypoint, exports UIComponentFactory and UIType
├── base.py                  # Abstract base classes for all UI components
├── README.md                # This file
├── cli/                     # CLI-specific implementations
│   ├── __init__.py          # Exports CLI components
│   ├── cli_app.py           # CLI application entry point
│   ├── components/          # Individual CLI component implementations
│   │   ├── __init__.py
│   │   ├── alert.py         # CLI alert component
│   │   ├── chart.py         # CLI chart component
│   │   ├── dashboard.py     # CLI dashboard component
│   │   ├── form.py          # CLI form component
│   │   ├── navigation.py    # CLI navigation component
│   │   ├── progress.py      # CLI progress component
│   │   └── table.py         # CLI table component
├── common/                  # Shared components
│   ├── __init__.py
│   ├── adapter.py           # Adapters to connect API with UI components
│   ├── factory.py           # Factory for creating UI components
│   └── manager.py           # Manager for handling UI operations
└── web/                     # Web-specific implementations
    ├── __init__.py          # Exports web components
    ├── exports.py           # Exports UI module components
    ├── web_app.py           # Web application entry point (Streamlit)
    └── components/          # Individual web component implementations
        ├── __init__.py
        ├── alert.py         # Web alert component using Streamlit
        ├── chart.py         # Web chart component using Streamlit
        ├── dashboard.py     # Web dashboard component using Streamlit
        ├── form.py          # Web form component using Streamlit
        ├── navigation.py    # Web navigation component using Streamlit
        ├── progress.py      # Web progress component using Streamlit
        └── table.py         # Web table component using Streamlit
```

## Architecture

The UI components follow a component-based architecture with these key features:

1. **Abstraction**: All components inherit from abstract base classes defined in `base.py`
2. **Factory Pattern**: The `UIComponentFactory` enables creation of the appropriate component based on UI type
3. **Adapter Pattern**: Adapters connect API functionality with UI components
4. **Dependency Injection**: Components receive configuration and data through their interfaces

## Usage

### Creating UI Components

```python
from ui import UIComponentFactory, UIType

# Create a CLI progress component
progress = UIComponentFactory.create_component(
    component_type="progress",
    ui_type=UIType.CLI,
    name="download_progress",
    description="Download Progress"
)

# Create a web table component
table = UIComponentFactory.create_component(
    component_type="table",
    ui_type=UIType.WEB,
    name="results_table",
    description="Results Table"
)
```

### Using Adapters

```python
from ui.common.adapter import MonitoringAdapter
from ui import UIType

# Create monitoring adapter for CLI interface
cli_monitor = MonitoringAdapter(UIType.CLI)

# Refresh dashboard with latest API data
cli_monitor.refresh()

# Get dashboard component
dashboard = cli_monitor.get_dashboard()

# Render dashboard
dashboard.render()
```

## Development

When adding new UI components:

1. Create a new class that inherits from the appropriate base class in `base.py`
2. Implement all abstract methods
3. Add the component to the appropriate module and export it
4. Register the component in the factory if needed

All components should follow the same interface pattern, where rendering and data updates are clearly separated.