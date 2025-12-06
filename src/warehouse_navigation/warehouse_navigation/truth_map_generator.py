import numpy as np
import cv2
from scipy.ndimage import distance_transform_edt


def create_binary_map(width_m, height_m, resolution=5):
    """
    Create a binary (black and white) map image.
    
    Parameters:
        width_m (float): Width of the map in meters.
        height_m (float): Height of the map in meters.
        resolution (int): Number of pixels per meter.
    
    Returns:
        np.ndarray: Black image of size (height_px, width_px) with uint8 type.
    """
    width_px = int(round(width_m * resolution))
    height_px = int(round(height_m * resolution))
    return np.zeros((height_px, width_px), dtype=np.uint8)

def world_to_image(x, y, height_px, resolution=5):
    """
    Convert world (meters) coordinates to image (pixel) coordinates.
    
    World coordinate system:
      - x increases to the right.
      - y increases upward.
    Image coordinate system (OpenCV):
      - x increases to the right.
      - y increases downward.
    
    Parameters:
        x (float): x-coordinate in meters.
        y (float): y-coordinate in meters.
        height_px (int): Height of the image in pixels.
        resolution (int): Number of pixels per meter.
    
    Returns:
        (int, int): (x, y) pixel coordinate in the image.
    """
    x_px = int(round(x * resolution))
    y_px = height_px - int(round(y * resolution))
    return x_px, y_px

def draw_line(img, x1, y1, x2, y2, thickness_m, resolution=5):
    """
    Draw a white line on the binary map between two world points.
    
    Parameters:
        img (np.ndarray): The binary map image.
        x1, y1 (float): Starting point in meters.
        x2, y2 (float): Ending point in meters.
        thickness_m (float): Thickness of the line in meters.
        resolution (int): Pixels per meter.
    """
    height_px = img.shape[0]
    pt1 = world_to_image(x1, y1, height_px, resolution)
    pt2 = world_to_image(x2, y2, height_px, resolution)
    thickness_px = max(1, int(round(thickness_m * resolution)))
    cv2.line(img, pt1, pt2, color=255, thickness=thickness_px)

def draw_circle(img, x, y, radius_m, thickness_m=None, resolution=5, fill=False):
    height_px = img.shape[0]
    center = world_to_image(x, y, height_px, resolution)
    radius_px = int(round(radius_m * resolution))
    if fill:
        thickness = -1  # OpenCV convention for filled shape
    else:
        thickness = max(1, int(round(thickness_m * resolution))) if thickness_m is not None else 1
    cv2.circle(img, center, radius_px, color=255, thickness=thickness)

def draw_semi_circle(img, center_x, center_y, radius_m, thickness_m, resolution=5, start_angle=0, end_angle=180):
    height_px = img.shape[0]
    # Convert center from world to image coordinates.
    center = world_to_image(center_x, center_y, height_px, resolution)
    axes = (int(round(radius_m * resolution)), int(round(radius_m * resolution)))
    thickness_px = max(1, int(round(thickness_m * resolution)))
    # Draw the arc using cv2.ellipse.
    cv2.ellipse(img, center, axes, angle=0, startAngle=start_angle, endAngle=end_angle, color=255, thickness=thickness_px)


def save_map(img, filename):
    """
    Save the binary map image to a file.
    
    Parameters:
        img (np.ndarray): The binary map image.
        filename (str): Path where the image will be saved.
    """
    cv2.imwrite(filename, img)


def draw_robo_room(margin = 0.1 ,resolution=5, thickness_m = 0.05):

    field_width = 10.8
    field_height = 7.4

    field_width += 2*margin
    field_height += 2*margin

    img = create_binary_map(field_width, field_height, resolution)
    # Draw field boundary using margin
    draw_line(img, margin, margin,
              field_width - margin, margin,
              thickness_m, resolution=resolution)  # Bottom edge

    draw_line(img, margin, field_height - margin,
              field_width - margin, field_height - margin,
              thickness_m, resolution=resolution)  # Top edge

    draw_line(img, margin, margin,
              margin, field_height - margin,
              thickness_m, resolution=resolution)  # Left edge

    draw_line(img, field_width - margin, margin,
              field_width - margin, field_height - margin,
              thickness_m, resolution=resolution)  # Right edge
    
    return img
    

def draw_hall12_room(margin=0.1, resolution=5, thickness_m=0.05):

    field_width = 3.57
    field_height = 3.46

    # Expand field size by margin
    field_width += 2 * margin
    field_height += 2 * margin

    img = create_binary_map(field_width, field_height, resolution)

    # Draw field boundary using margin
    draw_line(img, margin, margin,
              field_width - margin, margin,
              thickness_m, resolution=resolution)  # Bottom edge

    draw_line(img, margin, field_height - margin,
              field_width - margin, field_height - margin,
              thickness_m, resolution=resolution)  # Top edge

    draw_line(img, margin, margin,
              margin, field_height - margin,
              thickness_m, resolution=resolution)  # Left edge

    draw_line(img, field_width - margin, margin,
              field_width - margin, field_height - margin,
              thickness_m, resolution=resolution)  # Right edge

    return img

def ps_room(margin=0.1, resolution=5, thickness_m=0.05):

    field_width = 3.1
    field_height = 4.2

    # Expand field size by margin
    field_width += 2 * margin
    field_height += 2 * margin

    img = create_binary_map(field_width, field_height, resolution)

    # Draw field boundary using margin
    draw_line(img, margin + 0.9, margin,
              field_width - margin, margin,
              thickness_m, resolution=resolution)  # Bottom edge

    draw_line(img, margin, field_height - margin,
              field_width - margin, field_height - margin,
              thickness_m, resolution=resolution)  # Top edge

    draw_line(img, margin, margin,
              margin, field_height - margin,
              thickness_m, resolution=resolution)  # Left edge

    draw_line(img, field_width - margin, margin,
              field_width - margin, field_height - margin,
              thickness_m, resolution=resolution)  # Right edge

    return img


def create_distance_field(binary_img, decay_type='exponential', decay_param=0.1, threshold=0.1, max_distance=None):
    """
    Convert a binary image to grayscale based on distance from closest white pixels.
    
    Parameters:
        binary_img (np.ndarray): Input binary image (0 = black, 255 = white)
        decay_type (str): Type of decay function ('exponential', 'linear', 'quadratic', 'gaussian')
        decay_param (float): Parameter controlling decay rate
            - For 'exponential': decay rate (higher = faster decay)
            - For 'linear': slope (higher = faster decay)  
            - For 'quadratic': coefficient (higher = faster decay)
            - For 'gaussian': standard deviation (higher = slower decay)
        threshold (float): Minimum normalized value (0-1). Values below this are set to 0
        max_distance (float): Maximum distance to consider (in pixels). If None, uses image diagonal
    
    Returns:
        np.ndarray: Grayscale image with values based on distance from white pixels
    """
    # Ensure binary image is in correct format
    binary_mask = (binary_img > 127).astype(np.uint8)
    
    # Compute distance transform (distance from each pixel to nearest white pixel)
    distances = distance_transform_edt(1 - binary_mask)
    
    # Set maximum distance if not provided
    if max_distance is None:
        max_distance = np.sqrt(binary_img.shape[0]**2 + binary_img.shape[1]**2)
    
    # Clip distances to max_distance
    distances = np.clip(distances, 0, max_distance)
    
    # Apply decay function based on distance
    if decay_type == 'exponential':
        # f(d) = exp(-decay_param * d)
        normalized_values = np.exp(-decay_param * distances)
    elif decay_type == 'linear':
        # f(d) = max(0, 1 - decay_param * d / max_distance)
        normalized_values = np.maximum(0, 1 - decay_param * distances / max_distance)
    elif decay_type == 'quadratic':
        # f(d) = exp(-decay_param * d^2)
        normalized_values = np.exp(-decay_param * distances**2)
    elif decay_type == 'gaussian':
        # f(d) = exp(-d^2 / (2 * decay_param^2))
        normalized_values = np.exp(-distances**2 / (2 * decay_param**2))
    else:
        raise ValueError(f"Unknown decay_type: {decay_type}")
    
    # White pixels should have maximum value (1.0)
    normalized_values[binary_mask > 0] = 1.0
    
    # Apply threshold
    normalized_values[normalized_values < threshold] = 0.0
    
    # Convert to 8-bit grayscale (0-255)
    grayscale_img = (normalized_values * 255).astype(np.uint8)
    
    return grayscale_img


# Add this to your existing code's main section:
if __name__ == "__main__":
    # Your existing code...
    resolution = 100
    # field_img = draw_robo_room(margin = 0.1 ,resolution=resolution)
    field_img = ps_room(margin = 1 ,resolution=resolution)

    save_map(field_img, "src/warehouse_navigation/config/maps/test_field.png")
    
    # NEW: Create distance field version
    distance_field = create_distance_field(
        field_img, 
        decay_type='exponential',  # Options: 'exponential', 'linear', 'quadratic', 'gaussian'
        decay_param=0.06,          # Lower = slower decay, higher = faster decay
        threshold=0.03             # Values below 10% are set to 0
    )
    
    # Save the distance field
    save_map(distance_field, "src/warehouse_navigation/config/maps/distance_test_field.png")
    
    