#!/bin/bash

# Check if folder argument is provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 <folder_name>"
    echo "Example: $0 planets"
    exit 1
fi

FOLDER=$1

# Create output directory if it doesn't exist
mkdir -p "gen_images/$FOLDER"

# Process all PNG files in the specified folder
for file in images/$FOLDER/*.png; do
    # Get base filename without extension
    base=$(basename "$file" .png)
    
    # Process the image and save to .565.b64 file in gen_images
    magick "$file" -background black -alpha remove -depth 8 -colorspace RGB rgb:- | \
    ./rgb888_to_rgb565.py | \
    base64 > "gen_images/$FOLDER/${base}.565.b64"
    
    echo "Processed $file -> gen_images/$FOLDER/${base}.565.b64"
done 
