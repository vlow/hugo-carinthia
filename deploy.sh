#!/bin/bash

# Deploy script for Hugo blog
# This script builds the site and deploys it to the remote location

set -e

# Configuration
DEPLOY_TARGET="ssh://tc3.eu/var/www/"

echo "Building Hugo site..."
hugo --minify

echo "Hugo build completed successfully."
echo "Deploying to: $DEPLOY_TARGET"

# Deploy using rsync
rsync -avz --delete public/ "$DEPLOY_TARGET"

echo "Deployment completed successfully!"
