#!/bin/bash

if [ -z "$1" ]; then
    echo "Usage: $0 <text>"
    exit 1
fi

TEXT="$1"
TEMP_FILE="temp_${RANDOM}.png"
FONT_SIZE=64
FONT="Arial"  # You can change this to any installed font

while true; do
    echo "Trying font size: $FONT_SIZE"
    # Get rendered text dimensions
    DIMENSIONS=$(magick -background black -fill white -font "$FONT" -pointsize $FONT_SIZE label:"$TEXT" -format "%w %h" info: 2>&1)
    WIDTH=$(echo $DIMENSIONS | awk '{print $1}')
    HEIGHT=$(echo $DIMENSIONS | awk '{print $2}')
    echo "Text dimensions: ${WIDTH}x${HEIGHT}"
    if [ -n "$WIDTH" ] && [ -n "$HEIGHT" ] && [ "$WIDTH" -le 64 ] && [ "$HEIGHT" -le 64 ]; then
        break
    fi
    FONT_SIZE=$((FONT_SIZE - 1))
    if [ $FONT_SIZE -le 0 ]; then
        echo "Error: Could not fit text in image"
        exit 1
    fi
done

# Create the final image
magick -size 64x64 xc:black -gravity center -font "$FONT" -pointsize $FONT_SIZE -fill white -annotate 0 "$TEXT" output.png

# Also create a temp file for debugging
magick -size 64x64 xc:black -gravity center -font "$FONT" -pointsize $FONT_SIZE -fill white -annotate 0 "$TEXT" "$TEMP_FILE"

echo "Created output.png with font size $FONT_SIZE"
echo "Temporary file $TEMP_FILE kept for debugging" 