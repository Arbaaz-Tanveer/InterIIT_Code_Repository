import collections
import math
import logging
from typing import Deque, NamedTuple, Tuple, List
import os
import cv2
import numpy as np
import matplotlib as plt
import time



# Configure logging (if not already configured in the main file)
logging.basicConfig(level=logging.INFO)

class OdometryRecord(NamedTuple):
    timestamp: int  # Timestamp in milliseconds
    dx: float       # Incremental x displacement in robot frame (forward)
    dy: float       # Incremental y displacement in robot frame (right)
    dtheta: float   # Incremental rotation (radians)

class OdometryBuffer:
    def __init__(self, capacity: int = 1000):
        self.capacity = capacity
        self.buffer: Deque[OdometryRecord] = collections.deque(maxlen=capacity)
        self.last_timestamp: int = None

    def add_record(self, timestamp: int, dx: float, dy: float, dtheta: float):
        if self.last_timestamp is not None:
            if timestamp < self.last_timestamp:
                logging.warning("Detected timestamp decrease (possible microcontroller restart). "
                                "Clearing buffer to avoid invalid integration.")
                self.buffer.clear()
        self.last_timestamp = timestamp

        record = OdometryRecord(timestamp, dx, dy, dtheta)
        self.buffer.append(record)

    def integrate_with_initial(self, initial_pose: Tuple[float, float, float],
                               time_window_ms: int) -> Tuple[float, float, float]:
        """
        Integrate forward in time from an initial pose over the past time_window_ms.
        """
        if not self.buffer:
            # logging.warning("No odometry records available. Returning the initial pose.")
            return initial_pose

        latest_timestamp = self.buffer[-1].timestamp
        earliest_timestamp = self.buffer[0].timestamp
        available_window = latest_timestamp - earliest_timestamp

        if available_window < time_window_ms:
            logging.warning("Requested integration window of %d ms exceeds available data (%d ms). "
                            "Integrating over the maximum available window.", time_window_ms, available_window)
            records = list(self.buffer)
        else:
            start_time = latest_timestamp - time_window_ms
            records = [record for record in self.buffer if record.timestamp >= start_time]

        # Integration is performed in chronological order.
        x, y, theta = initial_pose

        for record in records:
            # Rotate the incremental displacement from the robot's frame to the global frame.
            cos_angle = math.cos(theta)
            sin_angle = math.sin(theta)
            global_dx = record.dx * cos_angle - record.dy * sin_angle
            global_dy = record.dx * sin_angle + record.dy * cos_angle

            # Update the global pose.
            x += global_dx
            y += global_dy
            theta += record.dtheta

        return (x, y, theta)

    def integrate_backward(self, final_pose: Tuple[float, float, float],
                             time_window_ms: int) -> Tuple[float, float, float]:
        """
        Integrate odometry records backward in time over the specified time window,
        starting from the final_pose to estimate the initial pose.
        
        The reversal is achieved by processing the records in reverse chronological order
        and inverting the incremental transformation for each record.
        """
        if not self.buffer:
            logging.warning("No odometry records available. Returning the final pose as the initial pose.")
            return final_pose

        latest_timestamp = self.buffer[-1].timestamp
        # Use records over the last time_window_ms from the final timestamp.
        start_time = latest_timestamp - time_window_ms
        # Filter records within the window.
        records = [record for record in self.buffer if record.timestamp >= start_time]

        if not records:
            logging.warning("No odometry records in the specified time window. Returning the final pose.")
            return final_pose

        # Process records in reverse chronological order.
        x, y, theta = final_pose
        # Reverse the order since we are "undoing" the motion.
        for record in reversed(records):
            # Undo the rotation: theta_prev = theta_next - dtheta.
            theta_prev = theta - record.dtheta

            # To undo the translation, note that in forward integration:
            #   x_next = x_prev + (dx * cos(theta_prev) - dy * sin(theta_prev))
            # Therefore, to retrieve x_prev:
            x_prev = x - (record.dx * math.cos(theta - record.dtheta) - record.dy * math.sin(theta - record.dtheta))
            y_prev = y - (record.dx * math.sin(theta - record.dtheta) + record.dy * math.cos(theta - record.dtheta))

            # Update the pose.
            x, y, theta = x_prev, y_prev, theta_prev

        return (x, y, theta)
        

def principal_value_radians(angle_radians):
    """
    Converts an angle in radians to its principal value in the range [-pi, pi].
    """
    # Normalize the angle to be within [0, 2*pi)
    normalized_angle = angle_radians % (2 * np.pi)

    # Adjust to the range [-pi, pi)
    principal_angle = np.where(normalized_angle > np.pi, normalized_angle - (2 * np.pi), normalized_angle)
    return principal_angle

def visualise_localisation_result(cam, angle, dx, dy, write_coords = True):
    # Return None early if no activation map
    if cam is None:
        return None

    # Load the field map
    field_img = cv2.imread(
        'src/warehouse_navigation/config/maps/test_field.png'
    )
    if field_img is None:
        raise FileNotFoundError("Field map image not found")

    # Normalize activation map to uint8
    if cam.dtype != np.uint8:
        cam_norm = cv2.normalize(cam, None, 0, 255, cv2.NORM_MINMAX)
        cam_uint8 = cam_norm.astype(np.uint8)
    else:
        cam_uint8 = cam

    # Compute rotation in radians and its sin/cos
    theta_rad = angle # adjust zero-reference if needed
    cos_t = np.cos(theta_rad)
    sin_t = np.sin(theta_rad)

    # Field center
    h_map, w_map = field_img.shape[:2]

    h_img, w_img = cam.shape[:2]
    ix, iy = w_img / 2.0, h_img / 2.0

    # Combined affine: rotate around center then translate
    # Compute translation terms so rotation is about (cx, cy)
    tx = dx - (cos_t * ix - sin_t * iy)
    ty = dy - (sin_t * ix + cos_t * iy)
    M = np.array([[cos_t, -sin_t, tx],
                  [sin_t,  cos_t, ty]], dtype=np.float32)

    # Warp activation map into field space
    overlay_map = cv2.warpAffine(cam_uint8, M, (w_map, h_map), flags=cv2.INTER_LINEAR)

    # Apply colormap
    cam_color = cv2.applyColorMap(overlay_map, cv2.COLORMAP_JET)

    # Blend with field image
    alpha = 0.5
    output = cv2.addWeighted(field_img, 1 - alpha, cam_color, alpha, 0)

    # Annotate
    rot_deg = (np.rad2deg(theta_rad) % 360)
    text = f"dx: {dx:.2f}, dy: {dy:.2f}, theta: {rot_deg:.2f}"
    if write_coords:
        cv2.putText(
            output, text, (field_img.shape[0]//100, field_img.shape[1]//30), cv2.FONT_HERSHEY_SIMPLEX,
            field_img.shape[1]/1000, (0, 255, 0), 1, cv2.LINE_AA
        )

    return output

if __name__ == "__main__":
    # Create an odometry buffer with capacity to store 2000 records.
    odo_buffer = OdometryBuffer(capacity=2000)
    
    # Simulate adding odometry data.
    import random
    current_time = 0  # starting timestamp in ms

    # Add records for 5 seconds (every 50ms)
    for _ in range(100):
        current_time += 50
        dx = random.uniform(0.0, 0.05)
        dy = random.uniform(-0.02, 0.02)
        dtheta = random.uniform(-0.01, 0.01)
        odo_buffer.add_record(current_time, dx, dy, dtheta)
    
    # Assume the net pose 2 seconds ago was known:
    initial_pose = (1.0, 1.0, 0.5)  # (x, y, theta)
    
    # Integrate over the past 2000 ms (2 seconds) to get the current pose.
    new_pose = odo_buffer.integrate_with_initial(initial_pose, time_window_ms=2000)
    print(f"Updated pose over the last 2 seconds: x={new_pose[0]:.3f}, y={new_pose[1]:.3f}, theta={new_pose[2]:.3f}")

    # Now, use integrate_backward to recover the initial pose from the final pose.
    recovered_initial_pose = odo_buffer.integrate_backward(new_pose, time_window_ms=2000)
    print(f"Recovered initial pose (backward integration): x={recovered_initial_pose[0]:.3f}, y={recovered_initial_pose[1]:.3f}, theta={recovered_initial_pose[2]:.3f}")
