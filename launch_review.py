#!/usr/bin/env python
"""
Launch script for SkillLab Review Dashboard
Starts the Streamlit web interface for document review
"""

import os
import sys
import subprocess
from pathlib import Path

# Ensure we're in the project root
project_root = Path(__file__).parent
os.chdir(project_root)

def main():
    """Launch the Streamlit app"""
    print("Launching SkillLab Review Dashboard...")
    
    # Run database sync first
    print("Synchronizing databases...")
    try:
        # Import the sync utility
        sys.path.append(str(project_root))
        from utils.db_sync import sync_databases
        
        # Run sync
        docs, issues = sync_databases()
        print(f"Sync complete. Synced {docs} documents and {issues} issues.")
    except Exception as e:
        print(f"Warning: Database sync failed: {str(e)}")
    
    # Launch Streamlit app
    streamlit_cmd = [
        "streamlit", "run", 
        os.path.join("review", "app.py"),
        "--browser.serverAddress", "localhost",
        "--server.port", "8501",
        "--theme.base", "dark"
    ]
    
    try:
        subprocess.run(streamlit_cmd)
    except KeyboardInterrupt:
        print("\nShutting down review dashboard...")
    except Exception as e:
        print(f"Error launching dashboard: {str(e)}")
        print("\nTo manually launch the dashboard, run:")
        print("streamlit run review/app.py")
        
        # Check if streamlit is installed
        try:
            import streamlit
            print("\nStreamlit is installed. Version:", streamlit.__version__)
        except ImportError:
            print("\nError: Streamlit is not installed. Install with:")
            print("pip install streamlit")
            return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())