# SkillLab Documentation

This directory contains comprehensive documentation for the SkillLab project.

## Core Documentation

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | System architecture, design patterns, and component interactions |
| [INSTALLATION.md](INSTALLATION.md) | Detailed installation instructions for all environments |
| [CLI_README.md](CLI_README.md) | Command-line interface reference and examples |
| [API.md](API.md) | API reference for programmatic integration |
| [UI.md](UI.md) | UI system overview and component reference |
| [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md) | Docker containerization setup and management |

## Additional Resources

- [Main README](../README.md) - Project overview and quick start guide
- [REFACTORING_STATUS.md](REFACTORING_STATUS.md) - Historical record of refactoring progress

## Documentation Diagrams

The documentation includes several diagrams to visualize the system architecture:

```
            ┌─────────────┐     ┌─────────────┐
            │    CLI UI   │     │    Web UI   │
            └──────┬──────┘     └──────┬──────┘
                   │                   │
                   ▼                   ▼
            ┌─────────────────────────────────┐
            │           API Layer             │
            └─┬─────────────┬────────────────┬┘
              │             │                │
    ┌─────────▼──────┐ ┌────▼─────┐  ┌───────▼───────┐
    │ Database Layer │ │ Pipeline │  │ Training Layer│
    └─┬──────────────┘ └────┬─────┘  └───────────────┘
      │                     │
┌─────▼─────┐      ┌────────┼───────┬───────────┐
│ Metrics DB│      │        │       │           │
└───────────┘      ▼        ▼       ▼           ▼
              ┌─────────┐ ┌─────┐ ┌─────┐ ┌──────────┐
              │   OCR   │ │ LLM │ │Auto │ │  Review  │
              │ Extract │ │ JSON│ │Corr.│ │ Interface│
              └────┬────┘ └──┬──┘ └─────┘ └──────────┘
                   │         │
                   ▼         ▼
              ┌─────────┐ ┌─────────┐
              │PaddleOCR│ │ Ollama  │
              │Container│ │Container│
              └─────────┘ └─────────┘
```

## Getting Started

If you're new to SkillLab, start with these resources:

1. [Installation Guide](INSTALLATION.md) - Set up SkillLab on your system
2. [Main README](../README.md) - Learn the basics of SkillLab
3. [CLI Reference](CLI_README.md) - Start using the command-line interface

## Contributing to Documentation

When contributing to the documentation:

1. Use Markdown formatting for all documents
2. Include code examples where applicable
3. Use ASCII diagrams or Mermaid syntax for visualizations
4. Follow the established structure and style
5. Update the main README.md when adding new documentation