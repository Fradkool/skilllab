"""
SkillLab Review Module
Provides human review interface for flagged documents
"""

__version__ = "0.1.0"

def run_app():
    """Launch the Streamlit review app"""
    from .app import main
    main()