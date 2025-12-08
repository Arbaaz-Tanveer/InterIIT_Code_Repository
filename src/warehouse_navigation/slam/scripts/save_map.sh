#!/bin/bash

# Default map name if not provided
MAP_NAME=${1:-"map_$(date +%Y%m%d_%H%M%S)"}

echo "Saving map as $MAP_NAME..."
ros2 run nav2_map_server map_saver_cli -f "$MAP_NAME"

if [ $? -eq 0 ]; then
    echo "Map saved successfully!"
    echo "Files created: $MAP_NAME.yaml, $MAP_NAME.pgm"
else
    echo "Failed to save map. Ensure SLAM is running."
fi
