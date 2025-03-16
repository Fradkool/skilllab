#!/usr/bin/env python
"""
SkillLab Monitoring Dashboard Launcher
Launches the monitoring dashboard using the UI component system
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from monitor.dashboard import MonitorDashboard
from ui.common.factory import UIType
from utils.logger import setup_logger
from api.monitoring import initialize_monitoring_system, shutdown_monitoring_system

# Setup logger
logger = setup_logger("launch_monitor")

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="SkillLab Monitoring Dashboard")
    parser.add_argument("--ui-type", type=str, choices=["cli", "web"], default="cli", help="UI type to use")
    parser.add_argument("--log-file", type=str, help="Path to log file")
    parser.add_argument("--db-file", type=str, help="Path to database file")
    args = parser.parse_args()
    
    # Determine UI type
    ui_type = UIType.WEB if args.ui_type.lower() == "web" else UIType.CLI
    
    logger.info(f"Starting monitoring dashboard with {ui_type.value} interface")
    
    try:
        # Initialize the monitoring system
        initialize_monitoring_system(enabled=True)
        
        # Create and run dashboard
        dashboard = MonitorDashboard(
            log_file=args.log_file,
            db_file=args.db_file,
            ui_type=ui_type
        )
        dashboard.run()
        
        # Shutdown cleanly when done
        shutdown_monitoring_system()
        return 0
    except KeyboardInterrupt:
        logger.info("Dashboard stopped by user")
        # Shutdown cleanly
        shutdown_monitoring_system()
        return 0
    except Exception as e:
        logger.error(f"Error running dashboard: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())