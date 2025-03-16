"""
Tests for UI manager
"""

import pytest
from unittest.mock import MagicMock, patch, call

from ui.common.manager import UIManager, UIMode, UIType

class TestUIManager:
    """Tests for UIManager"""
    
    def test_init(self):
        """Test initialization"""
        # Create mock adapters
        with patch('ui.common.manager.MonitoringAdapter') as mock_monitoring_adapter, \
             patch('ui.common.manager.ReviewAdapter') as mock_review_adapter, \
             patch('ui.common.manager.TrainingAdapter') as mock_training_adapter, \
             patch('ui.common.manager.UIComponentFactory.create_component') as mock_create_component:
            
            # Configure mocks
            mock_monitoring_adapter.return_value = MagicMock()
            mock_review_adapter.return_value = MagicMock()
            mock_training_adapter.return_value = MagicMock()
            mock_create_component.return_value = MagicMock()
            
            # Create manager
            manager = UIManager(UIType.CLI)
            
            # Verify initialization
            assert manager.ui_type == UIType.CLI
            assert manager.current_mode == UIMode.DASHBOARD
            assert manager.monitoring_adapter is mock_monitoring_adapter.return_value
            assert manager.review_adapter is mock_review_adapter.return_value
            assert manager.training_adapter is mock_training_adapter.return_value
            assert manager.main_nav is mock_create_component.return_value
            
            # Verify adapter initialization
            mock_monitoring_adapter.assert_called_once_with(UIType.CLI)
            mock_review_adapter.assert_called_once_with(UIType.CLI)
            mock_training_adapter.assert_called_once_with(UIType.CLI)
            
            # Verify navigation setup
            mock_create_component.assert_called_once_with(
                "navigation", UIType.CLI, "main_navigation", "SkillLab Navigation"
            )
            assert manager.main_nav.add_item.call_count >= 5
            assert manager.main_nav.set_active.call_count == 1
    
    def test_set_mode(self):
        """Test setting UI mode"""
        # Create mock adapters
        with patch('ui.common.manager.MonitoringAdapter') as mock_monitoring_adapter, \
             patch('ui.common.manager.ReviewAdapter') as mock_review_adapter, \
             patch('ui.common.manager.TrainingAdapter') as mock_training_adapter, \
             patch('ui.common.manager.UIComponentFactory.create_component') as mock_create_component:
            
            # Configure mocks
            mock_monitoring_adapter.return_value = MagicMock()
            mock_review_adapter.return_value = MagicMock()
            mock_training_adapter.return_value = MagicMock()
            nav_mock = MagicMock()
            mock_create_component.return_value = nav_mock
            
            # Create manager
            manager = UIManager(UIType.WEB)
            
            # Initial mode should be dashboard
            assert manager.current_mode == UIMode.DASHBOARD
            
            # Set mode to monitor
            manager.set_mode(UIMode.MONITOR)
            
            # Verify mode change
            assert manager.current_mode == UIMode.MONITOR
            nav_mock.set_active.assert_called_with("monitor")
    
    def test_render_ui_dashboard(self):
        """Test rendering dashboard UI"""
        # Create mock adapters and components
        with patch('ui.common.manager.MonitoringAdapter') as mock_monitoring_adapter, \
             patch('ui.common.manager.ReviewAdapter') as mock_review_adapter, \
             patch('ui.common.manager.TrainingAdapter') as mock_training_adapter, \
             patch('ui.common.manager.UIComponentFactory.create_component') as mock_create_component, \
             patch('ui.common.manager.UIManager._render_dashboard') as mock_render_dashboard:
            
            # Configure mocks
            mock_monitoring_adapter.return_value = MagicMock()
            mock_review_adapter.return_value = MagicMock()
            mock_training_adapter.return_value = MagicMock()
            nav_mock = MagicMock()
            mock_create_component.return_value = nav_mock
            
            # Create manager
            manager = UIManager(UIType.CLI)
            
            # Render UI
            manager.render_ui()
            
            # Verify navigation rendered
            nav_mock.render.assert_called_once()
            
            # Verify dashboard rendered
            mock_render_dashboard.assert_called_once()
    
    def test_render_ui_monitor(self):
        """Test rendering monitor UI"""
        # Create mock adapters and components
        with patch('ui.common.manager.MonitoringAdapter') as mock_monitoring_adapter, \
             patch('ui.common.manager.ReviewAdapter') as mock_review_adapter, \
             patch('ui.common.manager.TrainingAdapter') as mock_training_adapter, \
             patch('ui.common.manager.UIComponentFactory.create_component') as mock_create_component:
            
            # Configure mocks
            monitoring_adapter_mock = MagicMock()
            dashboard_mock = MagicMock()
            monitoring_adapter_mock.get_dashboard.return_value = dashboard_mock
            
            mock_monitoring_adapter.return_value = monitoring_adapter_mock
            mock_review_adapter.return_value = MagicMock()
            mock_training_adapter.return_value = MagicMock()
            nav_mock = MagicMock()
            mock_create_component.return_value = nav_mock
            
            # Create manager
            manager = UIManager(UIType.CLI)
            
            # Set mode to monitor
            manager.set_mode(UIMode.MONITOR)
            
            # Render UI
            manager.render_ui()
            
            # Verify navigation rendered
            nav_mock.render.assert_called_once()
            
            # Verify monitoring adapter used
            monitoring_adapter_mock.refresh.assert_called_once()
            monitoring_adapter_mock.get_dashboard.assert_called_once()
            dashboard_mock.render.assert_called_once()
    
    def test_render_ui_review(self):
        """Test rendering review UI"""
        # Create mock adapters and components
        with patch('ui.common.manager.MonitoringAdapter') as mock_monitoring_adapter, \
             patch('ui.common.manager.ReviewAdapter') as mock_review_adapter, \
             patch('ui.common.manager.TrainingAdapter') as mock_training_adapter, \
             patch('ui.common.manager.UIComponentFactory.create_component') as mock_create_component:
            
            # Configure mocks
            review_adapter_mock = MagicMock()
            dashboard_mock = MagicMock()
            review_adapter_mock.get_dashboard.return_value = dashboard_mock
            
            mock_monitoring_adapter.return_value = MagicMock()
            mock_review_adapter.return_value = review_adapter_mock
            mock_training_adapter.return_value = MagicMock()
            nav_mock = MagicMock()
            mock_create_component.return_value = nav_mock
            
            # Create manager
            manager = UIManager(UIType.WEB)
            
            # Set mode to review
            manager.set_mode(UIMode.REVIEW)
            
            # Render UI
            manager.render_ui()
            
            # Verify navigation rendered
            nav_mock.render.assert_called_once()
            
            # Verify review adapter used
            review_adapter_mock.refresh.assert_called_once()
            review_adapter_mock.get_dashboard.assert_called_once()
            dashboard_mock.render.assert_called_once()
    
    def test_render_ui_training(self):
        """Test rendering training UI"""
        # Create mock adapters and components
        with patch('ui.common.manager.MonitoringAdapter') as mock_monitoring_adapter, \
             patch('ui.common.manager.ReviewAdapter') as mock_review_adapter, \
             patch('ui.common.manager.TrainingAdapter') as mock_training_adapter, \
             patch('ui.common.manager.UIComponentFactory.create_component') as mock_create_component:
            
            # Configure mocks
            training_adapter_mock = MagicMock()
            dashboard_mock = MagicMock()
            training_adapter_mock.get_dashboard.return_value = dashboard_mock
            
            mock_monitoring_adapter.return_value = MagicMock()
            mock_review_adapter.return_value = MagicMock()
            mock_training_adapter.return_value = training_adapter_mock
            nav_mock = MagicMock()
            mock_create_component.return_value = nav_mock
            
            # Create manager
            manager = UIManager(UIType.CLI)
            
            # Set mode to training
            manager.set_mode(UIMode.TRAINING)
            
            # Render UI
            manager.render_ui()
            
            # Verify navigation rendered
            nav_mock.render.assert_called_once()
            
            # Verify training adapter used
            training_adapter_mock.refresh.assert_called_once()
            training_adapter_mock.get_dashboard.assert_called_once()
            dashboard_mock.render.assert_called_once()
    
    def test_get_ui_manager_singleton(self):
        """Test getting UI manager singleton"""
        # Create mock adapters
        with patch('ui.common.manager.MonitoringAdapter') as mock_monitoring_adapter, \
             patch('ui.common.manager.ReviewAdapter') as mock_review_adapter, \
             patch('ui.common.manager.TrainingAdapter') as mock_training_adapter, \
             patch('ui.common.manager.UIComponentFactory.create_component') as mock_create_component:
            
            # Configure mocks
            mock_monitoring_adapter.return_value = MagicMock()
            mock_review_adapter.return_value = MagicMock()
            mock_training_adapter.return_value = MagicMock()
            mock_create_component.return_value = MagicMock()
            
            # Clear existing singletons
            from ui.common.manager import _cli_manager, _web_manager
            import ui.common.manager
            ui.common.manager._cli_manager = None
            ui.common.manager._web_manager = None
            
            # Get CLI manager
            from ui.common.manager import get_ui_manager
            cli_manager = get_ui_manager(UIType.CLI)
            
            # Get it again - should be the same instance
            cli_manager2 = get_ui_manager(UIType.CLI)
            assert cli_manager is cli_manager2
            
            # Get web manager
            web_manager = get_ui_manager(UIType.WEB)
            
            # Get it again - should be the same instance
            web_manager2 = get_ui_manager(UIType.WEB)
            assert web_manager is web_manager2
            
            # CLI and web managers should be different
            assert cli_manager is not web_manager