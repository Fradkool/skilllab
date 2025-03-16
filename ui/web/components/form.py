"""
Web form component implementation
"""

from datetime import datetime, date, time
from typing import Dict, List, Any, Optional, Tuple, Callable
import streamlit as st

from ui.base import FormComponent

class WebFormComponent(FormComponent):
    """Web implementation of form component using Streamlit"""
    
    def __init__(self, name: str = "form", description: str = "Input form"):
        """Initialize web form component"""
        super().__init__(name, description)
        self.form_key = f"form_{name}_{id(self)}"
        self.submit_label = "Submit"
        self.show_reset = True
        self.reset_label = "Reset"
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
            
            if "submit_label" in data:
                self.submit_label = data["submit_label"]
            
            if "show_reset" in data:
                self.show_reset = data["show_reset"]
            
            if "reset_label" in data:
                self.reset_label = data["reset_label"]
        
        with st.form(key=self.form_key):
            if self.description:
                st.markdown(f"### {self.description}")
            
            # Render each field
            for field_id, field_info in self.fields.items():
                field_type = field_info["type"]
                label = field_info["label"]
                required = field_info["required"]
                default = field_info.get("default")
                options = field_info.get("options", [])
                
                # Display required indicator
                display_label = f"{label} *" if required else label
                
                # Create field based on type
                if field_type == "text":
                    current_value = self.values.get(field_id, default or "")
                    self.values[field_id] = st.text_input(
                        display_label,
                        value=current_value
                    )
                elif field_type == "textarea":
                    current_value = self.values.get(field_id, default or "")
                    self.values[field_id] = st.text_area(
                        display_label,
                        value=current_value
                    )
                elif field_type == "number":
                    current_value = self.values.get(field_id, default or 0)
                    self.values[field_id] = st.number_input(
                        display_label,
                        value=float(current_value)
                    )
                elif field_type == "password":
                    current_value = self.values.get(field_id, default or "")
                    self.values[field_id] = st.text_input(
                        display_label,
                        value=current_value,
                        type="password"
                    )
                elif field_type == "boolean":
                    current_value = self.values.get(field_id, default or False)
                    self.values[field_id] = st.checkbox(
                        display_label,
                        value=current_value
                    )
                elif field_type == "select":
                    current_value = self.values.get(field_id, default)
                    # Find index of default value
                    index = 0
                    if current_value in options:
                        index = options.index(current_value)
                    
                    self.values[field_id] = st.selectbox(
                        display_label,
                        options=options,
                        index=index
                    )
                elif field_type == "multiselect":
                    current_value = self.values.get(field_id, default or [])
                    self.values[field_id] = st.multiselect(
                        display_label,
                        options=options,
                        default=current_value
                    )
                elif field_type == "slider":
                    min_value = field_info.get("min", 0)
                    max_value = field_info.get("max", 100)
                    step = field_info.get("step", 1)
                    current_value = self.values.get(field_id, default or min_value)
                    
                    self.values[field_id] = st.slider(
                        display_label,
                        min_value=min_value,
                        max_value=max_value,
                        value=current_value,
                        step=step
                    )
                elif field_type == "date":
                    if default is None:
                        default = date.today()
                    elif isinstance(default, str):
                        try:
                            default = datetime.strptime(default, "%Y-%m-%d").date()
                        except ValueError:
                            default = date.today()
                    
                    current_value = self.values.get(field_id, default)
                    
                    self.values[field_id] = st.date_input(
                        display_label,
                        value=current_value
                    )
                elif field_type == "time":
                    if default is None:
                        default = time(0, 0)
                    elif isinstance(default, str):
                        try:
                            default = datetime.strptime(default, "%H:%M").time()
                        except ValueError:
                            default = time(0, 0)
                    
                    current_value = self.values.get(field_id, default)
                    
                    self.values[field_id] = st.time_input(
                        display_label,
                        value=current_value
                    )
                elif field_type == "file":
                    self.values[field_id] = st.file_uploader(
                        display_label,
                        type=field_info.get("file_types", None),
                        accept_multiple_files=field_info.get("multiple", False)
                    )
                elif field_type == "color":
                    current_value = self.values.get(field_id, default or "#FFFFFF")
                    self.values[field_id] = st.color_picker(
                        display_label,
                        value=current_value
                    )
                else:
                    st.warning(f"Unknown field type: {field_type}")
            
            # Add buttons
            col1, col2 = st.columns([1, 1])
            
            with col1:
                submit_button = st.form_submit_button(label=self.submit_label)
            
            with col2:
                if self.show_reset:
                    reset_button = st.form_submit_button(label=self.reset_label)
                    if reset_button:
                        self.values = {}
                        st.rerun()  # Force re-render
            
            self.submitted = submit_button
    
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
        
        return is_valid, error_messages
    
    def is_submitted(self) -> bool:
        """
        Check if form was submitted
        
        Returns:
            True if form was submitted, False otherwise
        """
        return self.submitted