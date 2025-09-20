#!/bin/bash

# Check if script is being run from project root
if [ ! -d "./content/posts" ]; then
    echo "Error: This script must be run from the project root directory."
    echo "Please change to the project root and run the script again."
    exit 1
fi

# Get post title from argument or prompt for it
if [ -n "$1" ]; then
    TITLE="$1"
else
    read -p "Enter post title: " TITLE
fi

if [ -z "$TITLE" ]; then
    echo "Error: Post title is required."
    exit 1
fi

# Create slug from title (lowercase, replace spaces with hyphens, remove special chars)
SLUG=$(echo "$TITLE" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9 ]//g' | sed 's/ \+/-/g' | sed 's/^-\+\|-\+$//g')

if [ -z "$SLUG" ]; then
    echo "Error: Could not generate valid slug from title."
    exit 1
fi

# Create unique directory name if it already exists
ORIGINAL_SLUG="$SLUG"
COUNTER=1
while [ -d "./content/posts/$SLUG" ]; do
    SLUG="${ORIGINAL_SLUG}-${COUNTER}"
    COUNTER=$((COUNTER + 1))
done

# Create post bundle directory
POST_DIR="./content/posts/$SLUG"
mkdir -p "$POST_DIR"

# Get current date in Hugo format
DATE=$(date -u +"%Y-%m-%dT%H:%M:%S%z")

# Create index.md with frontmatter
cat > "$POST_DIR/index.md" << EOF
+++
title = '$TITLE'
date = $DATE
draft = true
tags = []
+++

Write your post content here...
EOF

echo "Created post bundle: $POST_DIR"
echo "Post file: $POST_DIR/index.md"

# Get editor from HUGO_EDITOR env var or carinthia config
cd tooling/shared
EDITOR_CMD=$(python3 -c "from config import config_manager; print(config_manager.get_editor())")
cd - > /dev/null

# Open in editor if available
if [ -n "$EDITOR_CMD" ]; then
    echo "Opening in editor: $EDITOR_CMD"
    $EDITOR_CMD "$POST_DIR/index.md"
else
    echo "No editor configured. Set HUGO_EDITOR environment variable or configure editor in carinthia settings."
fi
