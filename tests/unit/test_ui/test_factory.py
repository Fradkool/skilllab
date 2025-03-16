"""
Tests for UI component factory
"""

import pytest
from unittest.mock import MagicMock, patch

from ui.common.factory import UIComponentFactory, UIType
from ui.base import UIComponent

class TestUIComponentFactory:
    """Tests for UIComponentFactory"""
    
    def test_create_component_cli(self):
        """Test creating a CLI component"""
        # Create mock components
        with patch('ui.common.factory.CLITableComponent') as mock_cli_table:
            # Configure mock
            mock_cli_table.return_value = MagicMock()
            
            # Call the factory method
            component = UIComponentFactory.create_component(
                "table", UIType.CLI, "test_table", "Test Table"
            )
            
            # Verify the component was created correctly
            assert component is not None
            mock_cli_table.assert_called_once_with(
                name="test_table", description="Test Table"
            )
    
    def test_create_component_web(self):
        """Test creating a web component"""
        # Create mock components
        with patch('ui.common.factory.WebChartComponent') as mock_web_chart:
            # Configure mock
            mock_web_chart.return_value = MagicMock()
            
            # Call the factory method
            component = UIComponentFactory.create_component(
                "chart", UIType.WEB, "test_chart", "Test Chart"
            )
            
            # Verify the component was created correctly
            assert component is not None
            mock_web_chart.assert_called_once_with(
                name="test_chart", description="Test Chart"
            )
    
    def test_create_component_invalid_type(self):
        """Test creating a component with invalid UI type"""
        # Call the factory method with invalid UI type
        component = UIComponentFactory.create_component(
            "table", "invalid_type", "test_table", "Test Table"
        )
        
        # Verify the component was not created
        assert component is None
    
    def test_create_component_invalid_component(self):
        """Test creating a component with invalid component type"""
        # Call the factory method with invalid component type
        component = UIComponentFactory.create_component(
            "invalid_component", UIType.CLI, "test_component", "Test Component"
        )
        
        # Verify the component was not created
        assert component is None
    
    def test_register_component(self):
        """Test registering a custom component"""
        # Create a mock component class
        mock_component_class = MagicMock()
        
        # Register the component
        UIComponentFactory.register_component(
            "custom_component", UIType.CLI, mock_component_class
        )
        
        # Try to create the custom component
        with patch.object(mock_component_class, '__call__', return_value=MagicMock()) as mock_call:
            component = UIComponentFactory.create_component(
                "custom_component", UIType.CLI, "test_custom", "Test Custom"
            )
            
            # Verify the component was created correctly
            assert component is not None
            mock_call.assert_called_once_with(
                name="test_custom", description="Test Custom"
            )
        
        # Clean up - remove the custom component
        UIComponentFactory._component_map[UIType.CLI].pop("custom_component", None)
    
    def test_register_component_new_ui_type(self):
        """Test registering a component with a new UI type"""
        # Create a mock component class
        mock_component_class = MagicMock()
        
        # Create a new UI type
        new_ui_type = "new_type"
        
        # Register the component
        UIComponentFactory.register_component(
            "custom_component", new_ui_type, mock_component_class
        )
        
        # Verify the new UI type was added to the component map
        assert new_ui_type in UIComponentFactory._component_map
        assert "custom_component" in UIComponentFactory._component_map[new_ui_type]
        assert UIComponentFactory._component_map[new_ui_type]["custom_component"] == mock_component_class
        
        # Clean up - remove the new UI type
        UIComponentFactory._component_map.pop(new_ui_type, None)