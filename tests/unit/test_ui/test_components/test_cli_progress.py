"""
Tests for CLI Progress Component
"""

import pytest
from unittest.mock import MagicMock, patch

import sys
from io import StringIO
from ui.cli.components.progress import CLIProgressComponent

class TestCLIProgressComponent:
    """Tests for CLIProgressComponent"""
    
    def test_init(self):
        """Test initialization"""
        # Create component
        component = CLIProgressComponent("test_progress", "Test Progress")
        
        # Verify initialization
        assert component.name == "test_progress"
        assert component.description == "Test Progress"
        assert component.current == 0
        assert component.total == 0
        assert component.message == ""
    
    def test_update(self):
        """Test updating progress"""
        # Create component
        component = CLIProgressComponent("test_progress", "Test Progress")
        
        # Update progress
        component.update(5, 10, "Processing...")
        
        # Verify state
        assert component.current == 5
        assert component.total == 10
        assert component.message == "Processing..."
    
    def test_complete(self):
        """Test completing progress"""
        # Create component
        component = CLIProgressComponent("test_progress", "Test Progress")
        
        # Set initial state
        component.update(5, 10, "Processing...")
        
        # Complete progress
        component.complete("Finished!")
        
        # Verify state
        assert component.current == 10
        assert component.total == 10
        assert component.message == "Finished!"
    
    def test_render_with_data_parameter(self):
        """Test rendering with data parameter"""
        # Capture stdout
        old_stdout = sys.stdout
        captured_output = StringIO()
        sys.stdout = captured_output
        
        try:
            # Create component
            component = CLIProgressComponent("test_progress", "Test Progress")
            
            # Create data
            data = {
                "current": 7,
                "total": 15,
                "message": "Working..."
            }
            
            # Render with data
            component.render(data)
            
            # Get output
            output = captured_output.getvalue()
            
            # Verify output
            assert "Test Progress" in output
            assert "Working..." in output
            assert "7/15" in output
            assert "46.7%" in output
            
            # Check state
            assert component.current == 7
            assert component.total == 15
            assert component.message == "Working..."
        
        finally:
            # Restore stdout
            sys.stdout = old_stdout
    
    def test_render_with_pre_set_data(self):
        """Test rendering with pre-set data"""
        # Capture stdout
        old_stdout = sys.stdout
        captured_output = StringIO()
        sys.stdout = captured_output
        
        try:
            # Create component
            component = CLIProgressComponent("test_progress", "Test Progress")
            
            # Set progress
            component.update(3, 10, "Running...")
            
            # Render
            component.render()
            
            # Get output
            output = captured_output.getvalue()
            
            # Verify output
            assert "Test Progress" in output
            assert "Running..." in output
            assert "3/10" in output
            assert "30.0%" in output
        
        finally:
            # Restore stdout
            sys.stdout = old_stdout
    
    def test_render_empty(self):
        """Test rendering with no data"""
        # Capture stdout
        old_stdout = sys.stdout
        captured_output = StringIO()
        sys.stdout = captured_output
        
        try:
            # Create component
            component = CLIProgressComponent("test_progress", "Test Progress")
            
            # Render empty component
            component.render()
            
            # Get output
            output = captured_output.getvalue()
            
            # Verify output
            assert "Test Progress" in output
            assert "0/0" in output
            assert "0.0%" in output
        
        finally:
            # Restore stdout
            sys.stdout = old_stdout