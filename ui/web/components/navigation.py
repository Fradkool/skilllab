"""
Web navigation component implementation
"""

from typing import Dict, List, Any, Optional, Callable
import streamlit as st

from ui.base import NavComponent

class WebNavComponent(NavComponent):
    """Web implementation of navigation component using Streamlit"""
    
    def __init__(self, name: str = "navigation", description: str = "Navigation component"):
        """Initialize web navigation component"""
        super().__init__(name, description)
        self.active_id = None
        self.callback = None
    
    def render(self, data: Any = None) -> None:
        """
        Render the navigation component
        
        Args:
            data: Navigation data (dict with items and options)
        """
        if data:
            if "items" in data:
                self.items = []
                for item in data["items"]:
                    self.add_item(
                        item_id=item.get("id", ""),
                        label=item.get("label", ""),
                        url=item.get("url"),
                        action=item.get("action"),
                        parent=item.get("parent")
                    )
            
            if "active_id" in data:
                self.active_id = data["active_id"]
            
            if "callback" in data:
                self.callback = data["callback"]
        
        # Group items by parent
        root_items = [item for item in self.items if item["parent"] is None]
        child_groups = {}
        
        for item in self.items:
            if item["parent"] is not None:
                if item["parent"] not in child_groups:
                    child_groups[item["parent"]] = []
                child_groups[item["parent"]].append(item)
        
        # Display as sidebar menu
        for item in root_items:
            item_id = item["id"]
            label = item["label"]
            
            # Check if item has children
            has_children = item_id in child_groups
            
            if has_children:
                # Create expandable section
                with st.sidebar.expander(label, item_id == self.active_id):
                    for child in child_groups[item_id]:
                        child_id = child["id"]
                        child_label = child["label"]
                        
                        # Create button for child item
                        if st.button(
                            child_label,
                            key=f"nav_{child_id}",
                            use_container_width=True,
                            type="primary" if child_id == self.active_id else "secondary"
                        ):
                            self.active_id = child_id
                            self._trigger_callback(child_id)
            else:
                # Create button for root item
                if st.sidebar.button(
                    label,
                    key=f"nav_{item_id}",
                    use_container_width=True,
                    type="primary" if item_id == self.active_id else "secondary"
                ):
                    self.active_id = item_id
                    self._trigger_callback(item_id)
    
    def _trigger_callback(self, item_id: str) -> None:
        """
        Trigger callback when navigation item is selected
        
        Args:
            item_id: Item identifier
        """
        if self.callback is not None:
            self.callback(item_id)
    
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
        self.items.append({
            "id": item_id,
            "label": label,
            "url": url,
            "action": action,
            "parent": parent
        })
    
    def set_active(self, item_id: str) -> None:
        """
        Set active navigation item
        
        Args:
            item_id: Item identifier
        """
        self.active_id = item_id