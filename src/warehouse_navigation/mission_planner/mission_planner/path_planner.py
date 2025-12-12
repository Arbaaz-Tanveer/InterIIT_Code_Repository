#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32MultiArray, MultiArrayDimension, String, Bool
from geometry_msgs.msg import PoseStamped
import numpy as np
import math
import cv2
import os
import json

# ================= CONFIGURATION =================
ARENA_WIDTH_M = 4.5   
ARENA_HEIGHT_M = 6.5  
PIX_TO_METER = 100 
SEARCH_WINDOW = 50 # Number of points to search ahead/behind for tracking (hysteresis)    

# Robot & Physics
ROBOT_RADIUS = 0.25 
OBS_RADIUS = 0.15   
SAFETY_MARGIN = 0.15 
TOTAL_SAFE_DIST = ROBOT_RADIUS + OBS_RADIUS + SAFETY_MARGIN

# BOUNDARY_MARGIN Removed - replaced by dynamic obstacle_bound

LOOKAHEAD_DIST = 0.5
STEP_SIZE = 0.1    
CIRCLE_STEP_ANGLE = 0.1 

# ARRIVAL_THRESHOLD & THETA_THRESHOLD moved to config 

# --- OBSTACLE FILTERS & PERSISTENCE ---
OBS_IGNORE_BELOW_Y = -2.0           # Ignore individual obstacles detected below this Y
ROBOT_IGNORE_ALL_Y_THRESHOLD = -2.0 # If robot is below this Y, ignore ALL obstacles (Start Zone)

OBS_PERSISTENCE_TIMEOUT = 10.0       # Obstacles persist for 1.0s after detection stops
OBS_SMOOTHING_ALPHA = 0.3           # Smoothing factor (0.1 = Slow/Smooth, 1.0 = Instant)
OBS_MATCH_DIST = 0.2                # Max distance to match a new detection to a tracked obstacle

# --- MANUAL MODE LOGIC ---
TRANSITION_POINT = np.array([-1.2, -2.0]) # Point on the path to go to first if in start zone
TRANSITION_TOLERANCE = 0.3               # Distance to consider transition point reached
# -------------------------

# FILES
CONFIG_FILE = "planner_config.json"

DEFAULT_DATA = {
    "scan_points": [
        [1.285, -1.23],
        [0.0, -1.23],
        [-0.785, -0.7],
        [-0.785, 0.7],
        [0.0, 1.23],
        [1.285,-0.73]
  ],
    "path_segments": [
        [1.5, -2.7, -1.2, -2.7, 2], 
        [-1.2, -2.7, -1.2, 1.5, 2], 
        [-1.2, 1.5, 1.2, 1.5, 3],   
        [1.2, 1.5, 1.2, -1.5, 4],   
        [1.2, -1.5, -0.7, -1.5, 5],  
        [-0.7, -1.5, -0.7, -2.3, 5],   
        [-0.7, -2.3, 1.5, -2.3, 3] ,
        [1.5, -2.3, 1.5, -2.7, 4]
    ],
    "racks": [
        [-1.6, -0.5, 0.4, 1.5], 
        [-1.6, 1.5, 0.4, 1.5],
        [0.0, 2.1, 1.2, 0.4],
        [1.6, -0.5, 0.4, 1.5]
    ],
    "obstacle_bound": [-1.95, -2.95, 1.95, 2.95], # x1, y1, x2, y2 (Default safe zone)
    "arrival_threshold": 0.15,
    "theta_threshold": 0.1
}

class SmartPathPlanner(Node):
    def __init__(self):
        super().__init__('smart_path_planner')

        # Standard Subscriptions
        self.sub_pose = self.create_subscription(PoseStamped, '/robot_pose', self.pose_callback, 10)
        self.sub_obs = self.create_subscription(Float32MultiArray, '/obstacles', self.obs_callback, 10)
        self.sub_target = self.create_subscription(Float32MultiArray, '/decision_target_data', self.target_callback, 10)
        
        # Mode & Manual Control Subscriptions
        self.sub_auto_scan = self.create_subscription(String, '/auto_scan', self.auto_scan_callback, 10)
        self.sub_manual_pose = self.create_subscription(PoseStamped, '/manual_pose', self.manual_pose_callback, 10)
        
        # Map Updates
        self.sub_scan_update = self.create_subscription(Float32MultiArray, 'map/scan_points', self.scan_update_callback, 10)
        self.sub_path_update = self.create_subscription(Float32MultiArray, 'map/path_segments', self.path_update_callback, 10)

        self.sub_racks_update = self.create_subscription(Float32MultiArray, 'map/racks', self.racks_update_callback, 10)
        self.sub_obs_bound_update = self.create_subscription(Float32MultiArray, 'map/obstacle_bound', self.obstacle_bound_callback, 10)

        # Publishers
        self.pub_path = self.create_publisher(Float32MultiArray, 'target_pos', 10)
        self.pub_distorted_scan = self.create_publisher(Float32MultiArray, '/distorted_scan_points', 10)
        self.pub_motion = self.create_publisher(Bool, 'motion_active', 10)

        # State Variables
        self.robot_pose = None 
        
        # Obstacle Lists
        self.obstacles = []           # Final merged list for planning
        self.tracked_obstacles = []   # Internal list for persistence/smoothing
        
        # Planning State
        self.final_goal = None 
        self.stop_index = None
        
        # Mode State
        self.auto_mode = False          # False = Manual, True = Auto
        self.current_mode_name = "MANUAL"
        self.manual_target_pose = None  # [x, y, theta]
        self.going_to_transition = False
        self.last_path_idx = None       # For tracking hysteresis 
        
        # Map Data
        self.scan_points = []
        self.racks = [] 
        self.segment_constraints = [] 
        self.obstacle_bound = [] # [x1, y1, x2, y2]
        self.arrival_threshold = 0.15
        self.theta_threshold = 0.1
        
        self.load_config()

        self.base_path, self.face_modes, self.path_segment_indices = self.build_path()
        self.compute_line_constraints()

        self.active_path = self.base_path.copy()
        self.face_modes_active = self.face_modes.copy()

        self.timer = self.create_timer(0.05, self.control_loop)
        self.get_logger().info("Planner Initialized")

    def load_config(self):
        data = DEFAULT_DATA
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                self.get_logger().info(f"Loaded config from {CONFIG_FILE}")
            except Exception as e:
                self.get_logger().error(f"Failed to load JSON: {e}. Using defaults.")
        
        self.scan_points = [np.array(p) for p in data.get("scan_points", [])]
        self.raw_path_segments = data.get("path_segments", DEFAULT_DATA["path_segments"])
        self.racks = data.get("racks", DEFAULT_DATA["racks"])
        self.obstacle_bound = data.get("obstacle_bound", DEFAULT_DATA["obstacle_bound"])
        self.arrival_threshold = data.get("arrival_threshold", DEFAULT_DATA["arrival_threshold"])
        self.theta_threshold = data.get("theta_threshold", DEFAULT_DATA["theta_threshold"])
        self.current_scan_index = 0

    def save_config(self):
        try:
            data = {
                "scan_points": [p.tolist() for p in self.scan_points],
                "path_segments": self.raw_path_segments,
                "racks": self.racks,
                "obstacle_bound": self.obstacle_bound,
                "arrival_threshold": self.arrival_threshold,
                "theta_threshold": self.theta_threshold
            }
            with open(CONFIG_FILE, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            self.get_logger().error(f"Failed to save JSON: {e}")

    # ================= PRECOMPUTATION LOGIC =================
    def compute_line_constraints(self):
        self.segment_constraints = []
        ref_point = np.array([0.0, 0.0]) 

        for seg in self.raw_path_segments:
            x1, y1, x2, y2, _ = seg
            A = y1 - y2
            B = x2 - x1
            C = -A * x1 - B * y1
            
            norm = math.sqrt(A*A + B*B)
            if norm > 0:
                A, B, C = A/norm, B/norm, C/norm

            val = A * ref_point[0] + B * ref_point[1] + C
            interior_sign = 1 if val >= 0 else -1
            
            self.segment_constraints.append({
                'A': A, 'B': B, 'C': C, 
                'sign': interior_sign
            })

    def build_path(self):
        pts = []
        modes = []
        indices = [] 
        
        for i, segment in enumerate(self.raw_path_segments):
            x1, y1, x2, y2, mode = segment
            start = np.array([x1, y1])
            end = np.array([x2, y2])
            dist = np.linalg.norm(end - start)
            steps = int(max(dist / STEP_SIZE, 1))
            
            for s in range(steps):
                alpha = s / steps
                pts.append(start * (1 - alpha) + end * alpha)
                modes.append(mode)
                indices.append(i)
        
        if self.raw_path_segments:
            last_seg = self.raw_path_segments[-1]
            pts.append(np.array([last_seg[2], last_seg[3]]))
            modes.append(last_seg[4])
            indices.append(len(self.raw_path_segments) - 1)
        
        return np.array(pts), np.array(modes), np.array(indices)

    # ================= ROS CALLBACKS =================
    def pose_callback(self, msg):
        x = msg.pose.position.x
        y = msg.pose.position.y
        q = msg.pose.orientation
        siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
        cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
        theta = math.atan2(siny_cosp, cosy_cosp)
        self.robot_pose = np.array([x, y, theta])

    def auto_scan_callback(self, msg):
        cmd = msg.data.strip().upper()
        if cmd == "START":
            self.auto_mode = True
            self.current_mode_name = "AUTO"
            self.get_logger().info("MODE: AUTO")
        elif cmd == "COORDINATE":
            self.auto_mode = False 
            self.current_mode_name = "COORDINATE"
            self.manual_target_pose = None # Reset stale target
            self.going_to_transition = False # Reset transition logic
            
            # Send empty path to reset controller
            empty_msg = Float32MultiArray()
            self.pub_path.publish(empty_msg)
            
            self.get_logger().info("MODE: COORDINATE (Waiting for new target...)")
        elif cmd == "STOP":
            self.auto_mode = False
            self.current_mode_name = "MANUAL"
            
            # Send empty path to reset controller
            empty_msg = Float32MultiArray()
            self.pub_path.publish(empty_msg)
            
            self.get_logger().info("MODE: MANUAL")

    def manual_pose_callback(self, msg):
        x = msg.pose.position.x
        y = msg.pose.position.y
        
        # Quaternion to Theta
        q = msg.pose.orientation
        siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
        cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
        theta = math.atan2(siny_cosp, cosy_cosp)
        
        self.manual_target_pose = np.array([x, y, theta])
        
        # Logic: If receiving a new target, check if we need to use transition point
        # Condition 1: Robot is in Start Zone (Y < -2.0)
        # Condition 2: Target is Inside Arena (Y > -2.0)
        
        current_y = self.robot_pose[1] if self.robot_pose is not None else -3.0
        
        if current_y < ROBOT_IGNORE_ALL_Y_THRESHOLD and y > ROBOT_IGNORE_ALL_Y_THRESHOLD:
            self.going_to_transition = True
            self.get_logger().info(f"Coordinate Mode: Target Inside ({y:.2f}), Robot Outside ({current_y:.2f}). Going via Transition: {TRANSITION_POINT}")
        else:
            self.going_to_transition = False
            self.get_logger().info(f"Coordinate Mode: Going Direct: {x:.2f}, {y:.2f}")

    def obs_callback(self, msg):
        current_time = self.get_clock().now().nanoseconds / 1e9
        
        # 1. ZONE OVERRIDE: If robot is in the start zone, clear everything
        if self.robot_pose is not None:
            if self.robot_pose[1] < ROBOT_IGNORE_ALL_Y_THRESHOLD:
                self.obstacles = []
                self.tracked_obstacles = []
                return

        # 2. PARSE NEW DETECTIONS
        raw_detections = []
        data = msg.data
        if len(data) >= 1:
            count = int(data[0])
            for i in range(count):
                idx = 1 + (i * 2)
                if idx + 1 < len(data):
                    ox, oy = data[idx], data[idx+1]
                    
                    # Y-Level Filter
                    # Y-Level Filter
                    if oy > OBS_IGNORE_BELOW_Y:
                        # DYNAMIC BOUNDARY FILTER
                        # obstacle_bound is [x1, y1, x2, y2]
                        if len(self.obstacle_bound) == 4:
                            x_min = min(self.obstacle_bound[0], self.obstacle_bound[2])
                            x_max = max(self.obstacle_bound[0], self.obstacle_bound[2])
                            y_min = min(self.obstacle_bound[1], self.obstacle_bound[3])
                            y_max = max(self.obstacle_bound[1], self.obstacle_bound[3])
                            
                            if x_min <= ox <= x_max and y_min <= oy <= y_max:
                                raw_detections.append(np.array([ox, oy]))
                        else:
                             # Fallback if config is broken (should not happen with defaults)
                             raw_detections.append(np.array([ox, oy]))

        # 3. MATCHING & SMOOTHING
        # We try to match every new detection to an existing tracked obstacle
        used_track_indices = set()
        
        for raw_pos in raw_detections:
            best_idx = -1
            min_dist = OBS_MATCH_DIST

            # Find closest tracked obstacle
            for i, tracked in enumerate(self.tracked_obstacles):
                if i in used_track_indices: continue
                
                dist = np.linalg.norm(raw_pos - tracked['pos'])
                if dist < min_dist:
                    min_dist = dist
                    best_idx = i
            
            if best_idx != -1:
                # MATCH FOUND: Update position using Exponential Moving Average
                old_pos = self.tracked_obstacles[best_idx]['pos']
                
                # Smooth: New = (Alpha * Raw) + ((1-Alpha) * Old)
                smooth_pos = (raw_pos * OBS_SMOOTHING_ALPHA) + (old_pos * (1.0 - OBS_SMOOTHING_ALPHA))
                
                self.tracked_obstacles[best_idx]['pos'] = smooth_pos
                self.tracked_obstacles[best_idx]['last_seen'] = current_time
                used_track_indices.add(best_idx)
            else:
                # NO MATCH: Create new tracked obstacle
                self.tracked_obstacles.append({
                    'pos': raw_pos,
                    'radius': TOTAL_SAFE_DIST,
                    'last_seen': current_time
                })

        # 4. PRUNING (PERSISTENCE LOGIC)
        # Remove obstacles that haven't been seen for > TIMEOUT seconds
        active_list = []
        for obs in self.tracked_obstacles:
            if (current_time - obs['last_seen']) < OBS_PERSISTENCE_TIMEOUT:
                active_list.append(obs)
        
        self.tracked_obstacles = active_list

        # 5. MERGE FOR PLANNER
        # Send the smoothed, persistent list to the merger
        if self.tracked_obstacles:
            # We must pass a deep copy or rebuild the list to avoid reference issues during merge
            clean_list_for_merge = [{'pos': o['pos'].copy(), 'radius': o['radius']} for o in self.tracked_obstacles]
            self.obstacles = self.merge_obstacles(clean_list_for_merge)
        else:
            self.obstacles = []

    def merge_obstacles(self, obstacles):
        """Recursively merge intersecting obstacles."""
        merged = True
        current_obs_list = obstacles

        while merged:
            merged = False
            new_list = []
            skip_indices = set()

            for i in range(len(current_obs_list)):
                if i in skip_indices: continue
                
                obs1 = current_obs_list[i]
                merged_this_iter = False
                
                for j in range(i + 1, len(current_obs_list)):
                    if j in skip_indices: continue
                    
                    obs2 = current_obs_list[j]
                    dist = np.linalg.norm(obs1['pos'] - obs2['pos'])
                    
                    if dist < (obs1['radius'] + obs2['radius']):
                        new_center = (obs1['pos'] + obs2['pos']) / 2.0
                        new_radius = (dist / 2.0) + max(obs1['radius'], obs2['radius'])
                        
                        new_list.append({
                            'pos': new_center,
                            'radius': new_radius
                        })
                        skip_indices.add(i)
                        skip_indices.add(j)
                        merged = True
                        merged_this_iter = True
                        break 
                
                if not merged_this_iter:
                    new_list.append(obs1)
            
            if merged:
                current_obs_list = new_list
        
        return current_obs_list

    def target_callback(self, msg):
        self.final_goal = np.array([msg.data[0], msg.data[1]])
        dists = np.linalg.norm(self.base_path - self.final_goal, axis=1)
        self.stop_index = np.argmin(dists)

    def scan_update_callback(self, msg):
        new_points = []
        data = msg.data
        for i in range(0, len(data), 2):
            new_points.append(np.array([data[i], data[i+1]]))
        self.scan_points = new_points
        self.save_config() 

    def path_update_callback(self, msg):
        new_segments = []
        data = msg.data
        stride = 5
        for i in range(0, len(data), stride):
            if i + 4 < len(data):
                new_segments.append([
                    data[i], data[i+1], data[i+2], data[i+3], int(data[i+4])
                ])
        if new_segments:
            self.raw_path_segments = new_segments
            self.base_path, self.face_modes, self.path_segment_indices = self.build_path()
            self.compute_line_constraints() 
            self.save_config() 

    def racks_update_callback(self, msg):
        new_racks = []
        data = msg.data
        stride = 4
        for i in range(0, len(data), stride):
            if i + 3 < len(data):
                new_racks.append([data[i], data[i+1], data[i+2], data[i+3]])
        if new_racks:
            self.racks = new_racks
            self.save_config()

    def obstacle_bound_callback(self, msg):
        data = list(msg.data)
        if len(data) == 4:
             self.obstacle_bound = data
             self.save_config()
             self.get_logger().info(f"Updated Obstacle Bound: {self.obstacle_bound}")

    # ================= INTERIOR PROJECTION LOGIC =================
    def process_distorted_scan_points(self):
        distorted_points = []
        scan_point_thetas = []
        
        for i, pt in enumerate(self.scan_points):
            current_pt = pt.copy()
            target_theta = 0.0

            # Find Mode / Theta from Base Path
            if len(self.base_path) > 0:
                dists = np.linalg.norm(self.base_path - current_pt, axis=1)
                nearest_idx = np.argmin(dists)
                seg_idx = self.path_segment_indices[nearest_idx]
                
                # Get Mode from Segment
                # Segment: [x1, y1, x2, y2, mode]
                mode = self.raw_path_segments[seg_idx][4]
                if mode == 2: target_theta = math.pi
                elif mode == 3: target_theta = math.pi / 2
                elif mode == 4: target_theta = 0.0
                elif mode == 5: target_theta = -math.pi / 2
                
                constraint = self.segment_constraints[seg_idx]
                A, B, C = constraint['A'], constraint['B'], constraint['C']
                target_sign = constraint['sign']
                normal = np.array([A, B]) 
            else:
                normal = np.array([1.0, 0.0])
                target_sign = 1
                A, B, C = 1, 0, 0
            
            scan_point_thetas.append(target_theta)

            if i == 0 or i == len(self.scan_points) - 1:
                distorted_points.append(current_pt)
                continue
            
            for obs in self.obstacles:
                obs_pos = obs['pos']
                obs_r = obs['radius']
                
                d_vec = current_pt - obs_pos
                dist_sq = np.dot(d_vec, d_vec)
                safe_sq = obs_r**2
                
                if dist_sq < safe_sq:
                    dot_dn = np.dot(d_vec, normal)
                    c_term = dist_sq - safe_sq
                    delta = 4 * (dot_dn**2) - 4 * c_term
                    
                    if delta >= 0:
                        sqrt_delta = math.sqrt(delta)
                        k1 = (-2*dot_dn + sqrt_delta) / 2.0
                        k2 = (-2*dot_dn - sqrt_delta) / 2.0
                        
                        p1 = current_pt + k1 * normal
                        p2 = current_pt + k2 * normal
                        
                        val1 = A * p1[0] + B * p1[1] + C
                        sign1 = 1 if val1 >= 0 else -1
                        val2 = A * p2[0] + B * p2[1] + C
                        sign2 = 1 if val2 >= 0 else -1
                        
                        if sign1 == target_sign: current_pt = p1
                        elif sign2 == target_sign: current_pt = p2
                        else: current_pt = p1
                            
            distorted_points.append(current_pt)
            
        return distorted_points, scan_point_thetas

    def publish_distorted_points(self, points):
        msg = Float32MultiArray()
        flat_list = []
        for p in points:
            flat_list.extend([float(p[0]), float(p[1])])
        msg.layout.dim = [MultiArrayDimension(label="points", size=len(flat_list), stride=2)]
        msg.data = flat_list
        self.pub_distorted_scan.publish(msg)

    # ================= ARC GENERATION =================
    def generate_innermost_arc(self, obs, start_point, end_point):
        obs_center = obs['pos']
        safe_dist = obs['radius']

        start_vec = start_point - obs_center
        end_vec = end_point - obs_center
        
        p_start_circ = obs_center + (start_vec / np.linalg.norm(start_vec)) * safe_dist
        p_end_circ = obs_center + (end_vec / np.linalg.norm(end_vec)) * safe_dist

        ang_start = math.atan2(p_start_circ[1] - obs_center[1], p_start_circ[0] - obs_center[0])
        ang_end = math.atan2(p_end_circ[1] - obs_center[1], p_end_circ[0] - obs_center[0])

        ang_start = (ang_start + 2*math.pi) % (2*math.pi)
        ang_end = (ang_end + 2*math.pi) % (2*math.pi)

        A = p_start_circ[1] - p_end_circ[1]
        B = p_end_circ[0] - p_start_circ[0]
        C = -A * p_start_circ[0] - B * p_start_circ[1]

        ref_val = A * 0 + B * 0 + C
        ref_sign = 1 if ref_val >= 0 else -1

        if ang_end > ang_start: mid_ccw = (ang_start + ang_end) / 2.0
        else: mid_ccw = (ang_start + ang_end + 2*math.pi) / 2.0
        
        p_mid_ccw = np.array([
            obs_center[0] + safe_dist * math.cos(mid_ccw),
            obs_center[1] + safe_dist * math.sin(mid_ccw)
        ])
        
        mid_val = A * p_mid_ccw[0] + B * p_mid_ccw[1] + C
        mid_sign = 1 if mid_val >= 0 else -1

        use_ccw = (mid_sign == ref_sign)

        arc_points = []
        if use_ccw:
            diff = ang_end - ang_start
            if diff < 0: diff += 2*math.pi
            steps = max(int(diff / CIRCLE_STEP_ANGLE), 2)
            for i in range(steps + 1):
                a = ang_start + (diff * i / steps)
                arc_points.append(np.array([
                    obs_center[0] + safe_dist * math.cos(a),
                    obs_center[1] + safe_dist * math.sin(a)
                ]))
        else:
            diff = ang_start - ang_end
            if diff < 0: diff += 2*math.pi
            steps = max(int(diff / CIRCLE_STEP_ANGLE), 2)
            for i in range(steps + 1):
                a = ang_start - (diff * i / steps)
                arc_points.append(np.array([
                    obs_center[0] + safe_dist * math.cos(a),
                    obs_center[1] + safe_dist * math.sin(a)
                ]))
        
        return arc_points

    def update_active_path(self):
        if not self.obstacles:
            self.active_path = self.base_path.copy()
            self.face_modes_active = self.face_modes.copy()
            return

        collision_ranges = []
        path_len = len(self.base_path)

        start_static_point = self.scan_points[0]
        end_static_point = self.scan_points[-1]

        for obs in self.obstacles:
            obs_pos = obs['pos']
            obs_r = obs['radius']

            # STATIC ENDPOINT PROTECTION
            dist_start = np.linalg.norm(obs_pos - start_static_point)
            dist_end = np.linalg.norm(obs_pos - end_static_point)

            if dist_start < obs_r or dist_end < obs_r:
                continue

            # STANDARD COLLISION CHECK
            indices = []
            for i, pt in enumerate(self.base_path):
                if np.linalg.norm(pt - obs_pos) < obs_r:
                    indices.append(i)
            
            if not indices:
                continue

            min_idx = min(indices)
            max_idx = max(indices)

            if min_idx == 0 or max_idx == path_len - 1:
                continue

            if min_idx <= max_idx:
                collision_ranges.append((min_idx, max_idx, obs))

        collision_ranges.sort(key=lambda x: x[0])

        new_path = []
        new_modes = []
        current_base_idx = 0
        
        for r_start, r_end, obs in collision_ranges:
            if r_start < current_base_idx:
                continue
            
            while current_base_idx < r_start:
                new_path.append(self.base_path[current_base_idx])
                new_modes.append(self.face_modes[current_base_idx])
                current_base_idx += 1
            
            anchor_start = self.base_path[r_start - 1] 
            anchor_end = self.base_path[r_end + 1]

            arc_pts = self.generate_innermost_arc(obs, anchor_start, anchor_end)
            
            ref_mode = self.face_modes[r_start] 
            for apt in arc_pts:
                new_path.append(apt)
                new_modes.append(ref_mode)
            
            current_base_idx = r_end + 1
            
        while current_base_idx < path_len:
            new_path.append(self.base_path[current_base_idx])
            new_modes.append(self.face_modes[current_base_idx])
            current_base_idx += 1

        self.active_path = np.array(new_path)
        self.face_modes_active = np.array(new_modes)

    def control_loop(self):
        if self.robot_pose is None: return
        self.update_active_path()
        
        distorted_points, scan_thetas = self.process_distorted_scan_points()
        self.publish_distorted_points(distorted_points)

        # === 1. DETERMINE TARGET AND PATH STRATEGY ===
        active_target_goal = None
        use_straight_line = False
        
        if self.auto_mode:
            # AUTO MODE: Use target from main.py via /decision_target_data
            active_target_goal = self.final_goal
        else:
            # MANUAL MODE
            if self.manual_target_pose is None:
                self.visualize(0, [], 1, distorted_points)
                return # No target yet

            # Check if we reached transition point
            dist_to_trans = np.linalg.norm(self.robot_pose[:2] - TRANSITION_POINT)
            
            # Debug log to see why it might be stuck
            if self.going_to_transition:
                 self.get_logger().info(f"Dist to transition: {dist_to_trans:.2f} (Tol: {TRANSITION_TOLERANCE})")

            # If we were going to transition and just reached it, clear the flag
            # Increased local tolerance to ensuring triggering
            if self.going_to_transition and dist_to_trans < 0.5:
                self.going_to_transition = False
                self.get_logger().info("Transition Point Reached. Going Direct.")

            if self.going_to_transition:
                # Follow existing path to transition point
                active_target_goal = TRANSITION_POINT
            else:
                # Go straight to manual target
                use_straight_line = True
                active_target_goal = self.manual_target_pose[:2]

        if active_target_goal is None and not use_straight_line:
             self.visualize(0, [], 1, distorted_points)
             # If no target in manual mode, ensure we stop
             if not self.auto_mode:
                 m = Bool()
                 m.data = False
                 self.pub_motion.publish(m)
             return

        # === 2. GENERATE PATH ===
        path_msg_points = []
        viz_segment = []
        curr_idx = 0
        direction = 1

        # CHECK ARRIVAL (Coordinate Mode)
        if not self.auto_mode and self.manual_target_pose is not None:
             # Check if we are close enough to the MANUAL TARGET
             # Note: active_target_goal might be transition point, so we check the FINAL manual target?
             # Actually, if going via transition, we first reach transition, then switch to final.
             # So we should check arrival at 'active_target_goal'.
             
             dist_to_current_goal = np.linalg.norm(self.robot_pose[:2] - active_target_goal)
             
             # Calculate Theta Diff
             # If target is transition, we don't care about theta? Usually we don't.
             # If target is Final Manual Pose, we care about theta.
             
             theta_error = 0.0
             if not self.going_to_transition:
                 # Final Target
                 desired_th = self.manual_target_pose[2]
                 diff = desired_th - self.robot_pose[2]
                 # Normalize
                 while diff > math.pi: diff -= 2*math.pi
                 while diff < -math.pi: diff += 2*math.pi
             theta_error = 0.0
             if not self.going_to_transition:
                 # Final Target
                 desired_th = self.manual_target_pose[2]
                 diff = desired_th - self.robot_pose[2]
                 # Normalize
                 while diff > math.pi: diff -= 2*math.pi
                 while diff < -math.pi: diff += 2*math.pi
                 theta_error = abs(diff)
             
             if dist_to_current_goal < self.arrival_threshold and theta_error < self.theta_threshold:
                  # Reached
                  if self.going_to_transition:
                      # If we were going to transition and reached it, loop will handle switching in next iter
                      # But for now, we still consider it "motion active" until logic flips valid target
                      pass 
                  else:
                      # Final goal reached
                      self.get_logger().info("Target Reached (XY + Theta). Stopping.")
                      # Clear target so we don't keep trying
                      self.manual_target_pose = None
                      
                      # Stop
                      m = Bool()
                      m.data = False
                      self.pub_motion.publish(m)
                      
                      # Publish empty path
                      empty = Float32MultiArray()
                      self.pub_path.publish(empty)
                      
                      self.visualize(0, [], 1, distorted_points)
                      return

        if use_straight_line:
            # --- STRAIGHT LINE GENERATION ---
            start = self.robot_pose[:2]
            end = active_target_goal
            vec = end - start
            dist = np.linalg.norm(vec)
            if dist > 0:
                vec = vec / dist
            
            # Generate a simple straight path of LOOKAHEAD_DIST
            steps = int(LOOKAHEAD_DIST / STEP_SIZE) + 1
            for i in range(1, steps + 1):
                p = start + vec * (i * STEP_SIZE)
                # If we overshoot the target, clamp to target
                if np.linalg.norm(p - start) > dist:
                    p = end
                
                # Theta is simply the angle to target, or final theta if close
                target_theta = math.atan2(vec[1], vec[0])
                
                # If very close to end, use manual orientation
                if np.linalg.norm(p - end) < 0.1:
                    target_theta = self.manual_target_pose[2]

                path_msg_points.append([p[0], p[1], target_theta])
                viz_segment.append(p)
                
        else:
            # --- EXISTING PATH FOLLOWING LOGIC ---
            
            # 1. Update Current Index with Hysteresis (Local Window)
            path_len = len(self.active_path)
            
            if self.last_path_idx is None or self.last_path_idx >= path_len:
                # First run or reset: Search Global
                dists = np.linalg.norm(self.active_path - self.robot_pose[:2], axis=1)
                curr_idx = np.argmin(dists)
            else:
                # Tracking: Search Local Window
                start_search = self.last_path_idx - SEARCH_WINDOW
                end_search = self.last_path_idx + SEARCH_WINDOW
                
                # Handle cyclic indices if needed, or clamping
                # Since we don't know if path is truly cyclic, simple clamping or modulo is tricky
                # safe approach: generate verify indices list
                search_indices = []
                for k in range(start_search, end_search + 1):
                    # modulo for closed loops, or clamp for open?
                    # let's use modulo if closed, clamp if open
                    if np.linalg.norm(self.active_path[0] - self.active_path[-1]) < 0.1:
                         search_indices.append(k % path_len)
                    else:
                         if 0 <= k < path_len:
                             search_indices.append(k)
                
                # Find best in window
                best_local_dist = 1e9
                best_local_idx = self.last_path_idx
                
                for k in search_indices:
                    d = np.linalg.norm(self.active_path[k] - self.robot_pose[:2])
                    if d < best_local_dist:
                        best_local_dist = d
                        best_local_idx = k
                
                curr_idx = best_local_idx

            self.last_path_idx = curr_idx # Update tracking memory
            path_len = len(self.active_path)
            is_closed = np.linalg.norm(self.active_path[0] - self.active_path[-1]) < 0.1

            stop_idx = path_len - 1
            if active_target_goal is not None:
                dists_to_goal = np.linalg.norm(self.active_path - active_target_goal, axis=1)
                stop_idx = np.argmin(dists_to_goal)

            direction = 1
            if is_closed:
                forward_dist = (stop_idx - curr_idx + path_len) % path_len
                backward_dist = (curr_idx - stop_idx + path_len) % path_len
                if backward_dist < forward_dist:
                    direction = -1
            else:
                if stop_idx < curr_idx:
                    direction = -1

            points_count = int(LOOKAHEAD_DIST / STEP_SIZE)
            indices = []
            idx = curr_idx
            
            for _ in range(points_count + 1):
                indices.append(idx)
                if idx == stop_idx: break
                idx += direction
                if is_closed: idx = idx % path_len
                else:
                    if idx < 0 or idx >= path_len: break
            
            if len(indices) > 0:
                path_segment = self.active_path[indices]
                modes_segment = self.face_modes_active[indices]
                viz_segment = path_segment
                
                for i, pt in enumerate(path_segment):
                    x, y = pt
                    mode = modes_segment[i]
                    target_theta = 0.0
                    
                    if mode == 2: target_theta = math.pi       
                    elif mode == 3: target_theta = math.pi / 2 
                    elif mode == 4: target_theta = 0.0         
                    elif mode == 5: target_theta = -math.pi / 2 
                    else:
                        if i < len(path_segment)-1:
                            dx = path_segment[i+1][0] - x
                            dy = path_segment[i+1][1] - y
                            if abs(dx) > 0.001 or abs(dy) > 0.001:
                                target_theta = math.atan2(dy, dx)
                                if direction == -1: target_theta += math.pi

                    # === SCAN POINT THETA OVERRIDE ===
                    # Check if this point on path is near a Distorted Scan Point
                    # If so, force the target theta to match the Scan Point's requirement
                    for s_chk_i, s_viz_pt in enumerate(distorted_points):
                        if s_chk_i < len(scan_thetas):
                            dist_s = np.linalg.norm(s_viz_pt - pt)
                            # Threshold: 0.2m (tune as needed)
                            if dist_s < 0.2:
                                target_theta = scan_thetas[s_chk_i]
                                break
                    
                    path_msg_points.append([float(x), float(y), float(target_theta)])

        # === 3. PUBLISH ===
        msg = Float32MultiArray()
        for p in path_msg_points:
            msg.data.extend([float(p[0]), float(p[1]), float(p[2])])
        self.pub_path.publish(msg)
        
        # Enable Motion in Coordinate Mode since we have a valid path
        if not self.auto_mode:
            m = Bool()
            m.data = True
            self.pub_motion.publish(m)
        
        self.visualize(curr_idx, viz_segment, direction, distorted_points)

    def visualize(self, curr_idx, local_segment, direction, distorted_points):
        h = int(ARENA_HEIGHT_M * PIX_TO_METER)
        w = int(ARENA_WIDTH_M * PIX_TO_METER)
        img = np.ones((h, w, 3), dtype=np.uint8) * 255 

        def to_pix(pt):
            cx = w // 2
            cy = h // 2
            px = int(cx + (pt[0] * PIX_TO_METER))
            py = int(cy - (pt[1] * PIX_TO_METER))
            return (px, py)

        cx, cy = to_pix((0,0))
        cv2.line(img, (cx, 0), (cx, h), (220, 220, 220), 1) 
        cv2.line(img, (0, cy), (w, cy), (220, 220, 220), 1) 
        
        for rx, ry, rw, rh in self.racks:
            tl_r = to_pix((rx - rw/2, ry + rh/2))
            br_r = to_pix((rx + rw/2, ry - rh/2))
            cv2.rectangle(img, tl_r, br_r, (120, 120, 120), -1)

        # DRAW DYNAMIC BOUNDARY MARGIN
        if len(self.obstacle_bound) == 4:
            x1, y1, x2, y2 = self.obstacle_bound
            p1 = to_pix((x1, y1))
            p2 = to_pix((x2, y2))
            # cv2.rectangle handles any corner order
            cv2.rectangle(img, p1, p2, (0, 255, 255), 1) # Yellow border for safe zone

        if len(self.base_path) > 1:
            pts = np.array([to_pix(p) for p in self.base_path], np.int32)
            cv2.polylines(img, [pts], False, (200, 200, 200), 2)
        
        if len(self.active_path) > 1:
            pts = np.array([to_pix(p) for p in self.active_path], np.int32)
            cv2.polylines(img, [pts], False, (255, 200, 0), 2) 
        
        if len(local_segment) > 1:
            pts = np.array([to_pix(p) for p in local_segment], np.int32)
            color = (0, 200, 0) if direction == 1 else (0, 100, 255)
            cv2.polylines(img, [pts], False, color, 3)

        for obs in self.obstacles:
            c = to_pix(obs['pos'])
            cv2.circle(img, c, 5, (255, 0, 0), -1) 
            cv2.circle(img, c, int(obs['radius']*PIX_TO_METER), (255, 200, 200), 1)

        for pt in self.scan_points:
            cv2.circle(img, to_pix(pt), 3, (0, 0, 0), -1)
            
        for i, pt in enumerate(distorted_points):
            orig = self.scan_points[i]
            if np.linalg.norm(pt - orig) > 0.01:
                pix_new = to_pix(pt)
                pix_orig = to_pix(orig)
                cv2.line(img, pix_orig, pix_new, (200, 0, 200), 1)
                cv2.circle(img, pix_new, 5, (255, 0, 255), -1)

        if self.robot_pose is not None:
            pt = to_pix(self.robot_pose[:2])
            cv2.circle(img, pt, int(0.2*PIX_TO_METER), (0, 0, 255), 2)
            th = self.robot_pose[2]
            end = (int(pt[0] + 30*math.cos(th)), int(pt[1] - 30*math.sin(th)))
            cv2.line(img, pt, end, (0,0,255), 3)

        # Status Overlay
        status = self.current_mode_name
        if not self.auto_mode and self.going_to_transition:
            status += " (TRANSITION)"
        elif not self.auto_mode and self.manual_target_pose is not None:
            status += " (ACTIVE)"
            
        cv2.putText(img, status, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        cv2.imshow("Smart Planner", img)
        cv2.waitKey(1)

def main(args=None):
    rclpy.init(args=args)
    node = SmartPathPlanner()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt: pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
        cv2.destroyAllWindows()

if __name__ == '__main__':
    main()
