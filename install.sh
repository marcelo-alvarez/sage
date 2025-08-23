#!/bin/bash

# Claude Orchestrator One-Line Installer
# Usage: curl -fsSL https://raw.githubusercontent.com/marcelo-alvarez/claude-orchestrator/main/install.sh | bash -s -- [--project-dir /path] [--global]

set -e

# Default values
PROJECT_DIR=""
LOCAL_COMMAND_ONLY=false
LOCAL_INSTALL=false
TEMP_DIR=""
BRANCH="main"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print functions
print_error() {
    echo -e "${RED}ERROR: $1${NC}" >&2
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Cleanup function
cleanup() {
    if [ -n "$TEMP_DIR" ] && [ -d "$TEMP_DIR" ] && [ "$LOCAL_INSTALL" != true ]; then
        print_info "Cleaning up temporary files..."
        rm -rf "$TEMP_DIR"
    fi
}

# Set trap for cleanup
trap cleanup EXIT

# Show usage information
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --project-dir DIR    Initialize project files in specific directory (default: current directory)"
    echo "  --branch BRANCH      Install from specific branch (default: main)"
    echo "  --local              Install from current directory instead of downloading from GitHub"
    echo "  --local-command      Install slash command locally in project instead of globally"
    echo "  --help              Show this help message"
    echo ""
    echo "Installation behavior:"
    echo "  - Runtime files always install to ~/.claude-orchestrator/"
    echo "  - Slash command installs globally to ~/.claude/commands/ by default"
    echo "  - Only task files (.claude/tasks*.md) are created in project directory"
    echo ""
    echo "Examples:"
    echo "  # Install globally (recommended)"
    echo "  curl -fsSL https://raw.githubusercontent.com/marcelo-alvarez/claude-orchestrator/main/install.sh | bash"
    echo ""
    echo "  # Initialize specific project"
    echo "  curl -fsSL https://raw.githubusercontent.com/marcelo-alvarez/claude-orchestrator/main/install.sh | bash -s -- --project-dir ~/my-project"
    echo ""
    echo "  # Install with local slash command (project-specific)"
    echo "  curl -fsSL https://raw.githubusercontent.com/marcelo-alvarez/claude-orchestrator/main/install.sh | bash -s -- --local-command"
    echo ""
    echo "  # Install from specific branch"
    echo "  ./install.sh --branch feature/web-dashboard"
    echo ""
    echo "  # Install from current directory (for development)"
    echo "  ./install.sh --local"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --project-dir)
            PROJECT_DIR="$2"
            shift 2
            ;;
        --branch)
            BRANCH="$2"
            shift 2
            ;;
        --local)
            LOCAL_INSTALL=true
            shift
            ;;
        --local-command)
            LOCAL_COMMAND_ONLY=true
            shift
            ;;
        --help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Set default project directory to current directory if not specified
if [ -z "$PROJECT_DIR" ]; then
    PROJECT_DIR="$(pwd)"
fi

# Validate dependencies
check_dependencies() {
    print_info "Checking dependencies..."
    
    if ! command -v git &> /dev/null; then
        print_error "git is required but not installed. Please install git and try again."
        exit 1
    fi
    
    if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
        print_error "Python is required but not installed. Please install Python 3 and try again."
        exit 1
    fi
    
    print_success "Dependencies check passed"
}

# Validate target directory
validate_target_directory() {
    print_info "Validating target directory: $PROJECT_DIR"
    
    # Create directory if it doesn't exist
    if [ ! -d "$PROJECT_DIR" ]; then
        print_info "Creating directory: $PROJECT_DIR"
        mkdir -p "$PROJECT_DIR" || {
            print_error "Failed to create directory: $PROJECT_DIR"
            exit 1
        }
    fi
    
    # Check if directory is writable
    if [ ! -w "$PROJECT_DIR" ]; then
        print_error "Directory is not writable: $PROJECT_DIR"
        exit 1
    fi
    
    print_success "Target directory validated"
}

# Clone repository to temporary directory or use current directory
clone_repository() {
    if [ "$LOCAL_INSTALL" = true ]; then
        print_info "Using current directory for local installation"
        
        # Check if we're in a valid orchestrator directory
        if [ ! -f "orchestrate.py" ] || [ ! -d "templates" ]; then
            print_error "Current directory doesn't appear to be a Claude Orchestrator repository"
            print_error "Missing required files: orchestrate.py or templates/ directory"
            print_error "Make sure you're running this script from the root of the claude-orchestrator repository"
            exit 1
        fi
        
        # Check for missing files that might be needed
        if [ ! -f "process_manager.py" ]; then
            print_warning "process_manager.py not found - some features may not work correctly"
        fi
        
        # Use current directory as source
        TEMP_DIR="$(pwd)"
        print_success "Using local directory as source"
    else
        print_info "Downloading Claude Orchestrator from branch: $BRANCH"
        
        TEMP_DIR=$(mktemp -d)
        git clone --quiet --branch "$BRANCH" https://github.com/marcelo-alvarez/claude-orchestrator.git "$TEMP_DIR" || {
            print_error "Failed to clone repository from branch: $BRANCH"
            exit 1
        }
        
        print_success "Repository downloaded to temporary directory"
    fi
}

# Install orchestrator runtime globally
install_orchestrator_runtime() {
    local runtime_dir="$HOME/.claude-orchestrator"
    print_info "Installing orchestrator runtime to: $runtime_dir"
    
    # Create runtime directory structure
    mkdir -p "$runtime_dir"/{agents,config}
    
    # Copy main orchestrator script
    cp "$TEMP_DIR/orchestrate.py" "$runtime_dir/orchestrate.py"
    
    # Copy process manager if it exists
    if [ -f "$TEMP_DIR/process_manager.py" ]; then
        cp "$TEMP_DIR/process_manager.py" "$runtime_dir/process_manager.py"
    fi
    
    # Copy dashboard server files if they exist
    if [ -f "$TEMP_DIR/dashboard_server.py" ]; then
        cp "$TEMP_DIR/dashboard_server.py" "$runtime_dir/dashboard_server.py"
    fi
    
    if [ -f "$TEMP_DIR/api_server.py" ]; then
        cp "$TEMP_DIR/api_server.py" "$runtime_dir/api_server.py"
    fi
    
    if [ -f "$TEMP_DIR/dashboard.html" ]; then
        cp "$TEMP_DIR/dashboard.html" "$runtime_dir/dashboard.html"
    fi
    
    # Copy cc-orchestrate executable if it exists
    if [ -f "$TEMP_DIR/cc-orchestrate" ]; then
        cp "$TEMP_DIR/cc-orchestrate" "$runtime_dir/cc-orchestrate"
        chmod +x "$runtime_dir/cc-orchestrate"
    fi
    
    # Copy cc-morchestrate executable if it exists
    if [ -f "$TEMP_DIR/cc-morchestrate" ]; then
        cp "$TEMP_DIR/cc-morchestrate" "$runtime_dir/cc-morchestrate"
        chmod +x "$runtime_dir/cc-morchestrate"
    fi
    
    # The orchestrate.py file is already configured for global installation
    # No path modifications needed
    
    # Copy agent templates to global location
    cp -r "$TEMP_DIR/templates/agents/"* "$runtime_dir/agents/"
    
    # Copy default config files
    if [ -f "$TEMP_DIR/templates/agent-config.json" ]; then
        cp "$TEMP_DIR/templates/agent-config.json" "$runtime_dir/config/"
    fi
    
    if [ -f "$TEMP_DIR/templates/workflow-config.json" ]; then
        cp "$TEMP_DIR/templates/workflow-config.json" "$runtime_dir/config/"
    fi
    
    print_success "Orchestrator runtime installed globally"
}

# Initialize project files
initialize_project() {
    if [ -n "$PROJECT_DIR" ]; then
        print_info "Initializing project files in: $PROJECT_DIR"
        cd "$PROJECT_DIR"
    else
        print_info "Initializing project files in current directory"
        PROJECT_DIR="$(pwd)"
    fi
    
    # Create minimal project structure
    mkdir -p .claude
    mkdir -p .agent-outputs
    
    # Remove existing agent-config.json if present to avoid conflicts
    if [ -f ".claude/agent-config.json" ]; then
        print_info "Removing existing .claude/agent-config.json to avoid conflicts"
        rm -f ".claude/agent-config.json"
    fi
    
    # Copy template task files if they don't exist
    if [ ! -f ".claude/tasks.md" ] && [ -f "$TEMP_DIR/templates/tasks.md" ]; then
        cp "$TEMP_DIR/templates/tasks.md" .claude/tasks.md
    fi
    
    if [ ! -f ".claude/tasks-checklist.md" ] && [ -f "$TEMP_DIR/templates/tasks-checklist.md" ]; then
        cp "$TEMP_DIR/templates/tasks-checklist.md" .claude/tasks-checklist.md
    fi
    
    # Copy CLAUDE.md template to project root if it doesn't exist
    if [ ! -f "CLAUDE.md" ] && [ -f "$TEMP_DIR/templates/CLAUDE.md" ]; then
        cp "$TEMP_DIR/templates/CLAUDE.md" CLAUDE.md
        print_info "Created CLAUDE.md from template - please customize the PROJECT OVERVIEW section"
    fi
    
    print_success "Project files initialized"
}

# Install slash command
install_slash_command() {
    local commands_dir
    
    if [ "$LOCAL_COMMAND_ONLY" = true ]; then
        commands_dir="$PROJECT_DIR/.claude/commands"
        print_info "Installing slash command locally to: $commands_dir"
    else
        commands_dir="$HOME/.claude/commands"
        print_info "Installing slash command globally to: $commands_dir"
    fi
    
    # Create commands directory
    mkdir -p "$commands_dir"
    
    # Build command files from template
    print_info "Building slash command files from template..."
    cd "$TEMP_DIR"
    ./build-commands.sh
    
    # Copy generated slash commands
    cp "$TEMP_DIR/orchestrator-commands/orchestrate.md"  "$commands_dir/orchestrate.md"
    cp "$TEMP_DIR/orchestrator-commands/morchestrate.md" "$commands_dir/morchestrate.md"
    
    # Update the script path in the slash commands to use global runtime (if needed)
    sed -i.bak 's|python orchestrate_claude\.py|python3 ~/.claude-orchestrator/orchestrate.py|g' "$commands_dir/orchestrate.md"
    rm -f "$commands_dir/orchestrate.md.bak"
    sed -i.bak 's|python orchestrate_claude\.py|python3 ~/.claude-orchestrator/orchestrate.py|g' "$commands_dir/morchestrate.md"
    rm -f "$commands_dir/morchestrate.md.bak"
    
    print_success "Slash commands installed"
}

# Make scripts executable
make_executable() {
    print_info "Making scripts executable..."
    
    chmod +x "$HOME/.claude-orchestrator/orchestrate.py" 2>/dev/null || true
    
    print_success "Scripts made executable"
}

# Create cc-orchestrate wrapper executable
create_wrapper_executable() {
    print_info "Creating cc-orchestrate wrapper executable..."
    
    # Find a suitable directory in PATH
    local wrapper_dir=""
    
    # Check common directories in order of preference
    for dir in "$HOME/.local/bin" "$HOME/bin" "/usr/local/bin"; do
        if [[ ":$PATH:" == *":$dir:"* ]] || [ "$dir" = "/usr/local/bin" ]; then
            wrapper_dir="$dir"
            break
        fi
    done
    
    # If no suitable directory found, use ~/.local/bin and add to PATH
    if [ -z "$wrapper_dir" ]; then
        wrapper_dir="$HOME/.local/bin"
        print_info "Adding $wrapper_dir to PATH in shell profile"
        
        # Add to shell profile if not already there
        local shell_profile=""
        if [ -f "$HOME/.zshrc" ]; then
            shell_profile="$HOME/.zshrc"
        elif [ -f "$HOME/.bashrc" ]; then
            shell_profile="$HOME/.bashrc"
        elif [ -f "$HOME/.bash_profile" ]; then
            shell_profile="$HOME/.bash_profile"
        fi
        
        if [ -n "$shell_profile" ] && ! grep -q "$wrapper_dir" "$shell_profile" 2>/dev/null; then
            echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$shell_profile"
            print_info "Added $wrapper_dir to PATH in $shell_profile"
        fi
    fi
    
    # Create the wrapper directory
    mkdir -p "$wrapper_dir"
    
    # Create the wrapper scripts - use our Python scripts if available, otherwise fallback to bash wrappers
    if [ -f "$HOME/.claude-orchestrator/cc-orchestrate" ]; then
        # Use the Python cc-orchestrate script
        cp "$HOME/.claude-orchestrator/cc-orchestrate" "$wrapper_dir/cc-orchestrate"
        chmod +x "$wrapper_dir/cc-orchestrate"
    else
        # Fallback to bash wrapper for backward compatibility
        cat > "$wrapper_dir/cc-orchestrate" << 'EOF'
#!/bin/bash
# Claude Code Orchestrator wrapper
exec python3 "$HOME/.claude-orchestrator/orchestrate.py" "$@"
EOF
        chmod +x "$wrapper_dir/cc-orchestrate"
    fi
    
    # Create cc-morchestrate wrapper
    if [ -f "$HOME/.claude-orchestrator/cc-morchestrate" ]; then
        # Use the Python cc-morchestrate script
        cp "$HOME/.claude-orchestrator/cc-morchestrate" "$wrapper_dir/cc-morchestrate"
        chmod +x "$wrapper_dir/cc-morchestrate"
    else
        # Fallback to bash wrapper for backward compatibility
        cat > "$wrapper_dir/cc-morchestrate" << 'EOF'
#!/bin/bash
# Claude Code Orchestrator Meta Mode wrapper
exec python3 "$HOME/.claude-orchestrator/orchestrate.py" "$@" meta
EOF
        chmod +x "$wrapper_dir/cc-morchestrate"
    fi
    
    print_success "cc-orchestrate and cc-morchestrate commands created in $wrapper_dir"
    
    # Check if they're immediately available
    if command -v cc-orchestrate &> /dev/null && command -v cc-morchestrate &> /dev/null; then
        print_success "cc-orchestrate and cc-morchestrate commands are available in PATH"
    else
        print_info "Commands will be available after restarting your terminal"
        print_info "Or run: export PATH=\"$wrapper_dir:\$PATH\""
    fi
}

# Print installation summary
print_summary() {
    echo ""
    echo "🎉 Claude Orchestrator installed successfully!"
    echo ""
    echo "📋 Installation structure:"
    echo "   ~/.claude-orchestrator/         # Runtime files (global)"
    echo "   ├── orchestrate.py             # Main orchestrator script"
    echo "   ├── agents/                    # Agent templates"
    echo "   └── config/                    # Default configurations"
    echo ""
    echo "   cc-orchestrate command          # Global wrapper executable in PATH"
    echo ""
    if [ "$LOCAL_COMMAND_ONLY" = true ]; then
        echo "   $PROJECT_DIR/.claude/commands/  # Slash command (local)"
    else
        echo "   ~/.claude/commands/            # Slash command (global)"
    fi
    echo ""
    if [ -n "$PROJECT_DIR" ]; then
        echo "📁 Project initialized: $PROJECT_DIR"
        echo "   .claude/"
        echo "   ├── tasks.md                   # Task tracking"
        echo "   └── tasks-checklist.md         # Task checklist"
        echo "   .agent-outputs/                # Agent work products"
        echo ""
    fi
    
    if [ "$LOCAL_COMMAND_ONLY" = true ]; then
        print_info "Slash command installed locally - available only in this project"
    else
        print_info "Slash command installed globally - available in all Claude Code projects"
    fi
    
    echo ""
    echo "🚀 Quick Start:"
    echo "   Terminal: cc-orchestrate bootstrap     # Generate initial tasks"
    echo "   Terminal: cc-orchestrate continue      # Run workflow (headless)"
    echo "   Terminal: cc-orchestrate interactive   # Interactive mode with gates"
    echo "   Terminal: cc-orchestrate serve         # Start dashboard server"
    echo "   Terminal: cc-orchestrate stop          # Stop all orchestrator processes"
    echo ""
    if [ -n "$PROJECT_DIR" ]; then
        echo "   Or add tasks manually to: $PROJECT_DIR/.claude/tasks-checklist.md"
    else
        echo "   Or navigate to your project and add tasks to .claude/tasks-checklist.md"
    fi
    echo "   Then in Claude Code: /orchestrate start"
    echo ""
    echo "📖 Available commands:"
    echo "   Workflow: start, continue, status, clean, complete, fail, bootstrap"
    echo "   Server: serve, stop"
    echo "   Gates: approve-criteria, modify-criteria, retry-explorer"
    echo "            approve-completion, retry-from-planner, retry-from-coder, retry-from-verifier"
    echo "   Mode: unsupervised, supervised"
    echo ""
    echo "💡 The orchestrator runtime is now completely separate from your project files!"
}

# Main installation process
main() {
    echo "🔧 Claude Orchestrator Installer"
    echo "================================"
    echo ""
    
    check_dependencies
    if [ -n "$PROJECT_DIR" ]; then
        validate_target_directory
    fi
    clone_repository
    install_orchestrator_runtime
    if [ -n "$PROJECT_DIR" ]; then
        initialize_project
    fi
    install_slash_command
    make_executable
    create_wrapper_executable
    print_summary
}

# Run main function
main "$@"
