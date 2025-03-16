#!/bin/bash
# Setup script for SkillLab CLI

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Create symbolic links to the CLI script in a directory that's in the user's PATH
# Try several common locations, starting with the most preferred
if [ -d "$HOME/.local/bin" ]; then
    echo "Creating symbolic link in $HOME/.local/bin"
    ln -sf "$SCRIPT_DIR/cli.py" "$HOME/.local/bin/skilllab"
    ln -sf "$SCRIPT_DIR/cli.py" "$HOME/.local/bin/sl"
    chmod +x "$SCRIPT_DIR/cli.py"
    echo "Done! You can now use 'skilllab' or 'sl' commands."
elif [ -d "$HOME/bin" ]; then
    echo "Creating symbolic link in $HOME/bin"
    ln -sf "$SCRIPT_DIR/cli.py" "$HOME/bin/skilllab"
    ln -sf "$SCRIPT_DIR/cli.py" "$HOME/bin/sl"
    chmod +x "$SCRIPT_DIR/cli.py"
    echo "Done! You can now use 'skilllab' or 'sl' commands."
else
    echo "Could not find a suitable directory in your PATH."
    echo "You can manually create symbolic links to $SCRIPT_DIR/cli.py"
    echo "Example: sudo ln -sf $SCRIPT_DIR/cli.py /usr/local/bin/skilllab"
    echo "Example: sudo ln -sf $SCRIPT_DIR/cli.py /usr/local/bin/sl"
fi

# Make sure the CLI script is executable
chmod +x "$SCRIPT_DIR/cli.py"

echo "Install required dependency:"
echo "pip install click"

# Remind the user to install click if not already installed
if ! python3 -c "import click" &> /dev/null; then
    echo "The 'click' package is required. Please install it with:"
    echo "pip install click"
fi

echo "CLI setup complete!"