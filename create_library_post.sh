#!/bin/bash

# Check if script is being run from project root
if [ ! -d "./content/library" ]; then
    echo "Error: This script must be run from the project root directory."
    echo "Please change to the project root and run the script again."
    exit 1
fi

# Get absolute path to library directory
LIBRARY_PATH=$(realpath ./content/library)

# Change to the tooling/library directory and run the Python tool with all arguments plus --create
cd tooling/library
python main.py "$@" --create "$LIBRARY_PATH"
