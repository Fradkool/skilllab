#!/usr/bin/env python
"""
SkillLab UI Launcher
Central launcher for all SkillLab UI components
"""

import os
import sys
import subprocess
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from ui.common.factory import UIType
from ui.common.manager import UIManager, UIMode
from utils.logger import setup_logger
from api.monitoring import initialize_monitoring_system
from database.sync import sync_databases

# Setup logger
logger = setup_logger("launch_ui")

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="SkillLab UI Launcher")
    parser.add_argument("mode", type=str, choices=["dashboard", "monitor", "review", "training", "extraction"], 
                       help="UI mode to launch")
    parser.add_argument("--ui-type", type=str, choices=["cli", "web"], default="web", help="UI type to use")
    parser.add_argument("--sync", action="store_true", help="Sync databases before launching")
    parser.add_argument("--port", type=int, default=8501, help="Port for web interface")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser")
    args = parser.parse_args()
    
    # Determine UI type
    ui_type = UIType.WEB if args.ui_type.lower() == "web" else UIType.CLI
    
    # Determine UI mode
    mode_map = {
        "dashboard": UIMode.DASHBOARD,
        "monitor": UIMode.MONITOR,
        "review": UIMode.REVIEW,
        "training": UIMode.TRAINING,
        "extraction": UIMode.EXTRACTION
    }
    ui_mode = mode_map[args.mode]
    
    logger.info(f"Launching SkillLab {args.mode} with {ui_type.value} interface")
    
    # Sync databases if requested
    if args.sync:
        try:
            logger.info("Synchronizing databases...")
            docs, issues = sync_databases()
            logger.info(f"Sync complete. Synced {docs} documents and {issues} issues.")
        except Exception as e:
            logger.error(f"Warning: Database sync failed: {str(e)}")
    
    # Initialize monitoring for all UIs
    try:
        initialize_monitoring_system(enabled=True)
    except Exception as e:
        logger.error(f"Warning: Monitoring system initialization failed: {str(e)}")
    
    # Launch UI based on type
    if ui_type == UIType.WEB:
        # For web UIs, we launch streamlit with the appropriate app
        if args.mode == "monitor":
            script_path = os.path.join(project_root, "launch_monitor.py")
            cmd = [sys.executable, script_path, "--ui-type", "web"]
        elif args.mode == "review":
            script_path = os.path.join(project_root, "launch_review.py")
            cmd = [
                "streamlit", "run", script_path,
                "--browser.serverAddress", "localhost",
                "--server.port", str(args.port),
                "--theme.base", "dark"
            ]
        elif args.mode == "training":
            script_path = os.path.join(project_root, "launch_training.py")
            cmd = [sys.executable, script_path, "--ui-type", "web"]
        else:
            # Use the central web app for dashboard and extraction
            script_path = os.path.join(project_root, "ui", "web", "web_app.py")
            cmd = [
                "streamlit", "run", script_path,
                "--browser.serverAddress", "localhost",
                "--server.port", str(args.port),
                "--theme.base", "dark"
            ]
        
        # Add no-browser flag if requested
        if args.no_browser:
            cmd.extend(["--server.headless", "true"])
        
        # Launch web UI
        try:
            subprocess.run(cmd)
            return 0
        except KeyboardInterrupt:
            logger.info("UI stopped by user")
            return 0
        except Exception as e:
            logger.error(f"Error launching UI: {str(e)}")
            return 1
    else:
        # For CLI UIs, we use the UI manager directly
        ui_manager = UIManager(UIType.CLI)
        ui_manager.set_mode(ui_mode)
        
        try:
            ui_manager.render_ui()
            return 0
        except KeyboardInterrupt:
            logger.info("UI stopped by user")
            return 0
        except Exception as e:
            logger.error(f"Error rendering UI: {str(e)}")
            return 1

if __name__ == "__main__":
    sys.exit(main())