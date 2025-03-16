#!/usr/bin/env python
"""
SkillLab CLI Dashboard
Command-line interface for SkillLab monitoring and management
"""

import os
import sys
import time
import argparse
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

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="SkillLab CLI Dashboard",
        epilog="Interactive CLI dashboard for SkillLab"
    )
    
    parser.add_argument(
        "--mode",
        choices=["dashboard", "monitor", "review", "training", "extraction"],
        default="dashboard",
        help="Dashboard mode to display"
    )
    
    return parser.parse_args()

def main():
    """Main entry point"""
    # Parse arguments
    args = parse_args()
    
    # Get configuration
    config = get_config()
    
    # Initialize UI manager
    ui_manager = UIManager(UIType.CLI)
    
    # Set mode based on arguments
    if args.mode == "dashboard":
        ui_manager.set_mode(UIMode.DASHBOARD)
    elif args.mode == "monitor":
        ui_manager.set_mode(UIMode.MONITOR)
    elif args.mode == "review":
        ui_manager.set_mode(UIMode.REVIEW)
    elif args.mode == "training":
        ui_manager.set_mode(UIMode.TRAINING)
    elif args.mode == "extraction":
        ui_manager.set_mode(UIMode.EXTRACTION)
    
    # Render UI
    ui_manager.render_ui()
    
    # Keep alive for user interaction (if needed)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)

if __name__ == "__main__":
    main()