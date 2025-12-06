#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32MultiArray, MultiArrayDimension
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

# Robot & Physics
ROBOT_RADIUS = 0.25 
OBS_RADIUS = 0.15   
SAFETY_MARGIN = 0.1 
TOTAL_SAFE_DIST = ROBOT_RADIUS + OBS_RADIUS + SAFETY_MARGIN

LOOKAHEAD_DIST = 0.5
STEP_SIZE = 0.1    
CIRCLE_STEP_ANGLE = 0.1 

# HYSTERESIS CONFIG
HYSTERESIS_BONUS = 1.5  # Equivalent to ~85 degrees of arc preference to stick to previous decision

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
        [1.6, 1.5, 0.4, 1.5],
        [1.6, -0.5, 0.4, 1.5]
    ]
}

class SmartPathPlanner(Node):
    def __init__(self):
        super().__init__('smart_path_planner')

        self.sub_pose = self.create_subscription(PoseStamped, '/robot_pose', self.pose_callback, 10)
        self.sub_obs = self.create_subscription(Float32MultiArray, '/obstacles', self.obs_callback, 10)
        self.sub_target = self.create_subscription(Float32MultiArray, '/decision_target_data', self.target_callback, 10)
        
        self.sub_scan_update = self.create_subscription(Float32MultiArray, 'map/scan_points', self.scan_update_callback, 10)
        self.sub_path_update = self.create_subscription(Float32MultiArray, 'map/path_segments', self.path_update_callback, 10)
        self.sub_racks_update = self.create_subscription(Float32MultiArray, 'map/racks', self.racks_update_callback, 10)

        self.pub_path = self.create_publisher(Float32MultiArray, 'target_pos', 10)
        self.pub_distorted_scan = self.create_publisher(Float32MultiArray, '/distorted_scan_points', 10)

        self.robot_pose = None 
        self.obstacles = []    
        self.final_goal = None 
        self.stop_index = None
        
        self.scan_points = []
        self.raw_path_segments = []
        self.racks = [] 
        self.segment_constraints = [] 
        
        # --- NEW: Memory for Hysteresis ---
        # Key: (x_int, y_int), Value: 'ccw' or 'cw'
        self.obs_memory = {}
        self.active_obs_keys = set()
        # ----------------------------------
        
        self.load_config()

        self.base_path, self.face_modes, self.path_segment_indices = self.build_path()
        self.compute_line_constraints()

        self.active_path = self.base_path.copy()
        self.face_modes_active = self.face_modes.copy()

        self.timer = self.create_timer(0.05, self.control_loop)
        self.get_logger().info("Planner Initialized (Stable Hysteresis Logic)")

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

    def save_config(self):
        try:
            data = {
                "scan_points": [p.tolist() for p in self.scan_points],
                "path_segments": self.raw_path_segments,
                "racks": self.racks
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

    def obs_callback(self, msg):
        data = msg.data
        if len(data) < 1: return
        count = int(data[0])
        
        raw_obstacles = []
        for i in range(count):
            idx = 1 + (i * 2)
            if idx + 1 < len(data):
                raw_obstacles.append({
                    'pos': np.array([data[idx], data[idx+1]]),
                    'radius': TOTAL_SAFE_DIST
                })
        self.obstacles = self.merge_obstacles(raw_obstacles)

    def merge_obstacles(self, obstacles):
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
                        new_list.append({'pos': new_center, 'radius': new_radius})
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

    # ================= INTERIOR PROJECTION =================
    def process_distorted_scan_points(self):
        distorted_points = []
        for i, pt in enumerate(self.scan_points):
            current_pt = pt.copy()
            if i == 0 or i == len(self.scan_points) - 1:
                distorted_points.append(current_pt)
                continue
            
            if len(self.base_path) > 0:
                dists = np.linalg.norm(self.base_path - current_pt, axis=1)
                nearest_idx = np.argmin(dists)
                seg_idx = self.path_segment_indices[nearest_idx]
                
                constraint = self.segment_constraints[seg_idx]
                A, B, C = constraint['A'], constraint['B'], constraint['C']
                target_sign = constraint['sign']
                normal = np.array([A, B]) 
            else:
                normal = np.array([1.0, 0.0])
                target_sign = 1
                A, B, C = 1, 0, 0

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
        return distorted_points

    def publish_distorted_points(self, points):
        msg = Float32MultiArray()
        flat_list = []
        for p in points:
            flat_list.extend([float(p[0]), float(p[1])])
        msg.layout.dim = [MultiArrayDimension(label="points", size=len(flat_list), stride=2)]
        msg.data = flat_list
        self.pub_distorted_scan.publish(msg)

    # ================= ROBUST ARC GENERATION =================
    def generate_innermost_arc(self, obs, start_point, end_point):
        """
        Generates an arc around the obstacle.
        Uses hysteresis to prevent flickering between CCW and CW.
        """
        obs_center = obs['pos']
        safe_dist = obs['radius']

        # 1. Project start/end to circle
        start_vec = start_point - obs_center
        end_vec = end_point - obs_center
        p_start_circ = obs_center + (start_vec / np.linalg.norm(start_vec)) * safe_dist
        p_end_circ = obs_center + (end_vec / np.linalg.norm(end_vec)) * safe_dist

        ang_start = math.atan2(p_start_circ[1] - obs_center[1], p_start_circ[0] - obs_center[0])
        ang_end = math.atan2(p_end_circ[1] - obs_center[1], p_end_circ[0] - obs_center[0])

        ang_start = (ang_start + 2*math.pi) % (2*math.pi)
        ang_end = (ang_end + 2*math.pi) % (2*math.pi)

        # 2. Calculate Arc Lengths
        diff_ccw = (ang_end - ang_start) % (2*math.pi)
        diff_cw = (ang_start - ang_end) % (2*math.pi)

        # 3. Calculate "Inner" Bias (Preference for side closer to 0,0)
        # We calculate the midpoints of both potential arcs and see which is closer to arena center
        mid_ccw_ang = (ang_start + diff_ccw / 2.0)
        mid_cw_ang = (ang_start - diff_cw / 2.0)
        
        mid_ccw_pt = obs_center + np.array([math.cos(mid_ccw_ang), math.sin(mid_ccw_ang)]) * safe_dist
        mid_cw_pt = obs_center + np.array([math.cos(mid_cw_ang), math.sin(mid_cw_ang)]) * safe_dist
        
        dist_ccw_to_origin = np.linalg.norm(mid_ccw_pt)
        dist_cw_to_origin = np.linalg.norm(mid_cw_pt)

        # Base Cost = Arc Length + Penalty if far from center
        # We add a small penalty (0.5m equivalent) to the side that is further from center
        # This preserves your original intent to stay "inside" the path loop
        cost_ccw = diff_ccw + (0.5 if dist_ccw_to_origin > dist_cw_to_origin else 0.0)
        cost_cw = diff_cw + (0.5 if dist_cw_to_origin > dist_ccw_to_origin else 0.0)

        # 4. Apply Hysteresis (Memory)
        # Create a unique key for this obstacle based on 10cm grid snap
        obs_key = (int(round(obs_center[0], 1)*10), int(round(obs_center[1], 1)*10))
        self.active_obs_keys.add(obs_key) # Mark as active for this frame

        if obs_key in self.obs_memory:
            prev_decision = self.obs_memory[obs_key]
            if prev_decision == 'ccw':
                cost_ccw -= HYSTERESIS_BONUS # Make staying CCW much cheaper
            else:
                cost_cw -= HYSTERESIS_BONUS  # Make staying CW much cheaper

        # 5. Final Decision
        use_ccw = (cost_ccw < cost_cw)
        
        # Save decision for next frame
        self.obs_memory[obs_key] = 'ccw' if use_ccw else 'cw'

        # 6. Generate Points
        arc_points = []
        if use_ccw:
            diff = diff_ccw
            steps = max(int(diff / CIRCLE_STEP_ANGLE), 2)
            for i in range(steps + 1):
                a = ang_start + (diff * i / steps)
                arc_points.append(np.array([
                    obs_center[0] + safe_dist * math.cos(a),
                    obs_center[1] + safe_dist * math.sin(a)
                ]))
        else:
            diff = diff_cw
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
            self.obs_memory.clear() # Clear memory if no obstacles
            return

        # Prepare memory for this frame
        self.active_obs_keys = set()
        
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

        # Garbage Collection: Remove obstacles from memory that we didn't see this frame
        # This prevents the dict from growing indefinitely
        keys_to_remove = []
        for k in self.obs_memory:
            if k not in self.active_obs_keys:
                keys_to_remove.append(k)
        for k in keys_to_remove:
            del self.obs_memory[k]

    def control_loop(self):
        if self.robot_pose is None: return
        self.update_active_path()
        
        distorted_points = self.process_distorted_scan_points()
        self.publish_distorted_points(distorted_points)

        if self.final_goal is None:
             self.visualize(0, [], 1, distorted_points)
             return

        dists = np.linalg.norm(self.active_path - self.robot_pose[:2], axis=1)
        curr_idx = np.argmin(dists)
        path_len = len(self.active_path)

        is_closed = np.linalg.norm(self.active_path[0] - self.active_path[-1]) < 0.1

        stop_idx = path_len - 1
        if self.stop_index is not None:
            dists_to_goal = np.linalg.norm(self.active_path - self.final_goal, axis=1)
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
        
        if len(indices) < 1: return

        path_segment = self.active_path[indices]
        modes_segment = self.face_modes_active[indices]
        
        msg = Float32MultiArray()
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

            msg.data.extend([float(x), float(y), float(target_theta)])

        self.pub_path.publish(msg)
        self.visualize(curr_idx, path_segment, direction, distorted_points)

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

        cv2.imshow("Smart Planner - Stable", img)
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