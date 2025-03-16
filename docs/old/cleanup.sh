#!/bin/bash
# Script to clean up documentation directory

echo "Cleaning up SkillLab documentation directory..."

# Files to keep (these won't be touched)
KEEP_FILES=(
  "ARCHITECTURE.md"
  "CLI_README.md"
  "DOCKER_DEPLOYMENT.md"
  "INSTALLATION.md"
  "API.md"
  "REFACTORING_STATUS.md"
  "UI.md"
)

# Create backup directory
BACKUP_DIR="obsolete_docs_backup"
mkdir -p "$BACKUP_DIR"
echo "Created backup directory: $BACKUP_DIR"

# Move obsolete files to backup
for file in *.md; do
  # Skip files we want to keep
  skip=false
  for keep in "${KEEP_FILES[@]}"; do
    if [ "$file" = "$keep" ]; then
      skip=true
      break
    fi
  done
  
  if [ "$skip" = false ]; then
    echo "Moving $file to $BACKUP_DIR/"
    mv "$file" "$BACKUP_DIR/"
  fi
done

echo "Documentation cleanup complete."
echo "Kept files: ${KEEP_FILES[*]}"
echo "Obsolete files moved to: $BACKUP_DIR/"