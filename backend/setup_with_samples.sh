#!/bin/bash

# Exit on any error
set -e

# Run the existing setup.sh script
./setup.sh

# Navigate to the database folder
cd database

# Unzip the sample_data.zip
echo "Unzipping sample_data.zip..."
unzip sample_data.zip

# Iterate over each PDF and add to the papers table using Python
for pdf in sample_data/*.pdf; do
    echo "Processing $pdf..."
    filename=$(basename "$pdf" .pdf)
    python3 insert_paper_demo.py "$filename" "$pdf"
done

echo "Setup with samples completed successfully!"
