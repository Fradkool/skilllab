#!/usr/bin/env python
"""
SkillLab Web Dashboard
Web interface for SkillLab monitoring and management using Streamlit
"""

import os
import sys
import time
import streamlit as st
from enum import Enum
from typing import Dict, Any, Optional

# Add project root to path
from pathlib import Path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from ui.common.factory import UIType
from ui.common.manager import UIManager, UIMode
from config import get_config

def main():
    """Main entry point for Streamlit app"""
    # Configure page
    st.set_page_config(
        page_title="SkillLab Dashboard",
        page_icon="📋",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Get configuration
    config = get_config()
    
    # Initialize UI manager if not in session state
    if 'ui_manager' not in st.session_state:
        st.session_state.ui_manager = UIManager(UIType.WEB)
    
    # Set up sidebar navigation
    st.sidebar.title("SkillLab Dashboard")
    
    # Add mode selection in sidebar
    mode = st.sidebar.radio(
        "Navigation",
        ["Dashboard", "Monitor", "Review", "Training", "Extraction"]
    )
    
    # Update UI mode based on selection
    if mode == "Dashboard":
        st.session_state.ui_manager.set_mode(UIMode.DASHBOARD)
    elif mode == "Monitor":
        st.session_state.ui_manager.set_mode(UIMode.MONITOR)
    elif mode == "Review":
        st.session_state.ui_manager.set_mode(UIMode.REVIEW)
    elif mode == "Training":
        st.session_state.ui_manager.set_mode(UIMode.TRAINING)
    elif mode == "Extraction":
        st.session_state.ui_manager.set_mode(UIMode.EXTRACTION)
    
    # Add refresh button
    if st.sidebar.button("Refresh Data"):
        st.experimental_rerun()
    
    # Render UI
    st.session_state.ui_manager.render_ui()
    
    # Add footer
    st.sidebar.markdown("---")
    st.sidebar.markdown("© SkillLab 2023")

if __name__ == "__main__":
    main()