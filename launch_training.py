#!/usr/bin/env python
"""
SkillLab Training UI Launcher
Launches the training UI for model training
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from training.ui import TrainingUI
from ui.common.factory import UIType
from utils.logger import setup_logger

# Setup logger
logger = setup_logger("launch_training")

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="SkillLab Training UI")
    parser.add_argument("--ui-type", type=str, choices=["cli", "web"], default="cli", help="UI type to use")
    args = parser.parse_args()
    
    # Determine UI type
    ui_type = UIType.WEB if args.ui_type.lower() == "web" else UIType.CLI
    
    logger.info(f"Starting training UI with {ui_type.value} interface")
    
    # Create and run training UI
    training_ui = TrainingUI(ui_type=ui_type)
    training_ui.initialize_ui()
    training_ui.render()

if __name__ == "__main__":
    main()