#!/bin/bash

# Check if script is being run from project root
if [ ! -d "./content/blips" ]; then
    echo "Error: This script must be run from the project root directory."
    echo "Please change to the project root and run the script again."
    exit 1
fi

# Get absolute path to project root
PROJECT_ROOT=$(realpath .)

# Change to the tooling/blips directory and run the Python tool with project root as first argument
cd tooling/blips
python main.py "$PROJECT_ROOT" "$@"
