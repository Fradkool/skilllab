"""
CLI form component implementation
"""

from typing import Dict, List, Any, Optional, Tuple, Callable

from ui.base import FormComponent

class CLIFormComponent(FormComponent):
    """CLI implementation of form component"""
    
    def __init__(self, name: str = "form", description: str = "Input form"):
        """Initialize CLI form component"""
        super().__init__(name, description)
        self.submitted = False
    
    def render(self, data: Any = None) -> None:
        """
        Render the form component
        
        Args:
            data: Form data
        """
        if data:
            if "fields" in data:
                for field_id, field_info in data["fields"].items():
                    self.add_field(
                        field_id=field_id,
                        field_type=field_info.get("type", "text"),
                        label=field_info.get("label", field_id),
                        required=field_info.get("required", False),
                        default=field_info.get("default"),
                        options=field_info.get("options")
                    )
            
            if "values" in data:
                self.set_values(data["values"])
        
        if not self.fields:
            print(f"{self.description}: No fields defined")
            return
        
        print(f"\n{self.description}:")
        
        # Collect values for each field
        for field_id, field_info in self.fields.items():
            field_type = field_info["type"]
            label = field_info["label"]
            required = field_info["required"]
            default = field_info.get("default")
            options = field_info.get("options", [])
            
            # Display required indicator
            display_label = f"{label} *" if required else label
            
            current_value = self.values.get(field_id, default)
            
            # Create field based on type
            if field_type == "text":
                # Get input with default
                input_prompt = f"  {display_label} [{current_value}]: " if current_value else f"  {display_label}: "
                value = input(input_prompt)
                
                # Use default if no input
                if not value and current_value is not None:
                    value = current_value
                
                self.values[field_id] = value
            elif field_type == "number":
                # Get input with default
                input_prompt = f"  {display_label} [{current_value}]: " if current_value is not None else f"  {display_label}: "
                value = input(input_prompt)
                
                # Use default if no input
                if not value and current_value is not None:
                    value = current_value
                else:
                    try:
                        value = float(value)
                    except ValueError:
                        print(f"    Invalid number, using default {current_value}")
                        value = current_value
                
                self.values[field_id] = value
            elif field_type == "boolean":
                # Get input with default
                default_str = "Y/n" if current_value else "y/N"
                input_prompt = f"  {display_label} [{default_str}]: "
                value = input(input_prompt).lower()
                
                # Parse boolean
                if not value:
                    value = current_value
                else:
                    value = value.lower() in ("y", "yes", "true", "1")
                
                self.values[field_id] = value
            elif field_type == "select":
                # Display options
                print(f"  {display_label}:")
                for i, option in enumerate(options):
                    selected = " (current)" if option == current_value else ""
                    print(f"    {i+1}. {option}{selected}")
                
                # Get input
                input_prompt = f"  Select option [1-{len(options)}]: "
                try:
                    choice = int(input(input_prompt))
                    if 1 <= choice <= len(options):
                        self.values[field_id] = options[choice-1]
                    elif current_value is not None:
                        self.values[field_id] = current_value
                except (ValueError, IndexError):
                    print(f"    Invalid choice, using default {current_value}")
                    self.values[field_id] = current_value
            else:
                print(f"    Field type '{field_type}' not supported in CLI")
        
        # Confirm submission
        submit = input("\n  Submit form? [Y/n]: ").lower()
        if not submit or submit.lower() in ("y", "yes", "true", "1"):
            self.submitted = True
            print("  Form submitted")
        else:
            self.submitted = False
            print("  Form cancelled")
    
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
        self.fields[field_id] = {
            "type": field_type,
            "label": label,
            "required": required,
            "default": default,
            "options": options or []
        }
    
    def get_values(self) -> Dict[str, Any]:
        """
        Get form values
        
        Returns:
            Dictionary with form values
        """
        return self.values
    
    def set_values(self, values: Dict[str, Any]) -> None:
        """
        Set form values
        
        Args:
            values: Dictionary with form values
        """
        self.values = values.copy()
    
    def validate(self) -> Tuple[bool, List[str]]:
        """
        Validate form values
        
        Returns:
            Tuple of (is_valid, error_messages)
        """
        is_valid = True
        error_messages = []
        
        # Check required fields
        for field_id, field_info in self.fields.items():
            if field_info["required"]:
                if field_id not in self.values or self.values[field_id] in (None, ""):
                    is_valid = False
                    error_messages.append(f"Field '{field_info['label']}' is required")
        
        # Print validation errors
        if not is_valid:
            print("Validation errors:")
            for error in error_messages:
                print(f"  - {error}")
        
        return is_valid, error_messages
    
    def is_submitted(self) -> bool:
        """
        Check if form was submitted
        
        Returns:
            True if form was submitted, False otherwise
        """
        return self.submitted