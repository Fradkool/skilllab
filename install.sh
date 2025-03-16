#!/bin/bash
#
# SkillLab Installation Script
# This script sets up the SkillLab environment, including dependencies, services, and CLI.
#

# Text formatting
BOLD="\033[1m"
RED="\033[31m"
GREEN="\033[32m"
YELLOW="\033[33m"
BLUE="\033[34m"
RESET="\033[0m"

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# Log file
LOG_FILE="$SCRIPT_DIR/install_log.txt"
> "$LOG_FILE"  # Clear log file

# Minimum required versions
MIN_PYTHON_VERSION="3.8.0"
MIN_PIP_VERSION="20.0.0"
MIN_DOCKER_VERSION="20.0.0"

# Function to log messages to file and display to user
log() {
    local level=$1
    local message=$2
    local color=$RESET
    
    # Set color based on level
    if [ "$level" = "INFO" ]; then
        color=$BLUE
    elif [ "$level" = "SUCCESS" ]; then
        color=$GREEN
    elif [ "$level" = "WARNING" ]; then
        color=$YELLOW
    elif [ "$level" = "ERROR" ]; then
        color=$RED
    fi
    
    # Log to file (without color)
    echo "$(date '+%Y-%m-%d %H:%M:%S') [$level] $message" >> "$LOG_FILE"
    
    # Display to user (with color)
    echo -e "${color}[$level] $message${RESET}"
}

# Function to prompt user for yes/no
prompt_yes_no() {
    local message=$1
    local default=${2:-n}
    
    local prompt
    if [ "$default" = "y" ]; then
        prompt="[Y/n]"
    else
        prompt="[y/N]"
    fi
    
    while true; do
        read -p "$(echo -e $YELLOW$message $prompt$RESET) " response
        response=${response:-$default}
        case "$response" in
            [Yy]* ) return 0;;
            [Nn]* ) return 1;;
            * ) echo "Please answer yes or no.";;
        esac
    done
}

# Function to check version
version_greater_equal() {
    local version1=$1
    local version2=$2
    printf '%s\n%s\n' "$version2" "$version1" | sort -V -C
}

# Function to create Python virtual environment
create_virtual_env() {
    log "INFO" "Creating Python virtual environment..."
    
    if [ -d "venv" ]; then
        if prompt_yes_no "Virtual environment already exists. Recreate?"; then
            log "INFO" "Removing existing virtual environment..."
            rm -rf venv
        else
            log "INFO" "Using existing virtual environment."
            return 0
        fi
    fi
    
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        log "ERROR" "Failed to create virtual environment."
        return 1
    fi
    
    log "SUCCESS" "Virtual environment created successfully."
    return 0
}

# Function to install Python requirements
install_requirements() {
    log "INFO" "Installing Python requirements..."
    
    source venv/bin/activate
    
    pip install --upgrade pip >> "$LOG_FILE" 2>&1
    pip install wheel >> "$LOG_FILE" 2>&1
    pip install -e . >> "$LOG_FILE" 2>&1
    pip install -r requirements.txt >> "$LOG_FILE" 2>&1
    
    # Make sure Click is installed for the CLI
    pip install click >> "$LOG_FILE" 2>&1
    
    if [ $? -ne 0 ]; then
        log "ERROR" "Failed to install requirements. Check $LOG_FILE for details."
        return 1
    fi
    
    log "SUCCESS" "Python requirements installed successfully."
    return 0
}

# Function to setup the CLI
setup_cli() {
    log "INFO" "Setting up SkillLab CLI..."
    
    # Make CLI executable
    chmod +x "$SCRIPT_DIR/cli.py"
    
    # Create symbolic links
    SYMLINK_DIRS=("$HOME/.local/bin" "$HOME/bin" "/usr/local/bin")
    SYMLINK_CREATED=false
    
    for dir in "${SYMLINK_DIRS[@]}"; do
        if [ -d "$dir" ] && echo "$PATH" | grep -q "$dir"; then
            if ! prompt_yes_no "Create 'skilllab' and 'sl' commands in $dir?"; then
                continue
            fi
            
            # Check if we need sudo for this directory
            if [ ! -w "$dir" ]; then
                log "INFO" "Need sudo permission to create symlinks in $dir"
                sudo ln -sf "$SCRIPT_DIR/cli.py" "$dir/skilllab"
                sudo ln -sf "$SCRIPT_DIR/cli.py" "$dir/sl"
            else
                ln -sf "$SCRIPT_DIR/cli.py" "$dir/skilllab"
                ln -sf "$SCRIPT_DIR/cli.py" "$dir/sl"
            fi
            
            if [ $? -eq 0 ]; then
                log "SUCCESS" "CLI commands created in $dir"
                SYMLINK_CREATED=true
                break
            fi
        fi
    done
    
    if [ "$SYMLINK_CREATED" = false ]; then
        log "WARNING" "Could not create CLI command symlinks. You'll need to run SkillLab using './cli.py'"
    fi
    
    return 0
}

# Function to check and install Docker
check_docker() {
    log "INFO" "Checking Docker installation..."
    
    if ! command -v docker &> /dev/null; then
        log "WARNING" "Docker is not installed."
        if prompt_yes_no "Would you like to install Docker?"; then
            log "INFO" "Installing Docker..."
            
            # Detect OS
            if [ -f /etc/os-release ]; then
                . /etc/os-release
                OS=$ID
            else
                OS=$(uname -s)
            fi
            
            # Install Docker based on OS
            case $OS in
                ubuntu|debian|linuxmint)
                    sudo apt-get update >> "$LOG_FILE" 2>&1
                    sudo apt-get install -y apt-transport-https ca-certificates curl software-properties-common >> "$LOG_FILE" 2>&1
                    curl -fsSL https://download.docker.com/linux/$OS/gpg | sudo apt-key add - >> "$LOG_FILE" 2>&1
                    sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/$OS $(lsb_release -cs) stable" >> "$LOG_FILE" 2>&1
                    sudo apt-get update >> "$LOG_FILE" 2>&1
                    sudo apt-get install -y docker-ce docker-ce-cli containerd.io >> "$LOG_FILE" 2>&1
                    ;;
                fedora|centos|rhel)
                    sudo dnf -y install dnf-plugins-core >> "$LOG_FILE" 2>&1
                    sudo dnf config-manager --add-repo https://download.docker.com/linux/$OS/docker-ce.repo >> "$LOG_FILE" 2>&1
                    sudo dnf install -y docker-ce docker-ce-cli containerd.io >> "$LOG_FILE" 2>&1
                    ;;
                *)
                    log "ERROR" "Unsupported OS for automatic Docker installation. Please install Docker manually from https://docs.docker.com/get-docker/"
                    return 1
                    ;;
            esac
            
            # Start Docker service
            sudo systemctl start docker >> "$LOG_FILE" 2>&1
            sudo systemctl enable docker >> "$LOG_FILE" 2>&1
            
            # Add current user to docker group
            sudo usermod -aG docker $USER >> "$LOG_FILE" 2>&1
            
            # Verify installation
            if ! docker --version &> /dev/null; then
                log "ERROR" "Docker installation failed. Please install Docker manually from https://docs.docker.com/get-docker/"
                return 1
            fi
            
            log "SUCCESS" "Docker installed successfully. You may need to log out and back in for group changes to take effect."
        else
            log "WARNING" "Docker is required for OCR and LLM services. Some features will not be available."
            return 1
        fi
    else
        docker_version=$(docker --version | awk '{print $3}' | sed 's/,//')
        log "SUCCESS" "Docker is installed (version $docker_version)."
        
        # Check Docker version
        if ! version_greater_equal "$docker_version" "$MIN_DOCKER_VERSION"; then
            log "WARNING" "Docker version $docker_version is older than the recommended version $MIN_DOCKER_VERSION. Some features may not work properly."
        fi
        
        # Check if Docker is running
        if ! docker info &> /dev/null; then
            log "WARNING" "Docker is not running."
            if prompt_yes_no "Would you like to start Docker?"; then
                sudo systemctl start docker >> "$LOG_FILE" 2>&1
                if [ $? -ne 0 ]; then
                    log "ERROR" "Failed to start Docker."
                    return 1
                fi
                log "SUCCESS" "Docker started successfully."
            else
                log "WARNING" "Docker is required for OCR and LLM services. Some features will not be available."
                return 1
            fi
        fi
    fi
    
    return 0
}

# Function to check and install Docker Compose
check_docker_compose() {
    log "INFO" "Checking Docker Compose installation..."
    
    if ! command -v docker-compose &> /dev/null; then
        log "WARNING" "Docker Compose is not installed."
        if prompt_yes_no "Would you like to install Docker Compose?"; then
            log "INFO" "Installing Docker Compose..."
            
            # Install Docker Compose
            sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.3/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose >> "$LOG_FILE" 2>&1
            sudo chmod +x /usr/local/bin/docker-compose >> "$LOG_FILE" 2>&1
            
            # Verify installation
            if ! docker-compose --version &> /dev/null; then
                log "ERROR" "Docker Compose installation failed. Please install Docker Compose manually from https://docs.docker.com/compose/install/"
                return 1
            fi
            
            log "SUCCESS" "Docker Compose installed successfully."
        else
            log "WARNING" "Docker Compose is required for running services. Some features will not be available."
            return 1
        fi
    else
        compose_version=$(docker-compose --version | awk '{print $3}')
        log "SUCCESS" "Docker Compose is installed (version $compose_version)."
    fi
    
    return 0
}

# Function to setup SkillLab services (PaddleOCR and Ollama)
setup_services() {
    log "INFO" "Setting up SkillLab services..."
    
    # Check for docker-compose.yml
    if [ ! -f "$SCRIPT_DIR/docker-compose.yml" ]; then
        log "ERROR" "docker-compose.yml not found. Services cannot be set up."
        return 1
    fi
    
    # Start services
    if prompt_yes_no "Start SkillLab services (PaddleOCR and Ollama)?"; then
        log "INFO" "Starting services. This may take a while for the first run..."
        
        # Start services with Docker Compose
        docker-compose up -d >> "$LOG_FILE" 2>&1
        
        if [ $? -ne 0 ]; then
            log "ERROR" "Failed to start services. Check $LOG_FILE for details."
            return 1
        fi
        
        log "SUCCESS" "Services started successfully."
        
        # Pull Mistral model if needed
        log "INFO" "Checking for Mistral model..."
        sleep 5  # Wait for Ollama to start
        
        if ! curl -s localhost:11434/api/tags | grep -q "mistral"; then
            if prompt_yes_no "Mistral model not found. Would you like to download it?"; then
                log "INFO" "Downloading Mistral model. This will take a while..."
                curl -X POST http://localhost:11434/api/pull -d '{"name": "mistral"}' >> "$LOG_FILE" 2>&1
                
                if [ $? -ne 0 ]; then
                    log "ERROR" "Failed to download Mistral model. Check $LOG_FILE for details."
                    return 1
                fi
                
                log "SUCCESS" "Mistral model downloaded successfully."
            else
                log "WARNING" "Mistral model is required for JSON generation. Some features will not be available."
            fi
        else
            log "SUCCESS" "Mistral model is already available."
        fi
    else
        log "INFO" "Services will not be started now. You can start them later with 'docker-compose up -d'"
    fi
    
    return 0
}

# Function to configure SkillLab
configure_skilllab() {
    log "INFO" "Configuring SkillLab..."
    
    # Create config directories if they don't exist
    mkdir -p data/ocr_results >> "$LOG_FILE" 2>&1
    mkdir -p data/json_results >> "$LOG_FILE" 2>&1
    mkdir -p data/models >> "$LOG_FILE" 2>&1
    mkdir -p logs >> "$LOG_FILE" 2>&1
    
    # Check for configuration file
    if [ ! -f "$SCRIPT_DIR/config/default.yaml" ]; then
        log "ERROR" "Configuration file not found. SkillLab cannot be configured properly."
        return 1
    fi
    
    log "SUCCESS" "SkillLab configured successfully."
    return 0
}

# Function to verify the installation
verify_installation() {
    log "INFO" "Verifying SkillLab installation..."
    
    # Check if CLI works
    source venv/bin/activate
    
    if ! python cli.py --help >> "$LOG_FILE" 2>&1; then
        log "ERROR" "CLI verification failed. Check $LOG_FILE for details."
        return 1
    fi
    
    # Check if services are running
    if ! docker ps | grep -q "paddleocr\|ollama"; then
        log "WARNING" "SkillLab services are not running. Some features may not be available."
    else
        log "SUCCESS" "SkillLab services are running."
    fi
    
    log "SUCCESS" "SkillLab installation verified successfully."
    return 0
}

# Main installation process
main() {
    echo -e "${BOLD}${BLUE}=================================================${RESET}"
    echo -e "${BOLD}${BLUE}        SkillLab Installation Script            ${RESET}"
    echo -e "${BOLD}${BLUE}=================================================${RESET}"
    echo
    log "INFO" "Starting installation process..."
    
    # Check Python version
    log "INFO" "Checking Python version..."
    if ! command -v python3 &> /dev/null; then
        log "ERROR" "Python 3 is not installed. Please install Python 3.8 or later."
        exit 1
    fi
    
    python_version=$(python3 --version | awk '{print $2}')
    log "INFO" "Found Python version $python_version"
    
    if ! version_greater_equal "$python_version" "$MIN_PYTHON_VERSION"; then
        log "ERROR" "Python version $python_version is older than the required version $MIN_PYTHON_VERSION. Please upgrade Python."
        exit 1
    fi
    
    # Check pip version
    log "INFO" "Checking pip version..."
    if ! command -v pip3 &> /dev/null; then
        log "WARNING" "pip is not installed."
        if prompt_yes_no "Would you like to install pip?"; then
            log "INFO" "Installing pip..."
            curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py >> "$LOG_FILE" 2>&1
            python3 get-pip.py >> "$LOG_FILE" 2>&1
            rm get-pip.py
            if [ $? -ne 0 ]; then
                log "ERROR" "Failed to install pip."
                exit 1
            fi
            log "SUCCESS" "pip installed successfully."
        else
            log "ERROR" "pip is required for installation. Exiting."
            exit 1
        fi
    fi
    
    pip_version=$(pip3 --version | awk '{print $2}')
    log "INFO" "Found pip version $pip_version"
    
    if ! version_greater_equal "$pip_version" "$MIN_PIP_VERSION"; then
        log "WARNING" "pip version $pip_version is older than the recommended version $MIN_PIP_VERSION. Consider upgrading pip."
    fi
    
    # Check for venv module
    log "INFO" "Checking for venv module..."
    if ! python3 -c "import venv" &> /dev/null; then
        log "WARNING" "Python venv module is not installed."
        if prompt_yes_no "Would you like to install venv?"; then
            log "INFO" "Installing Python venv module..."
            
            # Detect OS and install venv
            if command -v apt-get &> /dev/null; then
                sudo apt-get update >> "$LOG_FILE" 2>&1
                sudo apt-get install -y python3-venv >> "$LOG_FILE" 2>&1
            elif command -v dnf &> /dev/null; then
                sudo dnf install -y python3-venv >> "$LOG_FILE" 2>&1
            else
                log "ERROR" "Could not install venv automatically. Please install the Python venv module manually."
                exit 1
            fi
            
            if ! python3 -c "import venv" &> /dev/null; then
                log "ERROR" "Failed to install Python venv module."
                exit 1
            fi
            log "SUCCESS" "Python venv module installed successfully."
        else
            log "ERROR" "Python venv module is required for installation. Exiting."
            exit 1
        fi
    fi
    
    # Create virtual environment
    if ! create_virtual_env; then
        log "ERROR" "Failed to create virtual environment. Exiting."
        exit 1
    fi
    
    # Install Python requirements
    if ! install_requirements; then
        log "ERROR" "Failed to install Python requirements. Exiting."
        exit 1
    fi
    
    # Setup CLI
    if ! setup_cli; then
        log "WARNING" "Failed to setup CLI. Installation will continue."
    fi
    
    # Check Docker
    have_docker=true
    if ! check_docker; then
        have_docker=false
        log "WARNING" "Docker setup incomplete. Some features will not be available."
    fi
    
    # Check Docker Compose if Docker is installed
    if [ "$have_docker" = true ]; then
        if ! check_docker_compose; then
            log "WARNING" "Docker Compose setup incomplete. Some features will not be available."
        else
            # Setup services
            if ! setup_services; then
                log "WARNING" "Service setup incomplete. Some features will not be available."
            fi
        fi
    fi
    
    # Configure SkillLab
    if ! configure_skilllab; then
        log "WARNING" "SkillLab configuration incomplete. Some features may not work properly."
    fi
    
    # Verify installation
    verify_installation
    
    echo
    log "SUCCESS" "SkillLab installation completed!"
    echo
    echo -e "${BOLD}${GREEN}To start using SkillLab:${RESET}"
    echo -e "1. ${GREEN}Activate the virtual environment:${RESET} source venv/bin/activate"
    echo -e "2. ${GREEN}Run SkillLab CLI:${RESET} skilllab --help"
    echo
    echo -e "${BOLD}${GREEN}Available commands:${RESET}"
    echo -e "- Run extraction: ${GREEN}skilllab run extract --input-dir <path> --output-dir <path>${RESET}"
    echo -e "- Launch review interface: ${GREEN}skilllab ui review${RESET}"
    echo -e "- Check system status: ${GREEN}skilllab monitor status${RESET}"
    echo -e "- Show health: ${GREEN}skilllab health check${RESET}"
    echo
    echo -e "${BOLD}${BLUE}=================================================${RESET}"
    echo -e "${BOLD}${BLUE}          Installation Complete                 ${RESET}"
    echo -e "${BOLD}${BLUE}=================================================${RESET}"
}

# Run the main installation process
main