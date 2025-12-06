import cv2
import numpy as np
import yaml

# ----------------------------
# File paths
# ----------------------------
slam_map_path = "slam_map.pgm"
boundary_path = "map_boundary.png"
output_map_path = "updated_map.pgm"
output_yaml_path = "updated_map.yaml"

# ----------------------------
# Load images
# ----------------------------
slam_map = cv2.imread(slam_map_path, cv2.IMREAD_GRAYSCALE)
boundary = cv2.imread(boundary_path, cv2.IMREAD_GRAYSCALE)

# Resize boundary to match map
boundary = cv2.resize(boundary, (slam_map.shape[1], slam_map.shape[0]))

# ----------------------------
# Merge logic:
# White boundary area → free
# Black boundary area → obstacle
# ----------------------------
updated_map = slam_map.copy()

# Example: set boundary pixels darker than 100 to obstacle
obstacle_mask = boundary < 100
updated_map[obstacle_mask] = 0        # occupied cell in ROS map

# Example: set boundary pixels brighter than 200 to free
free_mask = boundary > 200
updated_map[free_mask] = 254          # free cell in ROS map

# ----------------------------
# Save output map
# ----------------------------
cv2.imwrite(output_map_path, updated_map)

# ----------------------------
# Create new YAML
# ----------------------------
yaml_data = {
    "image": "updated_map.pgm",
    "resolution": 0.05,          # CHANGE to match your SLAM resolution
    "origin": [0.0, 0.0, 0.0],
    "occupied_thresh": 0.65,
    "free_thresh": 0.196,
    "negate": 0
}

with open(output_yaml_path, "w") as f:
    yaml.dump(yaml_data, f)

print("Map updated successfully!")

