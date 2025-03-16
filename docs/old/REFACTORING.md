# SkillLab Project Refactoring Plan

## Overview

This document outlines a comprehensive refactoring plan for the SkillLab project to improve code organization, maintainability, and separation of concerns. The project extracts structured data from resumes using OCR and AI techniques.

## Current Structure

The current project structure:

- **extraction/**: OCR and JSON generation
- **training/**: Dataset creation and model training
- **monitor/**: CLI dashboard and metrics collection
- **review/**: Web-based human review interface
- **utils/**: Shared utilities
- **data/**: Input/output files
- **models/**: Trained models
- **main.py**: Core pipeline orchestration
- **cli.py**: Command line interface

## Refactoring Goals

1. **Consolidate Database Management**
2. **Standardize Configuration**
3. **Separate UI Components**
4. **Implement Pipeline Architecture**
5. **Add Testing Structure**
6. **Centralize Schema Definitions**
7. **Create API Layer**

## Detailed Implementation Plan

### Consolidate Database Management

**Problem**: Database logic is scattered across `review/db_manager.py`, `monitor/metrics.py`, and `utils/db_sync.py`.

**Solution**:
1. Create a `database/` directory
2. Implement:
   - `database/core.py` - Base database functionality ✅
   - `database/metrics_db.py` - Metrics operations ✅
   - `database/review_db.py` - Review operations ❌
   - `database/sync.py` - Synchronization utilities ❌
3. Add a database migration system using Alembic

**Migration Steps**:
1. Create the new files with identical functionality
2. Add deprecation warnings to old files
3. Update imports one module at a time
4. Run integration tests after each module update

### Standardize Configuration

**Problem**: Configuration is duplicated between `main.py` and `cli.py` with different approaches.

**Solution**:
1. Create a `config/` directory
2. Implement:
   - `config/default.yaml` - Default configuration ✅
   - `config/loader.py` - Configuration management ✅
   - `config/schema.py` - Configuration validation ✅
3. Support both YAML files and environment variables

**Migration Steps**:
1. Extract all configuration parameters from code
2. Create default configuration file
3. Implement configuration loader
4. Update `main.py` and `cli.py` to use new configuration system
5. Add backward compatibility for command-line arguments

### Separate UI Components

**Problem**: UI code mixes with business logic in both dashboards.

**Solution**:
1. Create a `ui/` directory
2. Implement:
   - `ui/cli/` - CLI dashboard components ✅
   - `ui/web/` - Web dashboard components ✅
   - `ui/common/` - Shared components ✅
3. Keep UI-specific logic separate from data processing

**Migration Steps**:
1. Identify UI-specific code in current implementations
2. Create new UI modules with identical functionality
3. Update launcher scripts to use new locations
4. Ensure UI only accesses data through well-defined interfaces

### Implement Pipeline Architecture

**Problem**: Pipeline steps are tightly coupled and have inconsistent interfaces.

**Solution**:
1. Create a `pipeline/` directory
2. Implement:
   - `pipeline/base.py` - Define step interface ✅
   - `pipeline/executor.py` - Pipeline execution logic ✅
   - `pipeline/steps/` - Individual step implementations ✅
3. Use consistent input/output format between steps

**Migration Steps**:
1. Define common step interface
2. Convert existing functions to pipeline steps one by one
3. Create pipeline executor to replace logic in `main.py`
4. Add appropriate logging and error handling
5. Update CLI to use new pipeline

### Add Testing Structure

**Problem**: Lack of comprehensive testing structure.

**Solution**:
1. Create a `tests/` directory mirroring the main structure
2. Implement:
   - `tests/unit/` - Unit tests by component ✅
   - `tests/integration/` - End-to-end tests
   - `tests/fixtures/` - Test data ❌
   - `tests/conftest.py` - Test configuration ✅
3. Add CI configuration for automated testing

**Migration Steps**:
1. Set up testing framework and utilities
2. Start with high-level integration tests
3. Add unit tests for each new refactored component
4. Create fixtures for sample data and mocks

### Centralize Schema Definitions

**Problem**: Data schemas are embedded in code rather than centralized.

**Solution**:
1. Create a `schemas/` directory
2. Implement:
   - `schemas/resume.json` - Resume JSON schema ✅
   - `schemas/metrics.json` - Metrics schema ✅
   - `schemas/validation.py` - Schema validation utilities ✅
3. Use schemas for validation throughout the codebase

**Migration Steps**:
1. Extract schema definitions from current code
2. Create JSON Schema files for each data type
3. Implement validation utilities
4. Update code to use centralized schemas
5. Add schema versioning support

### Create API Layer

**Problem**: Business logic mixed with CLI interface.

**Solution**:
1. Create an `api/` directory
2. Implement:
   - `api/extraction.py` - Extraction operations ✅
   - `api/training.py` - Training operations ❌
   - `api/review.py` - Review operations ❌
   - `api/monitoring.py` - Monitoring operations ❌
3. Make CLI a thin wrapper around the API

**Migration Steps**:
1. Extract core functions from CLI to API modules
2. Add appropriate error handling and parameter validation
3. Update CLI to call API functions
4. Ensure backward compatibility for existing scripts

## Implementation Order

To minimize disruption, implement in this order:
1. Schema Definitions (lowest risk)
2. Testing Structure (provides safety net)
3. Configuration System (foundation)
4. Database Management (core infrastructure)
5. Pipeline Architecture (core processing logic)
6. API Layer (interface to core functionality)
7. UI Separation (final polish)

## Best Practices

During refactoring:
1. Create one pull request per refactoring step
2. Use feature flags to enable/disable new implementations
3. Run tests after each change
4. Document new interfaces as you develop them
5. Maintain backward compatibility where possible
6. Deploy and test in staging before production

## Task Tracking

Create JIRA/GitHub issues for each refactoring task with:
1. Detailed description of changes
2. Migration plan for dependent code
3. Testing requirements
4. Definition of done
5. Backward compatibility considerations

## Conclusion

This refactoring will significantly improve the maintainability and scalability of the SkillLab project. By systematically addressing each architectural issue while maintaining backward compatibility, we can gradually transform the code base with minimal disruption to ongoing development.
