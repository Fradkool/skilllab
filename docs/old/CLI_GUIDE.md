# SkillLab CLI Guide

This document provides an overview of the SkillLab command-line interface, including both the main CLI commands and the new UI commands.

## Installation

The SkillLab CLI is installed automatically when you install the package:

```bash
pip install -e .
```

This will install the `skilllab` command (with `sl` as an alias) that you can use from anywhere.

## Basic Usage

```bash
# Show help
skilllab --help

# Show version
skilllab version
```

## Pipeline Commands

These commands run the core SkillLab pipeline functions:

### Run Full Pipeline

```bash
# Run the full pipeline
skilllab run --input-dir /path/to/input --output-dir /path/to/output

# Run with limit
skilllab run --input-dir /path/to/input --limit 10

# Run specific steps
skilllab run --start ocr --end json

# Run training with custom parameters
skilllab run --end training --epochs 10 --batch-size 8 --gpu-monitor
```

### Run Individual Steps

```bash
# OCR extraction only
skilllab extract --input-dir /path/to/resumes

# Generate JSON from OCR results
skilllab structure --input-dir /path/to/ocr_results

# Train model
skilllab train --dataset-dir /path/to/dataset --epochs 10
```

## UI Commands

SkillLab provides a unified interface for launching various UI components. The new UI commands provide a consistent way to launch different interfaces with the same pattern.

### Launch UI Components

```bash
# Launch the main dashboard (web interface)
skilllab ui dashboard

# Launch monitoring dashboard (CLI interface by default)
skilllab ui monitor

# Launch monitoring dashboard as web interface
skilllab ui monitor --ui-type web

# Launch review interface
skilllab ui review

# Launch training interface
skilllab ui training

# Launch extraction interface
skilllab ui extraction
```

### UI Command Options

All UI commands support the following options:

- `--ui-type`: Choose between `cli` or `web` interfaces
- `--port`: Specify the port for web interfaces (default: 8501)
- `--no-browser`: Don't open a browser window automatically

For example:

```bash
# Launch web training UI on port 8888 without opening browser
skilllab ui training --ui-type web --port 8888 --no-browser
```

### Legacy Commands

For backward compatibility, the following commands are still supported:

```bash
# Launch monitoring dashboard
skilllab monitor

# Launch review interface
skilllab review

# Show review queue status
skilllab review status

# List documents in review queue
skilllab review list --filter low_ocr_confidence --limit 10
```

## Direct UI Launchers

You can also use the launcher scripts directly:

```bash
# Launch monitoring dashboard
python launch_monitor.py [--ui-type cli|web]

# Launch review interface
python launch_review.py

# Launch training interface
python launch_training.py [--ui-type cli|web]

# Launch any UI using the central launcher
python launch_ui.py [dashboard|monitor|review|training|extraction] [options]
```

## Environment Variables

SkillLab respects the following environment variables:

- `SKILLLAB_CONFIG`: Path to custom configuration file
- `SKILLLAB_LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `SKILLLAB_INPUT_DIR`: Default input directory
- `SKILLLAB_OUTPUT_DIR`: Default output directory
- `SKILLLAB_MODEL_DIR`: Default model directory

## Examples

Here are some common usage examples:

```bash
# Process a batch of resumes and launch the review interface
skilllab run --input-dir /path/to/resumes --end json
skilllab ui review

# Monitor processing in real-time
skilllab run --input-dir /path/to/resumes &
skilllab ui monitor

# Train a new model and monitor progress
skilllab ui training --ui-type web
```

## Troubleshooting

If you encounter any issues with the CLI:

1. Check your configuration file (`config/default.yaml`)
2. Ensure all dependencies are installed
3. Check the log files in the `logs/` directory
4. Try running with the `--help` option to see available commands and options

For more help, see the full documentation or open an issue on GitHub.