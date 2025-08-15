#!/bin/bash

# Build script to generate slash command files from template
# Usage: ./build-commands.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE_FILE="$SCRIPT_DIR/orchestrator-commands/orchestrate.md.template"
OUTPUT_DIR="$SCRIPT_DIR/orchestrator-commands"

# Check if template exists
if [ ! -f "$TEMPLATE_FILE" ]; then
    echo "Error: Template file not found: $TEMPLATE_FILE"
    exit 1
fi

echo "Building slash command files from template..."

# Generate orchestrate.md
echo "  Generating orchestrate.md..."
sed \
    -e 's/{{COMMAND_NAME_TITLE}}/Orchestrate/g' \
    -e 's/{{COMMAND_DESCRIPTION}}/Manage the orchestration workflow for tasks with human-in-the-loop gates./g' \
    -e 's/{{MODE_SUFFIX}}//g' \
    -e 's/{{MODE_OUTPUTS}}/ outputs/g' \
    -e 's/{{MODE_SECTION}}//g' \
    -e 's/{{MODE_ADJECTIVE}}//g' \
    -e 's/{{META_COMMENT}}//g' \
    -e 's/{{META_FLAG}}//g' \
    -e 's/{{COMMAND_NAME}}/orchestrate/g' \
    "$TEMPLATE_FILE" > "$OUTPUT_DIR/orchestrate.md"

# Generate morchestrate.md
echo "  Generating morchestrate.md..."
sed \
    -e 's/{{COMMAND_NAME_TITLE}}/Meta-Orchestrate/g' \
    -e 's/{{COMMAND_DESCRIPTION}}/Manage orchestration workflows in meta mode (isolated from main orchestration sessions)./g' \
    -e 's/{{MODE_SUFFIX}}/ in meta mode/g' \
    -e 's/{{MODE_OUTPUTS}}/ meta mode outputs/g' \
    -e 's|{{MODE_SECTION}}|## Purpose\nThe `/morchestrate` command is identical to `/orchestrate` but runs in "meta mode":\n- Uses `.agent-outputs-meta/` instead of `.agent-outputs/` \n- Uses `.claude-meta/` instead of `.claude/`\n- All continuation commands automatically include "meta" flag\n- Prevents interference with main orchestration workflows\n\nThis is essential when developing the orchestrator itself, as it prevents test runs from interfering with the main development workflow.\n\n|g' \
    -e 's/{{MODE_ADJECTIVE}}/meta-/g' \
    -e 's/{{META_COMMENT}}/ in meta mode/g' \
    -e 's/{{META_FLAG}}/ meta/g' \
    -e 's/{{COMMAND_NAME}}/morchestrate/g' \
    "$TEMPLATE_FILE" > "$OUTPUT_DIR/morchestrate.md"

echo "✅ Successfully generated command files:"
echo "   - $OUTPUT_DIR/orchestrate.md"
echo "   - $OUTPUT_DIR/morchestrate.md"