#!/bin/bash

# Deploy script for Hugo blog
# This script builds the site and deploys it to the configured remote location

set -e

echo "Building Hugo site..."
hugo --minify

echo "Hugo build completed successfully."

# Read deploy target from blips tool config
CONFIG_FILE="tooling/blips/config.json"
DEPLOY_TARGET="ssh://tc3.eu/var/www/"

if [ -f "$CONFIG_FILE" ]; then
    # Extract deploy_target from JSON config (simple grep approach)
    DEPLOY_TARGET=$(grep -o '"deploy_target"[[:space:]]*:[[:space:]]*"[^"]*"' "$CONFIG_FILE" | sed 's/.*"deploy_target"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/')
fi

echo "Deploying to: $DEPLOY_TARGET"

# Deploy using rsync
rsync -avz --delete public/ "$DEPLOY_TARGET"

echo "Deployment completed successfully!"
