"""
Tests for Web Table Component
"""

import pytest
from unittest.mock import MagicMock, patch

import streamlit as st
from ui.web.components.table import WebTableComponent

class TestWebTableComponent:
    """Tests for WebTableComponent"""
    
    def test_init(self):
        """Test initialization"""
        # Create component
        component = WebTableComponent("test_table", "Test Table")
        
        # Verify initialization
        assert component.name == "test_table"
        assert component.description == "Test Table"
        assert component.headers == []
        assert component.rows == []
    
    def test_set_headers(self):
        """Test setting headers"""
        # Create component
        component = WebTableComponent("test_table", "Test Table")
        
        # Set headers
        headers = ["Column 1", "Column 2", "Column 3"]
        component.set_headers(headers)
        
        # Verify headers
        assert component.headers == headers
    
    def test_add_row(self):
        """Test adding a row"""
        # Create component
        component = WebTableComponent("test_table", "Test Table")
        
        # Set headers
        headers = ["Column 1", "Column 2", "Column 3"]
        component.set_headers(headers)
        
        # Add a row
        row = ["Value 1", "Value 2", "Value 3"]
        component.add_row(row)
        
        # Verify row
        assert component.rows == [row]
        
        # Add another row
        row2 = ["Value 4", "Value 5", "Value 6"]
        component.add_row(row2)
        
        # Verify rows
        assert component.rows == [row, row2]
    
    def test_render_with_data_parameter(self):
        """Test rendering with data parameter"""
        # Mock streamlit
        with patch('ui.web.components.table.st') as mock_st:
            # Create component
            component = WebTableComponent("test_table", "Test Table")
            
            # Create data
            data = {
                "headers": ["Column 1", "Column 2", "Column 3"],
                "rows": [
                    ["Value 1", "Value 2", "Value 3"],
                    ["Value 4", "Value 5", "Value 6"]
                ]
            }
            
            # Render with data
            component.render(data)
            
            # Verify streamlit calls
            assert mock_st.subheader.call_count == 1
            assert mock_st.subheader.call_args[0][0] == "Test Table"
            
            # Check that dataframe was called
            mock_st.dataframe.assert_called_once()
            
            # Verify dataframe data
            df_arg = mock_st.dataframe.call_args[0][0]
            assert list(df_arg.columns) == data["headers"]
            assert list(df_arg.values[0]) == data["rows"][0]
            assert list(df_arg.values[1]) == data["rows"][1]
    
    def test_render_with_set_data(self):
        """Test rendering with pre-set data"""
        # Mock streamlit
        with patch('ui.web.components.table.st') as mock_st:
            # Create component
            component = WebTableComponent("test_table", "Test Table")
            
            # Set headers and rows
            component.set_headers(["Column 1", "Column 2", "Column 3"])
            component.add_row(["Value 1", "Value 2", "Value 3"])
            component.add_row(["Value 4", "Value 5", "Value 6"])
            
            # Render
            component.render()
            
            # Verify streamlit calls
            assert mock_st.subheader.call_count == 1
            assert mock_st.subheader.call_args[0][0] == "Test Table"
            
            # Check that dataframe was called
            mock_st.dataframe.assert_called_once()
            
            # Verify dataframe data
            df_arg = mock_st.dataframe.call_args[0][0]
            assert list(df_arg.columns) == ["Column 1", "Column 2", "Column 3"]
            assert list(df_arg.values[0]) == ["Value 1", "Value 2", "Value 3"]
            assert list(df_arg.values[1]) == ["Value 4", "Value 5", "Value 6"]
    
    def test_render_empty(self):
        """Test rendering with no data"""
        # Mock streamlit
        with patch('ui.web.components.table.st') as mock_st:
            # Create component
            component = WebTableComponent("test_table", "Test Table")
            
            # Render empty component
            component.render()
            
            # Verify streamlit calls
            assert mock_st.subheader.call_count == 1
            assert mock_st.subheader.call_args[0][0] == "Test Table"
            
            # Should display info message
            mock_st.info.assert_called_once()
            assert "No data" in mock_st.info.call_args[0][0]