"""
API module for SkillLab
Provides high-level interface to SkillLab functionality
"""

# Import API functions
from .extraction import (
    extract_text_from_pdf,
    batch_extract_text,
    generate_json_from_text,
    batch_generate_json,
    validate_and_correct_json,
    run_full_extraction_pipeline
)

from .training import (
    build_training_dataset,
    train_donut_model,
    evaluate_model,
    run_training_pipeline,
    get_training_progress,
    get_available_models,
    get_dataset_metadata,
    get_training_history,
    export_model,
    delete_model
)

from .review import (
    get_review_queue,
    get_document_details,
    update_document_status,
    save_review_feedback,
    get_dashboard_stats,
    get_review_history,
    get_performance_stats,
    get_error_analysis, 
    get_improvement_metrics,
    approve_document,
    reject_document,
    save_document_json,
    load_documents_from_filesystem,
    sync_review_data,
    recycle_for_training
)

from .monitoring import (
    initialize_monitoring_system,
    shutdown_monitoring_system,
    get_system_resources,
    start_resource_monitoring,
    stop_resource_monitoring,
    get_pipeline_progress,
    get_performance_metrics,
    get_recent_activity,
    get_document_processing_stats,
    record_custom_metric
)

from .health import (
    get_health_api
)

__all__ = [
    # Extraction API
    "extract_text_from_pdf",
    "batch_extract_text",
    "generate_json_from_text",
    "batch_generate_json",
    "validate_and_correct_json",
    "run_full_extraction_pipeline",
    
    # Training API
    "build_training_dataset",
    "train_donut_model",
    "evaluate_model",
    "run_training_pipeline",
    "get_training_progress",
    "get_available_models",
    "get_dataset_metadata",
    "get_training_history",
    "export_model",
    "delete_model",
    
    # Review API
    "get_review_queue",
    "get_document_details",
    "update_document_status",
    "save_review_feedback",
    "get_dashboard_stats",
    "get_review_history",
    "get_performance_stats",
    "get_error_analysis",
    "get_improvement_metrics",
    "approve_document",
    "reject_document",
    "save_document_json",
    "load_documents_from_filesystem",
    "sync_review_data",
    "recycle_for_training",
    
    # Monitoring API
    "initialize_monitoring_system",
    "shutdown_monitoring_system",
    "get_system_resources",
    "start_resource_monitoring",
    "stop_resource_monitoring",
    "get_pipeline_progress",
    "get_performance_metrics",
    "get_recent_activity",
    "get_document_processing_stats",
    "record_custom_metric",
    
    # Health API
    "get_health_api"
]