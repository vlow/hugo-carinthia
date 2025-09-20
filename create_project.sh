#!/bin/bash

# Check if script is being run from project root
if [ ! -d "./content/projects" ]; then
    echo "Error: This script must be run from the project root directory."
    echo "Please change to the project root and run the script again."
    exit 1
fi

# Get project title from argument or prompt for it
if [ -n "$1" ]; then
    TITLE="$1"
else
    read -p "Enter project title: " TITLE
fi

if [ -z "$TITLE" ]; then
    echo "Error: Project title is required."
    exit 1
fi

# Create slug from title with improved slugification
slugify_title() {
    echo "$1" | \
        tr '[:upper:]' '[:lower:]' | \
        sed 's/[àáâãäå]/a/g; s/[èéêë]/e/g; s/[ìíîï]/i/g; s/[òóôõö]/o/g; s/[ùúûü]/u/g; s/[ñ]/n/g; s/[ç]/c/g' | \
        sed 's/[^a-z0-9 ]//g' | \
        tr -s ' ' | \
        tr ' ' '-' | \
        sed 's/^-\+\|-\+$//g' | \
        cut -c1-50 | \
        sed 's/-\+$//g'
}

SLUG=$(slugify_title "$TITLE")

if [ -z "$SLUG" ]; then
    echo "Error: Could not generate valid slug from title."
    exit 1
fi

# Create unique filename if it already exists
ORIGINAL_SLUG="$SLUG"
COUNTER=1
while [ -f "./content/projects/$SLUG.md" ]; do
    SLUG="${ORIGINAL_SLUG}-${COUNTER}"
    COUNTER=$((COUNTER + 1))
done

# Use Hugo to create the project file
PROJECT_PATH="projects/$SLUG.md"
hugo new content "$PROJECT_PATH"

if [ $? -ne 0 ]; then
    echo "Error: Failed to create project with Hugo"
    exit 1
fi

# Update the title in the created file to match user input
PROJECT_FILE="./content/$PROJECT_PATH"
if [ -f "$PROJECT_FILE" ]; then
    # Replace the auto-generated title with user's title
    sed -i '' "s/title = '.*'/title = '$TITLE'/" "$PROJECT_FILE"
fi

echo "Created project file: $PROJECT_FILE"

# Get editor from HUGO_EDITOR env var or carinthia config
cd tooling/shared
EDITOR_CMD=$(python3 -c "from config import config_manager; print(config_manager.get_editor())")
cd - > /dev/null

# Open in editor if available
if [ -n "$EDITOR_CMD" ]; then
    echo "Opening in editor: $EDITOR_CMD"
    $EDITOR_CMD "$PROJECT_FILE"
else
    echo "No editor configured. Set HUGO_EDITOR environment variable or configure editor in carinthia settings."
fi
