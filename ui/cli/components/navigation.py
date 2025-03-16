"""
CLI navigation component implementation
"""

from typing import Dict, List, Any, Optional, Callable

from ui.base import NavComponent

class CLINavComponent(NavComponent):
    """CLI implementation of navigation component"""
    
    def __init__(self, name: str = "navigation", description: str = "Navigation component"):
        """Initialize CLI navigation component"""
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
        
        if not self.items:
            print(f"{self.description}: No navigation items defined")
            return
        
        # Group items by parent
        root_items = [item for item in self.items if item["parent"] is None]
        child_groups = {}
        
        for item in self.items:
            if item["parent"] is not None:
                if item["parent"] not in child_groups:
                    child_groups[item["parent"]] = []
                child_groups[item["parent"]].append(item)
        
        # Display navigation menu
        print(f"\n{self.description}:")
        
        # Display root items
        for i, item in enumerate(root_items):
            item_id = item["id"]
            label = item["label"]
            active = "*" if item_id == self.active_id else " "
            
            # Check if item has children
            has_children = item_id in child_groups
            
            if has_children:
                print(f"  {i+1}. {active} {label}")
                
                # Display children
                for j, child in enumerate(child_groups[item_id]):
                    child_id = child["id"]
                    child_label = child["label"]
                    child_active = "*" if child_id == self.active_id else " "
                    
                    print(f"    {i+1}.{j+1}. {child_active} {child_label}")
            else:
                print(f"  {i+1}. {active} {label}")
        
        # Get user input
        try:
            choice = input("\n  Select option: ")
            
            # Parse choice
            if "." in choice:
                # Handle child selection
                parts = choice.split(".")
                if len(parts) == 2:
                    try:
                        root_index = int(parts[0]) - 1
                        child_index = int(parts[1]) - 1
                        
                        if 0 <= root_index < len(root_items):
                            root_item = root_items[root_index]
                            root_id = root_item["id"]
                            
                            if root_id in child_groups and 0 <= child_index < len(child_groups[root_id]):
                                selected_item = child_groups[root_id][child_index]
                                self.active_id = selected_item["id"]
                                self._trigger_callback(self.active_id)
                    except ValueError:
                        print("  Invalid selection")
            else:
                # Handle root selection
                try:
                    root_index = int(choice) - 1
                    
                    if 0 <= root_index < len(root_items):
                        selected_item = root_items[root_index]
                        self.active_id = selected_item["id"]
                        self._trigger_callback(self.active_id)
                except ValueError:
                    print("  Invalid selection")
        except KeyboardInterrupt:
            print("\n  Navigation cancelled")
    
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