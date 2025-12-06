#!/usr/bin/env python3
import time
import threading
import os
import numpy as np
import cv2
import math
import logging

# ROS2 imports
import rclpy
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor
from std_msgs.msg import Float32MultiArray, MultiArrayDimension, Int16MultiArray
from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import PoseStamped
from localisation_pkg.srv import Localisation

# Import utilities (adjust path as needed)
from main_pkg.utilities import (
    OdometryBuffer, 
    principal_value_radians,
    visualise_localisation_result
)

# ---------------------------------------------------
# Global variables & Configuration
# ---------------------------------------------------

# --- PERFORMANCE CONFIGURATION ---
ENABLE_SAMPLING = True       # Set to True to downsample LiDAR points for speed
SAMPLE_SIZE = 500            # Number of points to keep if sampling is on
ENABLE_VISUALIZATION = False # Set to False to disable CV2 windows and map drawing
LIDAR_OFFSET_X = -20 #IN CM
# ---------------------------------

# --- OBSTACLE DETECTION CONFIG ---
OBSTACLE_CLUSTER_DIST = 0.15     # Max distance between points to be one object
OBSTACLE_MIN_POINTS = 5          # Min points to try fitting a circle
OBSTACLE_MAX_RESIDUAL = 0.02     # How "round" the object must be
OBSTACLE_MIN_RADIUS = 0.05       # Min radius in meters
OBSTACLE_MAX_RADIUS = 0.3       # Max radius in meters
OBSTACLE_MAX_RANGE = 4.0         # Ignore points further than 4m
# ---------------------------------
obstacle_publishing = False

# Global to share detected circles with the visualization thread
latest_obstacles_vis = []
latest_ground_map = None
latest_localiser_img = None
latest_scan_data = None

FIELD_WIDTH = 3.77
FIELD_HEIGHT = 3.66

map_scale = 100  # pixels per meter
map_size_m = 8
map_size_px = int(map_size_m * map_scale)

# Robot state
bot_pos = [1.285, -1.23, -np.pi/2]  # x, y, theta
obstacles = []
odo_buffer = OdometryBuffer(capacity=2000)

# Odometry tracking for localization fusion/rejection
x_abs_delta_since_last_localisation = 0
y_abs_delta_since_last_localisation = 0
rotation_since_last_localisation = 0

# Thread safety
global_lock = threading.Lock()

# ROS2 node and communication
ros_node = None
bot_pos_pub = None
obstacles_pub = None
command_sub = None
scan_sub = None
localisation_client = None
executor = None
executor_localisation = None

# Logging settings
log_settings = {
    "lidar": {
        "scan_received": False,
        "map_update": False,
    },
    "localisation": {
        "request_sent": False,
        "response": False,
        "rejection": True,       # Log when a jump is rejected
        "tolerance": False,
        "odometry_weight": False,
        "latency": False,
        "merged_position": True,
    },
    "command_received": False,
}


# ---------------------------------------------------
# Helper: Euler to Quaternion
# ---------------------------------------------------
def get_quaternion_from_euler(yaw):
    """Convert an Euler angle (yaw) to a quaternion [x, y, z, w]."""
    qx = 0.0
    qy = 0.0
    qz = np.sin(yaw / 2.0)
    qw = np.cos(yaw / 2.0)
    return [qx, qy, qz, qw]


# ---------------------------------------------------
# LiDAR scan callback
# ---------------------------------------------------
def scan_callback(msg: LaserScan):
    """
    Callback for receiving LiDAR scan data.
    Stores the scan data globally for processing.
    """
    global latest_scan_data
    
    with global_lock:
        latest_scan_data = {
            'ranges': np.array(msg.ranges),
            'angle_min': msg.angle_min,
            'angle_max': msg.angle_max,
            'angle_increment': msg.angle_increment,
            'timestamp': time.time()
        }
    
    if log_settings["lidar"]["scan_received"]:
        print(f"Received LiDAR scan with {len(msg.ranges)} points")


def euclidean_clusters(points):
    """Clusters contiguous points based on Euclidean distance."""
    if len(points) == 0:
        return []
    clusters = []
    current = [points[0]]
    for prev, curr in zip(points[:-1], points[1:]):
        # Calculate distance
        dist = math.hypot(curr[0] - prev[0], curr[1] - prev[1])
        if dist <= OBSTACLE_CLUSTER_DIST:
            current.append(curr)
        else:
            clusters.append(current)
            current = [curr]
    if current:
        clusters.append(current)
    return clusters

def fit_circle(xy_points):
    """Fits a circle to points. Returns (x, y, r, residual) or None."""
    pts = np.array(xy_points)
    x = pts[:,0]
    y = pts[:,1]
    A = np.column_stack((x, y, np.ones_like(x)))
    b = -(x**2 + y**2)
    try:
        params, *_ = np.linalg.lstsq(A, b, rcond=None)
    except Exception:
        return None
    a, b_param, c = params
    x0 = -a / 2.0
    y0 = -b_param / 2.0
    r_sq = x0**2 + y0**2 - c
    if r_sq <= 0: return None
    r = math.sqrt(r_sq)
    
    # Residual check
    dists = np.sqrt((x - x0)**2 + (y - y0)**2)
    mean_res = float(np.mean(np.abs(dists - r)))
    
    return (float(x0), float(y0), float(r), mean_res)


# ---------------------------------------------------
# Convert LiDAR scan to ground map
# ---------------------------------------------------
def lidar_to_points_and_map(scan_data, map_size_px, scale, 
                           enable_sampling=False, sample_size=200, 
                           visualize=True):
    """
    Returns:
    1. points_flat: Sampled, flattened pixel list (for Localization/GUI)
    2. ground_map: Visual image
    3. full_points_meters: Full high-precision list [(x,y), ...] (for Obstacle Detection)
    """
    ground_map = np.zeros((map_size_px, map_size_px), dtype=np.uint8) if visualize else None
    
    ranges = scan_data['ranges']
    angle_min = scan_data['angle_min']
    angle_increment = scan_data['angle_increment']
    center_x = map_size_px / 2.0
    center_y = map_size_px / 2.0

    # --- 1. Vectorized Calculation (Fast & Complete) ---
    valid_mask = (np.isfinite(ranges)) & (ranges > 0.01)
    inds = np.arange(len(ranges))[valid_mask]
    r = ranges[valid_mask]
    
    theta = angle_min + inds * angle_increment
    x_all = r * np.cos(theta)
    y_all = -r * np.sin(theta)  # Standard ROS: y is left

    # Store full list for Obstacle Detection [N, 2]
    full_points_meters = np.column_stack((x_all, y_all))

    # --- 2. Sampling (For Localization/Map Speed) ---
    if enable_sampling and len(x_all) > sample_size:
        sample_inds = np.random.choice(len(x_all), sample_size, replace=False)
        x_vis = x_all[sample_inds]
        y_vis = y_all[sample_inds]
    else:
        x_vis = x_all
        y_vis = y_all

    # --- 3. Convert Sampled Points to Pixels ---
    px_arr = (center_x + y_vis * scale + LIDAR_OFFSET_X).astype(np.int16)
    py_arr = (center_y - x_vis * scale).astype(np.int16)

    in_bounds = (px_arr >= 0) & (px_arr < map_size_px) & \
                (py_arr >= 0) & (py_arr < map_size_px)
    
    px_final = px_arr[in_bounds]
    py_final = py_arr[in_bounds]

    if visualize:
        # ground_map[py_final, px_final] = 255
        for px, py in zip(px_final, py_final):
            cv2.circle(ground_map, (px, py), 1, (255), -1)

    # Center coordinates relative to robot (0,0) for the service
    x_centered = px_final - center_x
    y_centered = py_final - center_y
    
    points_flat = np.stack((x_centered, y_centered), axis=1).flatten().astype(np.int16).tolist()
    
    return points_flat, ground_map, full_points_meters


# ---------------------------------------------------
# Odometry callback
# ---------------------------------------------------
def command_callback(msg):
    """
    Callback for odometry delta updates.
    Updates dead-reckoning and accumulates deltas for rejection logic.
    """
    global bot_pos, x_abs_delta_since_last_localisation
    global y_abs_delta_since_last_localisation, rotation_since_last_localisation
    
    try:
        command_data = msg.data
        if log_settings["command_received"]:
            print(f"Received odometry: {command_data}")
        
        if len(command_data) < 4:
            return
        
        with global_lock:
            # Store raw odom for latency compensation later
            odo_buffer.add_record(command_data[0], command_data[1], 
                                command_data[2], command_data[3])
            theta = bot_pos[2]
        
        dx, dy, dtheta = command_data[1], command_data[2], command_data[3]
        
        # Transform local robot delta to global map frame
        cos_angle = math.cos(theta)
        sin_angle = math.sin(theta)
        global_dx = dx * cos_angle - dy * sin_angle
        global_dy = dx * sin_angle + dy * cos_angle
        
        # Update robot position (Dead Reckoning)
        with global_lock:
            bot_pos[0] += global_dx
            bot_pos[1] += global_dy
            bot_pos[2] = principal_value_radians(bot_pos[2] + dtheta)
            
            # Accumulate absolute deltas to determine trust/tolerance of next vision update
            x_abs_delta_since_last_localisation += abs(dx)
            y_abs_delta_since_last_localisation += abs(dy)
            rotation_since_last_localisation += abs(dtheta)
    
    except Exception as e:
        logging.exception(f"Error processing odometry: {e}")


# ---------------------------------------------------
# ROS2 message helper
# ---------------------------------------------------
def create_float32_array(data, label=""):
    """Create a Float32MultiArray message with proper layout"""
    msg = Float32MultiArray()
    msg.layout.dim.append(MultiArrayDimension())
    msg.layout.dim[0].label = label
    msg.layout.dim[0].size = len(data)
    msg.layout.dim[0].stride = len(data)
    msg.layout.data_offset = 0
    msg.data = [float(val) for val in data]
    return msg


# ---------------------------------------------------
# Localization Client
# ---------------------------------------------------
class LocalisationClient(Node):
    def __init__(self):
        super().__init__('localisation_client')
        self.cli = self.create_client(Localisation, 'localise')
        self.req = Localisation.Request()

    def send_request(self, flattened_points, bounds):
        points = Int16MultiArray()
        points.data = flattened_points
        dim0 = MultiArrayDimension()
        dim0.label = 'points'
        dim0.size = len(flattened_points) // 2
        dim0.stride = len(flattened_points)
        dim1 = MultiArrayDimension()
        dim1.label = 'coords'
        dim1.size = 2
        dim1.stride = 2
        points.layout.dim = [dim0, dim1]
        points.layout.data_offset = 0
        self.req.points = points

        bounds_msg = Float32MultiArray()
        bounds_msg.data = bounds
        dim0 = MultiArrayDimension()
        dim0.label = 'axes'
        dim0.size = 3
        dim0.stride = 6
        dim1 = MultiArrayDimension()
        dim1.label = 'bounds'
        dim1.size = 2
        dim1.stride = 2
        bounds_msg.layout.dim = [dim0, dim1]
        bounds_msg.layout.data_offset = 0
        self.req.bounds = bounds_msg

        if log_settings["localisation"]["request_sent"]:
            self.get_logger().info("Sending localization request")
        
        return self.cli.call_async(self.req)

def detect_and_create_obstacle_msg(raw_points):
    """
    Takes raw (x,y) meter points, performs clustering and circle fitting.
    Returns:
        1. Float32MultiArray message ready for publishing
        2. List of (cx, cy, r) tuples for visualization
    """
    # 1. Filter by Max Range (Numpy optimization)
    if len(raw_points) > 0:
        dists = np.linalg.norm(raw_points, axis=1)
        det_pts = raw_points[dists <= OBSTACLE_MAX_RANGE]
    else:
        return None, []

    # 2. Cluster
    clusters = euclidean_clusters(det_pts)
    
    # 3. Fit & Filter
    obs_flat_list = []      # Data for ROS message
    valid_circles_vis = []  # Data for CV2 visualization
    
    for cluster in clusters:
        if len(cluster) < OBSTACLE_MIN_POINTS: continue
        
        fit = fit_circle(cluster)
        if not fit: continue
        
        cx, cy, r, res = fit
        
        # Filter: Residual & Radius
        if res <= OBSTACLE_MAX_RESIDUAL and OBSTACLE_MIN_RADIUS <= r <= OBSTACLE_MAX_RADIUS:
            obs_flat_list.extend([cx, cy])
            valid_circles_vis.append((cx, cy, r))

    # 4. Create Message: [Count, x1, y1, x2, y2...]
    final_data = [float(len(valid_circles_vis))] + obs_flat_list
    msg = create_float32_array(final_data, label="obstacles")
    
    return msg, valid_circles_vis

# ---------------------------------------------------
# Localization thread
# ---------------------------------------------------
def localisation_thread_func():
    """
    Continuously processes LiDAR data to update ground map and perform localization
    in a non-blocking manner. Includes outlier rejection and sensor fusion.
    """
    global bot_pos, latest_ground_map, latest_localiser_img
    global x_abs_delta_since_last_localisation, y_abs_delta_since_last_localisation
    global rotation_since_last_localisation
    global latest_obstacles_vis # Access the global we added in Step 1
    
    show_localisation_result = True
    estimated_lidar_latency = 0.05  # 50ms processing latency assumption
    
    # --- ASYNC STATE VARIABLES ---
    current_future = None
    capture_time_of_pending_req = 0
    # ---------------------------

    while True:
        time.sleep(0.01)

        with global_lock:
            if latest_scan_data is None:
                continue
            scan_data = latest_scan_data.copy()
        
        # 1. Update Map & Get Raw Points
        points, common_ground_map, raw_meter_points = lidar_to_points_and_map(
            scan_data, 
            map_size_px, 
            map_scale, 
            enable_sampling=ENABLE_SAMPLING, 
            sample_size=SAMPLE_SIZE,
            visualize=ENABLE_VISUALIZATION
        )
        
        # Update global ground map for display
        if ENABLE_VISUALIZATION and common_ground_map is not None:
            with global_lock:
                latest_ground_map = common_ground_map.copy()

        # ====================================================
        # 2. OBSTACLE DETECTION (Clean Call)
        # ====================================================
        if obstacle_publishing:
            try:
                obs_msg, vis_circles = detect_and_create_obstacle_msg(raw_meter_points)
                
                # Publish
                if obs_msg:
                    obstacles_pub.publish(obs_msg)
                
                # Update Visualization Global
                with global_lock:
                    latest_obstacles_vis = vis_circles

            except Exception as e:
                # Don't let detection crash the localization thread
                print(f"Obstacle detection failed: {e}")
        # ====================================================

        # ---------------------------------------------------------
        # 3. Check Service Availability (Localization Logic follows...)
        # ---------------------------------------------------------
        if not localisation_client.cli.service_is_ready():
            continue

        # ---------------------------------------------------------
        # 3. Non-Blocking Request Handling
        # ---------------------------------------------------------
        
        # STATE A: NO REQUEST PENDING -> Send one
        if current_future is None:
            
            with global_lock:
                curr_pos = bot_pos.copy()
            
            # Prepare Search Bounds (Centered on current odometry)
            map_pos = [
                (curr_pos[0] + (FIELD_WIDTH/2)) * map_scale,
                (-curr_pos[1] + (FIELD_HEIGHT/2)) * map_scale,
                2 * np.pi - curr_pos[2]
            ]
            bound_size = [0.5 * map_scale, 0.5 * map_scale, np.pi/4] # Search window
            
            bounds = [
                map_pos[0] - bound_size[0], map_pos[0] + bound_size[0],
                map_pos[1] - bound_size[1], map_pos[1] + bound_size[1],
                map_pos[2] - bound_size[2], map_pos[2] + bound_size[2]
            ]
            
            # Send the request asynchronously
            current_future = localisation_client.send_request(points, bounds)
            
            # Save the timestamp of the actual data we just sent for latency calc
            capture_time_of_pending_req = scan_data['timestamp'] - estimated_lidar_latency

        # STATE B: REQUEST PENDING -> Check if done
        else:
            if current_future.done():
                try:
                    response = current_future.result()
                    
                    if response is not None:
                        # --- Process Response ---
                        
                        if log_settings["localisation"]["response"]:
                            localisation_client.get_logger().info(
                                f'Loc Response: X={response.transform.data[0]:.3f} '
                                f'Y={response.transform.data[1]:.3f} '
                                f'Theta={response.transform.data[2]:.3f}'
                            )

                        tx_cartesian = response.transform.data[0] / map_scale - (FIELD_WIDTH/2)
                        ty_cartesian = -(response.transform.data[1] / map_scale - (FIELD_HEIGHT/2))
                        heading = principal_value_radians(2*np.pi - response.transform.data[2])

                        # # =========================================================
                        # # REJECTION LOGIC
                        # # =========================================================
                        with global_lock:
                            curr_pos = bot_pos.copy()
                            # How much have we moved since the last valid update?
                            sq_dist_delta = (x_abs_delta_since_last_localisation ** 2 + 
                                           y_abs_delta_since_last_localisation ** 2)
                            angle_delta = rotation_since_last_localisation
                        
                        # Dynamic Tolerance: scales with distance moved
                        square_distance_tolerance = 0.3 + sq_dist_delta * sq_dist_delta * 0.01
                        angle_tolerance = 0.5 + angle_delta * 0.01

                        if log_settings["localisation"]["tolerance"]:
                             print(f"Tolerance: SqDist={square_distance_tolerance:.3f}, Angle={angle_tolerance:.3f}")

                        # Calculate error between Odometry (curr_pos) and Vision Result
                        pos_diff_sq = ((tx_cartesian - curr_pos[0]) ** 2 + (ty_cartesian - curr_pos[1]) ** 2)
                        angle_diff = abs(principal_value_radians(heading - curr_pos[2]))

                        # Reject if the jump is too large (glitch detection)
                        if pos_diff_sq > square_distance_tolerance or angle_diff > angle_tolerance:
                             if log_settings["localisation"]["rejection"]:
                                 localisation_client.get_logger().info(f"REJECTED: DistErr={pos_diff_sq:.3f},angleError={angle_diff} Tol={square_distance_tolerance:.3f}")
                             # IMPORTANT: Do not reset deltas, do not update position
                             raise ValueError("Tolerance exceeded")

                        # =========================================================
                        # LATENCY COMPENSATION
                        # =========================================================
                        localization_end_time = time.time()
                        total_latency = localization_end_time - capture_time_of_pending_req
                        
                        if log_settings["localisation"]["latency"]:
                             print(f"Total Latency: {total_latency:.4f}s")

                        # Start with the raw vision result
                        pos_localisation = [tx_cartesian, ty_cartesian, heading]
                        
                        # Integrate odometry from capture_time to NOW to forward-predict the result
                        pos_localisation = odo_buffer.integrate_with_initial(
                            pos_localisation, 
                            time_window_ms=total_latency * 1000
                        )

                        # =========================================================
                        # DYNAMIC WEIGHTING (Sensor Fusion)
                        # =========================================================
                        # Check displacement in last 100ms to see if robot is moving
                        displacement = odo_buffer.integrate_with_initial([0.0, 0.0, 0.0], 100)
                        velocity_proxy = displacement[0]**2 + displacement[1]**2
                        
                        # Stationary = High Odom Weight (0.95). Moving = Lower Odom Weight (0.75)
                        # odometry_weight = 0.85 - min(0.20, 300.0 * velocity_proxy)
                        odometry_weight = 1.00         #-----------------------------------------------------------------------------------------------
                        if log_settings["localisation"]["odometry_weight"]:
                            print(f"Odom Weight: {odometry_weight:.3f}")

                        # Merge Current State (Odom) with Corrected State (Vision)
                        final_pos = [
                            odometry_weight * curr_pos[0] + (1 - odometry_weight) * pos_localisation[0],
                            odometry_weight * curr_pos[1] + (1 - odometry_weight) * pos_localisation[1],
                            odometry_weight * ((curr_pos[2] - pos_localisation[2] + np.pi) % (2 * np.pi) - np.pi) + pos_localisation[2]
                        ]

                        # =========================================================
                        # UPDATE GLOBAL STATE
                        # =========================================================
                        if log_settings["localisation"]["merged_position"]:
                             print(f"Merged Pos: {final_pos}")

                        with global_lock:
                            bot_pos = final_pos.copy()        ##-----------------------------------------------------------------------------
                            
                            # Reset Deltas on successful update
                            x_abs_delta_since_last_localisation = 0
                            y_abs_delta_since_last_localisation = 0
                            rotation_since_last_localisation = 0
                            
                            # Visualize result
                            if ENABLE_VISUALIZATION and show_localisation_result and common_ground_map is not None:
                                latest_localiser_img = visualise_localisation_result(
                                    common_ground_map, 
                                    response.transform.data[2],
                                    response.transform.data[0], 
                                    response.transform.data[1],
                                    write_coords=False
                                )
                
                except ValueError as ve:
                    # Specific catch for tolerance rejection (do nothing, just retry)
                    pass 
                except Exception as e:
                    # Log other errors but keep running
                    localisation_client.get_logger().error(f"Localization update failed: {e}")
                
                finally:
                    # CRITICAL: Reset future to None so we can send a new request next loop
                    current_future = None
            
            else:
                # STATE C: REQUEST STILL RUNNING
                # Do nothing here. The loop continues, ensuring the map (Step 1)
                # keeps updating while the C++ node thinks.
                pass


# ---------------------------------------------------
# Initialize ROS2
# ---------------------------------------------------
def init_ros2():
    global ros_node, bot_pos_pub, obstacles_pub
    global command_sub, scan_sub, localisation_client, executor
    
    rclpy.init()
    
    # Create nodes
    ros_node = Node('lidar_vision_system')
    localisation_client = LocalisationClient()
    
    # --- Publishers ---
    bot_pos_pub = ros_node.create_publisher(PoseStamped, 'robot_pose', 10)
    obstacles_pub = ros_node.create_publisher(Float32MultiArray, '/obstacles', 10)
    
    # --- Subscribers ---
    command_sub = ros_node.create_subscription(
        Float32MultiArray, 'odom_delta', command_callback, 10
    )
    scan_sub = ros_node.create_subscription(
        LaserScan, 'scan', scan_callback, 10
    )
    
    # --- Executor Setup (The Fix) ---
    # Use one MultiThreadedExecutor for everything.
    # We increase threads to 4 to ensure the scan callback, odom callback, 
    # and service client response don't block each other.
    executor = MultiThreadedExecutor(num_threads=4)
    
    executor.add_node(ros_node)
    executor.add_node(localisation_client) # Add client to the SPINNING executor
    
    # Spin the executor in a background thread
    threading.Thread(target=lambda: executor.spin(), daemon=True).start()
    
    print("ROS2 initialized successfully")


# ---------------------------------------------------
# Main function
# ---------------------------------------------------
def main():
    init_ros2()
    
    localise_thread = threading.Thread(target=localisation_thread_func, daemon=True)
    localise_thread.start()
    localisation_client.get_logger().info("Started localization thread")
    
    try:
        while True:
            # Thread-safe copy of state
            with global_lock:
                current_bot_pos = bot_pos.copy()
                ground_map_to_show = latest_ground_map.copy() if latest_ground_map is not None else None
                localiser_img_to_show = latest_localiser_img.copy() if latest_localiser_img is not None else None
                current_obstacles = list(latest_obstacles_vis)
            
            # --- PUBLISH POSE ---
            pose_msg = PoseStamped()
            pose_msg.header.stamp = ros_node.get_clock().now().to_msg()
            pose_msg.header.frame_id = "map"
            pose_msg.pose.position.x = float(current_bot_pos[0])
            pose_msg.pose.position.y = float(current_bot_pos[1])
            q = get_quaternion_from_euler(current_bot_pos[2])
            pose_msg.pose.orientation.x, pose_msg.pose.orientation.y = q[0], q[1]
            pose_msg.pose.orientation.z, pose_msg.pose.orientation.w = q[2], q[3]
            bot_pos_pub.publish(pose_msg)
            
            # --- VISUALIZATION ---
            if ENABLE_VISUALIZATION:
                if ground_map_to_show is not None:
                    
                    # DRAW OBSTACLES
                    center_px = map_size_px / 2.0
                    for (cx, cy, r) in current_obstacles:
                        # Meters -> Pixels
                        px = int(center_px + cy * map_scale + LIDAR_OFFSET_X)
                        py = int(center_px - cx * map_scale)
                        radius_px = int(r * map_scale)
                        
                        # Draw Circle (Green) and Center (Red)
                        cv2.circle(ground_map_to_show, (px, py), radius_px, (100, 255, 100), 2)
                        cv2.circle(ground_map_to_show, (px, py), 3, (0, 0, 255), -1)

                    cv2.imshow("LiDAR Ground Map", ground_map_to_show)
                
                if localiser_img_to_show is not None:
                    cv2.imshow("Localization Result", localiser_img_to_show)
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            else:
                time.sleep(0.01)
            
            time.sleep(0.01)
    
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        if ENABLE_VISUALIZATION:
            cv2.destroyAllWindows()
        if ros_node is not None:
            ros_node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
