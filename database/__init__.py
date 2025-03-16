"""
Database module for SkillLab
Provides database connection and repositories
"""

from .core import DatabaseConnection, BaseRepository
from .metrics_db import MetricsRepository
from .review_db import ReviewRepository
from .sync import sync_databases

# Initialize global instances
_metrics_repository = None
_review_repository = None

def get_metrics_repository() -> MetricsRepository:
    """
    Get metrics repository instance
    
    Returns:
        Metrics repository
    """
    global _metrics_repository
    
    if _metrics_repository is None:
        _metrics_repository = MetricsRepository()
    
    return _metrics_repository

def get_review_repository() -> ReviewRepository:
    """
    Get review repository instance
    
    Returns:
        Review repository
    """
    global _review_repository
    
    if _review_repository is None:
        _review_repository = ReviewRepository()
    
    return _review_repository

__all__ = [
    "DatabaseConnection", 
    "BaseRepository", 
    "MetricsRepository",
    "ReviewRepository",
    "get_metrics_repository",
    "get_review_repository",
    "sync_databases"
]