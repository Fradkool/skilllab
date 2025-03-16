# SkillLab UI System Guide

This document provides a comprehensive guide to the SkillLab UI component system, covering both CLI and web interfaces.

## UI System Architecture

SkillLab uses a modular UI architecture with these key components:

```
ui/
├── base.py             # Abstract base classes and interfaces
├── common/             # Shared utilities and patterns
│   ├── factory.py      # Component factory
│   ├── adapter.py      # API adapters
│   └── manager.py      # UI manager
├── cli/                # CLI interface components
│   ├── components/     # CLI-specific component implementations
│   └── cli_app.py      # CLI application
└── web/                # Web interface components
    ├── components/     # Web-specific component implementations
    └── web_app.py      # Web application
```

## Design Patterns

The UI system uses several design patterns:

### Factory Pattern

The UI component factory (`ui/common/factory.py`) creates UI components based on the requested UI type:

```python
factory = UIComponentFactory(UIType.CLI)  # or UIType.WEB
dashboard = factory.create_dashboard()
```

### Adapter Pattern

Adapters (`ui/common/adapter.py`) connect UI components to the API, handling data conversion and interaction:

```python
adapter = MonitoringAdapter(UIType.CLI)
adapter.update_resources(resources_data)
```

### Strategy Pattern

Different UI implementations (CLI vs. web) provide the same functionality through different strategies:

```python
# CLI implementation
class CLIProgressBar(ProgressBar):
    def render(self) -> None:
        # Render using ASCII characters

# Web implementation
class WebProgressBar(ProgressBar):
    def render(self) -> None:
        # Render using Streamlit components
```

## Component Types

The UI system includes these core component types:

1. **Dashboard**: Overall UI container
2. **Alert**: Notification messages
3. **Chart**: Data visualization
4. **Form**: Input collection
5. **Navigation**: Menu and navigation
6. **Progress**: Progress indicators
7. **Table**: Tabular data display

Each component has a base interface and implementations for both CLI and web.

## CLI Interface

The CLI interface uses terminal-based components for interactive display:

- Text-based progress bars
- ASCII charts
- Tabular data with formatting
- Keyboard navigation

### CLI Components

```python
from ui.cli.components import (
    CLIDashboard,
    CLIAlert,
    CLIChart,
    CLIForm,
    CLINavigation,
    CLIProgress,
    CLITable
)
```

### Example: CLI Dashboard

```python
from ui.cli.components import CLIDashboard

dashboard = CLIDashboard()
dashboard.add_title("SkillLab Monitor")
dashboard.add_section("Resource Usage")
dashboard.add_chart(cpu_data, title="CPU Usage")
dashboard.render()
```

## Web Interface

The web interface uses Streamlit for interactive web-based display:

- Interactive charts
- Rich form controls
- Dynamic updates
- File uploads

### Web Components

```python
from ui.web.components import (
    WebDashboard,
    WebAlert,
    WebChart,
    WebForm,
    WebNavigation,
    WebProgress,
    WebTable
)
```

### Example: Web Dashboard

```python
from ui.web.components import WebDashboard

dashboard = WebDashboard()
dashboard.add_title("SkillLab Monitor")
dashboard.add_section("Resource Usage")
dashboard.add_chart(cpu_data, title="CPU Usage")
dashboard.render()
```

## UI Manager

The UI manager (`ui/common/manager.py`) provides a high-level interface for working with UI components:

```python
# Create a UI manager for CLI
manager = UIManager(UIType.CLI)

# Set the UI mode
manager.set_mode(UIMode.MONITOR)

# Render the UI
manager.render_ui()
```

## UI Workflows

### 1. Monitoring Workflow

The monitoring UI displays:
- System resource usage
- Pipeline progress
- Document processing metrics
- Recent activity log

```python
# Create monitoring adapter
adapter = MonitoringAdapter(UIType.CLI)

# Update with latest data
adapter.update_resources(get_system_resources())
adapter.update_pipeline_progress(get_pipeline_progress())
adapter.update_document_stats(get_document_processing_stats())

# Render the dashboard
dashboard = adapter.get_dashboard()
dashboard.render()
```

### 2. Review Workflow

The review UI provides:
- Document queue listing
- Individual document review
- Correction interface
- Approval/rejection

```python
# Create review adapter
adapter = ReviewAdapter(UIType.WEB)

# Get document queue
documents = adapter.get_review_queue()

# Display queue
table = adapter.create_document_table(documents)
table.render()

# Show document details
if selected_doc:
    details = adapter.get_document_details(selected_doc)
    adapter.display_document(details)
```

### 3. Training Workflow

The training UI shows:
- Model selection
- Training configuration
- Progress monitoring
- Results visualization

```python
# Create training adapter
adapter = TrainingAdapter(UIType.WEB)

# Configure training
form = adapter.create_training_form()
config = form.get_values()

# Start training
adapter.start_training(config)

# Monitor progress
progress = adapter.get_training_progress()
progress_bar = adapter.create_progress_bar(progress)
progress_bar.render()
```

## UI Launchers

SkillLab includes launcher scripts for different UI modes:

- `launch_ui.py`: Central UI launcher
- `launch_monitor.py`: Monitoring dashboard launcher
- `launch_review.py`: Review interface launcher
- `launch_training.py`: Training interface launcher

### Launching UIs

From the command line:
```bash
# Launch monitoring dashboard (CLI)
skilllab ui monitor --ui-type cli

# Launch review interface (Web)
skilllab ui review --ui-type web --port 8502

# Launch training interface (Web)
skilllab ui training --ui-type web
```

From Python:
```python
from ui.common.manager import UIManager, UIMode
from ui.common.factory import UIType

# Create manager
manager = UIManager(UIType.CLI)
manager.set_mode(UIMode.MONITOR)

# Render UI
manager.render_ui()
```

## Creating Custom UI Components

You can create custom UI components by extending the base classes:

```python
from ui.base import Component, Dashboard
from ui.cli.components import CLIComponent

class CustomCLIComponent(CLIComponent):
    def __init__(self, title: str):
        super().__init__()
        self.title = title
        
    def render(self) -> None:
        print(f"=== {self.title} ===")
        # Custom rendering logic
```

## UI Configuration

UI behavior can be configured in `config/default.yaml`:

```yaml
ui:
  theme: 'dark'
  refresh_interval: 5
  animation: true
  cli:
    colors: true
    unicode: true
  web:
    port: 8501
    theme: 'dark'
    show_sidebar: true
```

## Extending the UI System

To add a new UI type:

1. Create a new enum value in `UIType`
2. Implement component classes for the new UI type
3. Update the factory to handle the new UI type
4. Create adapters for the new UI type

## Conclusion

The SkillLab UI system provides a flexible, extensible framework for both CLI and web interfaces. By separating interface from implementation and using consistent design patterns, the system enables multiple UI options while maintaining consistent functionality and user experience.