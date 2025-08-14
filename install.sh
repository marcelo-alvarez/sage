#!/bin/bash

# Claude Orchestrator One-Line Installer
# Usage: curl -fsSL https://raw.githubusercontent.com/marcelo-alvarez/claude-orchestrator/main/install.sh | bash -s -- [--project-dir /path] [--global]

set -e

# Default values
PROJECT_DIR=""
GLOBAL_INSTALL=false
TEMP_DIR=""

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
    if [ -n "$TEMP_DIR" ] && [ -d "$TEMP_DIR" ]; then
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
    echo "  --project-dir DIR    Install to specific directory (default: current directory)"
    echo "  --global            Install slash command globally (~/.claude/commands/)"
    echo "  --help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  # Install in current directory (local slash command)"
    echo "  curl -fsSL https://raw.githubusercontent.com/marcelo-alvarez/claude-orchestrator/main/install.sh | bash"
    echo ""
    echo "  # Install in specific directory"
    echo "  curl -fsSL https://raw.githubusercontent.com/marcelo-alvarez/claude-orchestrator/main/install.sh | bash -s -- --project-dir ~/my-project"
    echo ""
    echo "  # Install with global slash command"
    echo "  curl -fsSL https://raw.githubusercontent.com/marcelo-alvarez/claude-orchestrator/main/install.sh | bash -s -- --project-dir ~/my-project --global"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --project-dir)
            PROJECT_DIR="$2"
            shift 2
            ;;
        --global)
            GLOBAL_INSTALL=true
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

# Clone repository to temporary directory
clone_repository() {
    print_info "Downloading Claude Orchestrator..."
    
    TEMP_DIR=$(mktemp -d)
    git clone --quiet https://github.com/marcelo-alvarez/claude-orchestrator.git "$TEMP_DIR" || {
        print_error "Failed to clone repository"
        exit 1
    }
    
    print_success "Repository downloaded to temporary directory"
}

# Install orchestrator files
install_orchestrator() {
    print_info "Installing orchestrator files to: $PROJECT_DIR"
    
    cd "$PROJECT_DIR"
    
    # Create .claude directory structure
    mkdir -p .claude
    
    # Copy main orchestrator script
    cp "$TEMP_DIR/orchestrate.py" .claude/orchestrate.py
    
    # Update paths in orchestrate.py for .claude/ directory structure
    sed -i.bak 's|self\.outputs_dir = Path("\.agent-outputs")|self.outputs_dir = Path(".agent-outputs")|g' .claude/orchestrate.py
    sed -i.bak 's|self\.tasks_file = Path("tasks\.md")|self.tasks_file = Path(".claude/tasks.md")|g' .claude/orchestrate.py
    sed -i.bak 's|self\.checklist_file = Path("tasks-checklist\.md")|self.checklist_file = Path(".claude/tasks-checklist.md")|g' .claude/orchestrate.py
    rm -f .claude/orchestrate.py.bak
    
    # Create other required directories
    mkdir -p .claude-agents/{explorer,planner,coder,verifier}
    mkdir -p .agent-outputs
    
    # Copy agent templates
    cp -r "$TEMP_DIR/templates/agents/"* .claude-agents/
    
    # Copy template files to .claude directory
    if [ -f "$TEMP_DIR/templates/tasks.md" ]; then
        cp "$TEMP_DIR/templates/tasks.md" .claude/tasks.md
    fi
    
    if [ -f "$TEMP_DIR/templates/tasks-checklist.md" ]; then
        cp "$TEMP_DIR/templates/tasks-checklist.md" .claude/tasks-checklist.md
    fi
    
    # Copy CLAUDE.md template to project root if it doesn't exist
    if [ ! -f "CLAUDE.md" ] && [ -f "$TEMP_DIR/templates/CLAUDE.md" ]; then
        cp "$TEMP_DIR/templates/CLAUDE.md" CLAUDE.md
        print_info "Created CLAUDE.md from template - please customize the PROJECT OVERVIEW section"
    fi
    
    print_success "Orchestrator files installed"
}

# Install slash command
install_slash_command() {
    local commands_dir
    
    if [ "$GLOBAL_INSTALL" = true ]; then
        commands_dir="$HOME/.claude/commands"
        print_info "Installing slash command globally to: $commands_dir"
    else
        commands_dir="$PROJECT_DIR/.claude/commands"
        print_info "Installing slash command locally to: $commands_dir"
    fi
    
    # Create commands directory
    mkdir -p "$commands_dir"
    
    # Copy slash command and update the script path
    cp "$TEMP_DIR/orchestrator-commands/orchestrate.md" "$commands_dir/orchestrate.md"
    
    # Update the script path in the slash command to use .claude/orchestrate.py with python3
    if [ "$GLOBAL_INSTALL" = true ]; then
        # For global install, use relative path from any project
        sed -i.bak 's|python orchestrate_claude\.py|python3 .claude/orchestrate.py|g' "$commands_dir/orchestrate.md"
    else
        # For local install, use relative path
        sed -i.bak 's|python orchestrate_claude\.py|python3 .claude/orchestrate.py|g' "$commands_dir/orchestrate.md"
    fi
    rm -f "$commands_dir/orchestrate.md.bak"
    
    print_success "Slash command installed"
}

# Make scripts executable
make_executable() {
    print_info "Making scripts executable..."
    
    chmod +x "$PROJECT_DIR/.claude/orchestrate.py" 2>/dev/null || true
    
    print_success "Scripts made executable"
}

# Print installation summary
print_summary() {
    echo ""
    echo "🎉 Claude Orchestrator installed successfully!"
    echo ""
    echo "📁 Installation directory: $PROJECT_DIR"
    echo ""
    echo "📋 Project structure created:"
    echo "   .claude/"
    echo "   ├── orchestrate.py              # Main orchestrator script"
    echo "   ├── tasks.md                    # Task tracking"
    echo "   ├── tasks-checklist.md          # Task checklist"
    echo "   └── commands/"
    if [ "$GLOBAL_INSTALL" = true ]; then
        echo "       └── (slash command installed globally)"
    else
        echo "       └── orchestrate.md          # Slash command (local)"
    fi
    echo "   .claude-agents/                 # Agent templates"
    echo "   .agent-outputs/                 # Agent work products"
    echo ""
    
    if [ "$GLOBAL_INSTALL" = true ]; then
        print_info "Slash command installed globally - available in all Claude Code projects"
    else
        print_info "Slash command installed locally - available only in this project"
    fi
    
    echo ""
    echo "🚀 Quick Start:"
    echo "1. Add tasks to .claude/tasks-checklist.md"
    echo "2. In Claude Code, run: /orchestrate start"
    echo ""
    echo "📖 Commands:"
    echo "   /orchestrate start       # Start fresh workflow"
    echo "   /orchestrate continue    # Continue workflow"
    echo "   /orchestrate status      # Show current progress"
    echo "   /orchestrate clean       # Reset outputs"
    echo ""
    echo "For more information, see the README.md in the project directory."
}

# Main installation process
main() {
    echo "🔧 Claude Orchestrator Installer"
    echo "================================"
    echo ""
    
    check_dependencies
    validate_target_directory
    clone_repository
    install_orchestrator
    install_slash_command
    make_executable
    print_summary
}

# Run main function
main "$@"