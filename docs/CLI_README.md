# SkillLab CLI Reference

This document provides a reference for using the SkillLab command-line interface, which has been modernized to use the Click framework and provide a consistent, user-friendly experience.

## Installation

1. Make sure you have installed the required dependencies:
   ```
   pip install click
   ```

2. Run the setup script to create command aliases:
   ```
   bash setup_cli.sh
   ```

## Command Structure

SkillLab CLI uses a hierarchical command structure with primary command groups and subcommands.

### Basic Usage

```
skilllab [command-group] [command] [options]
```

Alias: `sl` can be used instead of `skilllab`.

### Getting Help

All commands have built-in help that can be accessed with the `-h` or `--help` flag:

```
skilllab --help
skilllab run --help
skilllab run pipeline --help
```

## Command Groups

### Run Commands

Commands for running SkillLab processing pipelines:

- `skilllab run pipeline`: Run the full SkillLab pipeline
  ```
  skilllab run pipeline --input-dir ~/resumes --output-dir ~/output --model-dir ~/models
  ```

- `skilllab run extract`: Run OCR extraction only
  ```
  skilllab run extract --input-dir ~/resumes --output-dir ~/output --limit 10
  ```

- `skilllab run structure`: Run JSON generation and correction
  ```
  skilllab run structure --input-dir ~/ocr_results --output-dir ~/output
  ```

- `skilllab run train`: Run model training
  ```
  skilllab run train --dataset-dir ~/dataset --model-dir ~/models --epochs 10
  ```

### UI Commands

Commands for launching user interfaces:

- `skilllab ui dashboard`: Launch main dashboard
  ```
  skilllab ui dashboard --ui-type web --port 8501
  ```

- `skilllab ui monitor`: Launch monitoring dashboard
  ```
  skilllab ui monitor --ui-type cli
  ```

- `skilllab ui review`: Launch review interface
  ```
  skilllab ui review --ui-type web --sync
  ```

- `skilllab ui training`: Launch training interface
  ```
  skilllab ui training --ui-type web
  ```

- `skilllab ui extraction`: Launch extraction interface
  ```
  skilllab ui extraction --ui-type web
  ```

### Review Commands

Commands for document review operations:

- `skilllab review web`: Launch web review interface
  ```
  skilllab review web --port 8502
  ```

- `skilllab review status`: Show review queue status
  ```
  skilllab review status
  ```

- `skilllab review list`: List documents in review queue
  ```
  skilllab review list --filter low_ocr_confidence --limit 50
  ```

- `skilllab review sync`: Synchronize review databases
  ```
  skilllab review sync
  ```

### Monitor Commands

Commands for monitoring operations:

- `skilllab monitor status`: Show monitoring status
  ```
  skilllab monitor status
  ```

- `skilllab monitor dashboard`: Launch monitoring dashboard
  ```
  skilllab monitor dashboard --ui-type cli
  ```

- `skilllab monitor metrics`: Show performance metrics
  ```
  skilllab monitor metrics --range week --type resource
  ```

### Training Commands

Commands for training operations:

- `skilllab training list-models`: List available models
  ```
  skilllab training list-models
  ```

- `skilllab training dataset-info`: Show dataset information
  ```
  skilllab training dataset-info --dataset-dir ~/dataset
  ```

- `skilllab training web`: Launch training web interface
  ```
  skilllab training web
  ```

### Health Commands

Commands for health check operations:

- `skilllab health check`: Run health checks on the system
  ```
  skilllab health check --all
  ```

## Common Options

Many commands share common options:

- `--ui-type`: Type of UI to use (`cli` or `web`)
- `--port`: Port for web interface (default: 8501)
- `--no-browser`: Don't open browser when launching web interfaces
- `--limit`: Limit number of items to process or display
- `--input-dir`, `--output-dir`: Input and output directories

## Examples

### Running the Full Pipeline

```bash
# Run the entire pipeline from OCR to training
skilllab run pipeline --input-dir ~/resumes --end training

# Run only extraction and JSON generation
skilllab run pipeline --input-dir ~/resumes --end json
```

### Reviewing Documents

```bash
# Show review queue status
skilllab review status

# List documents with specific issues
skilllab review list --filter missing_contact

# Launch web review interface
skilllab review web
```

### Monitoring

```bash
# Check system status and resources
skilllab monitor status

# View performance metrics for the last week
skilllab monitor metrics --range week
```

### Training

```bash
# List available models
skilllab training list-models

# Run training with custom parameters
skilllab run train --epochs 20 --batch-size 8 --gpu-monitor
```

## Configuration

The CLI uses the centralized configuration system. Default values for directories, database locations, and other settings are read from the configuration files in the `config/` directory.