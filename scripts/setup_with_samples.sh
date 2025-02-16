#!/bin/bash

# Exit on any error
set -e

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

# Run the existing setup.sh script
"$SCRIPT_DIR/setup.sh"

# Use the new seed folder for sample data
SAMPLES_DIR="$( cd "$SCRIPT_DIR/../modules/database/seed" && pwd )"

# Iterate over each PDF in the seed folder and add to the papers table using Python
for pdf in "$SAMPLES_DIR"/*.pdf; do
    echo "Processing $pdf..."
    filename=$(basename "$pdf" .pdf)
    uv run "$SCRIPT_DIR/seed.py" "$filename" "$pdf"
done



echo "Setup with samples completed successfully!"