#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Bool, Float32MultiArray, Int32MultiArray, Float32
from geometry_msgs.msg import PoseStamped
import math
import time
import json
import os

# Thresholds & Timers
# Thresholds & Timers
# ARRIVAL_THRESHOLD = 0.07   # Moved to config
# THETA_THRESHOLD = 0.05     # Moved to config
CONFIG_FILE = "planner_config.json"
SETTLE_TIME = 1.0          # Seconds to wait to stabilize
STOP_POINT_WAIT_TIME = 5.0 # Seconds to wait at the last point (No Scan)
COOLDOWN_TIME = 10.0       # Seconds to wait at Start before restart

# Rack Configuration
POINTS_PER_RACK = 3        # Number of scan points per rack
ZSCAN_LOWER = 20.0
ZSCAN_UPPER = 170.0

class WarehouseManager(Node):
    def __init__(self):
        super().__init__('warehouse_manager')

        # --- SUBSCRIBERS ---
        self.sub_points = self.create_subscription(
            Float32MultiArray, '/distorted_scan_points', self.points_callback, 10)
        
        self.sub_pose = self.create_subscription(
            PoseStamped, '/robot_pose', self.pose_callback, 10)
        
        self.sub_autoscan = self.create_subscription(
            String, 'auto_scan', self.autoscan_callback, 10)
        
        self.sub_zscan_status = self.create_subscription(
            Bool, 'zscan_active', self.zscan_status_callback, 10)

        self.sub_restart = self.create_subscription(
            Bool, 'restart', self.restart_callback, 10)

        # --- UPDATED: Multi-Rack Subscriber ---
        # --- UPDATED: Multi-Rack Subscriber ---
        self.sub_scan_rack = self.create_subscription(
            Int32MultiArray, 'scan_rack', self.scan_rack_callback, 10)
            
        self.sub_zscan_manual = self.create_subscription(
            Float32, 'zscan_manual', self.zscan_manual_callback, 10)

        # --- UPDATED: Path Subscriber for Theta ---
        self.sub_path = self.create_subscription(
            Float32MultiArray, 'target_pos', self.path_callback, 10)

        # --- PUBLISHERS ---
        self.pub_target = self.create_publisher(
            Float32MultiArray, '/decision_target_data', 10)
        
        self.pub_motion = self.create_publisher(
            Bool, 'motion_active', 10)
        
        self.pub_zscan_trigger = self.create_publisher(
            Bool, 'zscan', 10)
            
        self.pub_session = self.create_publisher(
            String, 'session_control', 10)

        # --- INTERNAL STATE ---
        self.points = []          
        self.robot_pose = None    
        self.autoscan_on = False  
        self.zscan_busy = False 
        self.current_z_cm = ZSCAN_LOWER  # Assume 20 on startup (due to calib)
        self.target_z_end = None # 'TOP' or 'BOTTOM' for the actual scan move
        self.scanner_at_top = False # Track logical position (False=Bottom, True=Top)
        
        # Path Tracking State
        self.current_path_target_theta = None
        
        # State Machine
        self.state = "IDLE"
        self.target_idx = 1       
        self.timer_start_time = 0.0
        
        # Execution Control
        self.scan_limit_idx = -1  # -1 means run to end
        self.rack_queue = []      # Queue for rack sequence [1, 2, 3...]
        
        # Thresholds (Defaults)
        self.arrival_threshold = 0.07
        self.theta_threshold = 0.05

        # Load initial points
        self.load_initial_points()

        self.create_timer(0.1, self.control_loop) 
        self.get_logger().info(f"Warehouse Manager Ready. Racks defined with {POINTS_PER_RACK} point(s) each.")

    def load_initial_points(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    self.points = data.get("scan_points", [])
                    self.arrival_threshold = data.get("arrival_threshold", 0.07)
                    self.theta_threshold = data.get("theta_threshold", 0.05)
                    self.get_logger().info(f"Loaded {len(self.points)} initial points. Thresh: Dist={self.arrival_threshold}, Theta={self.theta_threshold}")
            except Exception as e:
                self.get_logger().error(f"Failed to load JSON: {e}")
        else:
            self.get_logger().warn(f"Config file {CONFIG_FILE} not found.")

    def start_new_cycle(self):
        """Restart the full autoscan loop after cooldown."""
        # Reset state
        self.target_idx = 1
        self.scan_limit_idx = -1   # full loop mode
        self.state = "MOVING"
        self.set_motion(True)
        self.get_logger().info("🔄 New autoscan cycle started. Heading to Point 1.")
        
        # Signal new session for CSV logging
        session_msg = String()
        session_msg.data = "NEW"
        self.pub_session.publish(session_msg)

    # ================= CALLBACKS =================
    def restart_callback(self, msg):
        if msg.data: 
            self.get_logger().warn("⚠️ RESTART TRIGGERED! Aborting.")
            self.autoscan_on = False 
            self.stop_robot()        
            self.state = "FORCE_RETURN" 
            self.scan_limit_idx = -1 # Reset limit
            self.rack_queue = []     # Clear queue
            self.get_logger().info("Queue Cleared. Returning to Start Position...")

    def scan_rack_callback(self, msg):
        """Receives array [1, 2, 3] and executes sequentially."""
        requested_racks = list(msg.data)
        if not requested_racks:
            return

        if len(self.points) < 2:
            self.get_logger().warn("No scan points loaded.")
            return

        self.rack_queue = requested_racks
        self.get_logger().info(f"Received Rack Sequence: {self.rack_queue}")
        
        # Start the first one immediately
        self.process_next_rack_in_queue()

    def process_next_rack_in_queue(self):
        if not self.rack_queue:
            self.get_logger().info("Rack Queue Empty. Sequence Complete.")
            self.autoscan_on = False
            self.state = "IDLE"
            self.stop_robot()
            return

        next_rack = self.rack_queue.pop(0)
        
        # Index 0 is Start. Index 1 is Rack 1 Point 1.
        start_idx = 1 + (next_rack - 1) * POINTS_PER_RACK
        limit_idx = start_idx + POINTS_PER_RACK
        max_valid_idx = len(self.points) - 1 
        
        if start_idx >= max_valid_idx:
            self.get_logger().warn(f"Rack {next_rack} invalid (Indices out of range). Skipping.")
            self.process_next_rack_in_queue() # Try next
            return

        self.target_idx = start_idx
        self.scan_limit_idx = min(limit_idx, max_valid_idx)
        
        self.autoscan_on = True
        self.state = "MOVING"
        self.set_motion(True)
        self.get_logger().info(f"Processing Rack {next_rack}. Start: {self.target_idx}, Stop Before: {self.scan_limit_idx}")

    def points_callback(self, msg):
        new_points = []
        data = msg.data
        for i in range(0, len(data), 2):
            if i+1 < len(data):
                new_points.append([data[i], data[i+1]])
        if len(new_points) > 0:
            self.points = new_points

    def pose_callback(self, msg):
        q = msg.pose.orientation
        siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
        cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
        theta = math.atan2(siny_cosp, cosy_cosp)
        self.robot_pose = [msg.pose.position.x, msg.pose.position.y, theta]

    def autoscan_callback(self, msg):
        cmd = msg.data
        if cmd == "START":
            if not self.autoscan_on:
                self.get_logger().info("AUTOSCAN ON (Full Loop Mode).")
                self.autoscan_on = True
                self.scan_limit_idx = -1 # Full loop
                self.rack_queue = []     # Clear specific rack requests
                
                
                if self.state == "IDLE":
                    # Determine Session Type
                    # If target_idx is 1 (Start) or 0 (Uninit?), it's a NEW session.
                    # Otherwise, we are resuming from a later point.
                    is_new_session = (self.target_idx <= 1)
                    session_msg = String()
                    session_msg.data = "NEW" if is_new_session else "RESUME"
                    self.pub_session.publish(session_msg)
                    self.get_logger().info(f"Session Control: {session_msg.data} (Idx: {self.target_idx})")

                    if self.target_idx >= len(self.points) - 1 or self.target_idx == 0:
                        self.target_idx = 1
                    self.state = "MOVING"
                    self.set_motion(True)

        elif cmd == "COORDINATE":
            self.get_logger().info("COORDINATE MODE ENABLED. Autoscan Loop Disabled.")
            self.autoscan_on = False
            self.state = "IDLE"
            self.rack_queue = []
            self.stop_robot()

        elif cmd == "STOP":
            self.get_logger().info("AUTOSCAN DISABLED. Stopping.")
            self.autoscan_on = False
            self.state = "IDLE"
            self.rack_queue = []
            self.stop_robot()

    def zscan_status_callback(self, msg):
        self.zscan_busy = msg.data

    def zscan_manual_callback(self, msg):
        # Keep track of where the scanner is, roughly
        self.current_z_cm = msg.data

    def path_callback(self, msg):
        # target_pos is [x, y, theta, x, y, theta...]
        # We want the theta of the LAST point in the path, as that is the final orientation for this segment.
        data = msg.data
        if len(data) >= 3:
            # Last 3 elements are [x, y, theta]
            self.current_path_target_theta = data[-1]
        else:
            self.current_path_target_theta = None

    # ================= HELPERS =================
    def publish_target(self, point):
        msg = Float32MultiArray()
        msg.data = [float(point[0]), float(point[1])]
        self.pub_target.publish(msg)

    def set_motion(self, active: bool):
        msg = Bool()
        msg.data = active
        self.pub_motion.publish(msg)

    def trigger_zscan(self, value: bool):
        msg = Bool()
        msg.data = value
        self.pub_zscan_trigger.publish(msg)
        mode_str = "TOP (1)" if value else "BOTTOM (0)"
        self.get_logger().info(f"Setting Z-Scan to {mode_str}")
        # Update internal state approximation immediately
        self.current_z_cm = ZSCAN_UPPER if value else ZSCAN_LOWER

    def stop_robot(self):
        self.set_motion(False)

    def get_distance(self, p1, p2):
        return math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)

    # ================= MAIN LOOP =================
    def control_loop(self):
        if not self.autoscan_on and self.state != "FORCE_RETURN":
            return 
        
        if self.robot_pose is None or not self.points: 
            return 

        # --- CHECK SCAN LIMIT (For Single/Sequence Rack Mode) ---
        if self.scan_limit_idx != -1 and self.target_idx >= self.scan_limit_idx:
            # Current Rack Done. Check Queue.
            self.get_logger().info(f"Rack Finished.")
            self.process_next_rack_in_queue()
            return

        # --- STATE: FORCE_RETURN ---
        if self.state == "FORCE_RETURN":
            target = self.points[0] 
            self.publish_target(target)
            self.set_motion(True)
            
            target = self.points[0] 
            self.publish_target(target)
            self.set_motion(True)
            
            dist = self.get_distance(self.robot_pose, target)
            if dist < self.arrival_threshold:
                # CHECK THETA THRESHOLD
                arrived = True
                
                if self.current_path_target_theta is not None:
                     current_theta = self.robot_pose[2]
                     diff = self.current_path_target_theta - current_theta
                     while diff > math.pi: diff -= 2*math.pi
                     while diff < -math.pi: diff += 2*math.pi
                     
                     while diff > math.pi: diff -= 2*math.pi
                     while diff < -math.pi: diff += 2*math.pi
                     
                     if abs(diff) > self.theta_threshold:
                         arrived = False

                if arrived:
                    self.set_motion(False)
                    self.trigger_zscan(False) 
                    self.target_idx = 1 
                    self.get_logger().info("Restart Complete. At Start.")
                    self.state = "IDLE"
            return 

        # --- STATE: MOVING ---
        if self.state == "MOVING":
            if self.target_idx >= len(self.points):
                self.state = "RETURNING"
                return

            target = self.points[self.target_idx]
            self.publish_target(target)
            self.set_motion(True) 

            dist = self.get_distance(self.robot_pose, target)
            
            # Check Theta (Assume target theta is 0? Or do we care? 
            # Ideally points should have theta, but current json is [x,y]. 
            # If no target theta, maybe skip? 
            # BUT user asked for arrival threshold. 
            # Let's assume we align to path or just checking stability? 
            # Actually, autoscan usually implies forward motion along a path.
            # If we don't have a target theta, applying a threshold is tricky.
            # However, for consistency with request "apply THETA_THRESHOLD so robot stops when all x,y,theta inside",
            # we need a target theta. 
            # Autoscan points are just points. The path planner generates the theta (tangent to path).
            # So main.py doesn't really know the target theta unless we assume something.
            # If the user insists, maybe they mean stability (d_theta ~ 0)? 
            # Or maybe they mean alignment to the vector?
            # Re-reading: "apply THETA_THRESHOLD = 0.1 radians so that the robot stops when all x, y, theta are inside the threshold"
            # This implies there IS a target theta.
            # Since self.points are just [x, y], let's assume we want to stabilize orientation?
            # Or maybe we just skip theta check here if we don't have it, but complying strictly might mean
            # we need to infer it. 
            # Safest is to just check distance for autoscan if theta is undefined, BUT
            # user specifically asked for it in main.py.
            # Let's check if the robot has stopped turning (omega ~ 0)? No, user said "inside threshold" implies error.
            # Given we only have X,Y points, maybe we don't enforce theta for intermediate points?
            # Wait, user request was "in coordinate mode... also as you are applying ARRIVAL_THRESHOLD in main.py...".
            # The coordinate mode fix was for path_planner. The threshold request was for main.py (Autoscan).
            # If autoscan points don't have theta, we can't check error.
            # PROPOSAL: We will check theta error relative to 0 or previous segment?
            # Actually, standard behavior for waypoints is usually "reach within radius".
            # If I add theta check without target theta, I break it.
            # I will check if points have 3 elements. If not, I will ignore theta check to prevent bug, 
            # but I'll add the logic to support it if they do.
            # User might be adding 3rd element later? OR they might mean Coordinate Mode logic in path_planner (which I did).
            # But they said "apply ... in main.py".
            # Let's assume NO THETA check for intermediate points if data is missing, to be safe.
            # Update: I will just use distance check as before if no theta.
             
            # Wait, `get_distance` uses [0] and [1]. My `robot_pose` is now 3 elements. ensure get_distance works.
                       
            dist = self.get_distance(self.robot_pose, target) # Re-calc dist
            if dist < self.arrival_threshold:
                # CHECK THETA THRESHOLD
                arrived = True
                
                if self.current_path_target_theta is not None:
                     # Calculate diff
                     current_theta = self.robot_pose[2]
                     diff = self.current_path_target_theta - current_theta
                     # Normalize
                     while diff > math.pi: diff -= 2*math.pi
                     while diff < -math.pi: diff += 2*math.pi
                     
                     while diff > math.pi: diff -= 2*math.pi
                     while diff < -math.pi: diff += 2*math.pi
                     
                     if abs(diff) > self.theta_threshold:
                         arrived = False
                         # Optional: Log occasionally?
                         # self.get_logger().info(f"Dist OK, but Angle Diff {diff:.2f} > {THETA_THRESHOLD}")

                if arrived:
                    self.state = "SETTLING"
                    self.timer_start_time = time.time()
                    is_last_point = (self.target_idx == len(self.points) - 1)
                    
                    if is_last_point:
                        self.get_logger().info(f"Arrived at FINAL Point {self.target_idx}.")
                    else:
                        self.get_logger().info(f"Arrived at Point {self.target_idx}.")

        # --- STATE: SETTLING ---
        elif self.state == "SETTLING":
            target = self.points[self.target_idx]
            self.publish_target(target)
            self.set_motion(True)

            elapsed = time.time() - self.timer_start_time
            if elapsed > SETTLE_TIME:
                if self.target_idx == len(self.points) - 1:
                    self.state = "WAIT_AT_LAST"
                    self.set_motion(False)
                    self.timer_start_time = time.time()
                    self.get_logger().info(f"Stop Point. Waiting {STOP_POINT_WAIT_TIME}s.")
                else:
                    self.state = "START_SCAN"

        # --- STATE: WAIT_AT_LAST ---
        elif self.state == "WAIT_AT_LAST":
            self.set_motion(False)
            elapsed = time.time() - self.timer_start_time
            if elapsed > STOP_POINT_WAIT_TIME:
                self.state = "RETURNING"
                self.set_motion(True)
                self.get_logger().info("Wait complete. Returning to Start.")

        # --- STATE: START_SCAN ---
        elif self.state == "START_SCAN":
            self.set_motion(False)
            
            # Check if we are already at an end (Tolerance 5cm)
            dist_lower = abs(self.current_z_cm - ZSCAN_LOWER)
            dist_upper = abs(self.current_z_cm - ZSCAN_UPPER)
            is_at_lower = dist_lower < 5.0
            is_at_upper = dist_upper < 5.0
            
            if is_at_lower or is_at_upper:
                # Optimized Zigzag: We are at an end, scanning to opposite
                target_is_top = is_at_lower # If at lower, go top
                
                self.get_logger().info(f"Z-Scan (Zigzag): At {'BOTTOM' if is_at_lower else 'TOP'}. Sweeping to {'TOP' if target_is_top else 'BOTTOM'}.")
                
                self.target_z_end = target_is_top
                self.trigger_zscan(self.target_z_end)
                self.scanner_at_top = target_is_top
                
                self.state = "WAITING_FOR_SCAN_START"
                self.timer_start_time = time.time()
            else:
                # Intermediate Position: Must align first
                nearest_is_top = (dist_upper < dist_lower)
                self.get_logger().info(f"Z-Scan (Align): Intermediate ({self.current_z_cm:.1f}). Aligning to {'TOP' if nearest_is_top else 'BOTTOM'} first.")
                
                self.trigger_zscan(nearest_is_top) # Goto Nearest
                
                # After alignment, we scan to the OPPOSITE
                self.target_z_end = not nearest_is_top
                
                self.state = "ALIGN_Z_WAIT"
                self.timer_start_time = time.time()

        # --- STATE: ALIGN_Z_WAIT (Moving to Start Position) ---
        elif self.state == "ALIGN_Z_WAIT":
            self.set_motion(False)
            elapsed = time.time() - self.timer_start_time
            
            # Wait for active signal or timeout
            if self.zscan_busy:
                 # It started moving
                 pass 
            else:
                # Case: Arrived or didn't start (assuming success/timeout handled by hardware/latency)
                if elapsed > 3.0: 
                     self.get_logger().info("Aligned. Starting Full SWEEP.")
                     
                     # Now trigger the actual sweep
                     self.trigger_zscan(self.target_z_end)
                     self.scanner_at_top = self.target_z_end
                     
                     self.state = "WAITING_FOR_SCAN_START"
                     self.timer_start_time = time.time()
        
        # --- STATE: WAITING_FOR_SCAN_START ---
        elif self.state == "WAITING_FOR_SCAN_START":
            self.set_motion(False)
            if self.zscan_busy:
                self.get_logger().info("Scanner Active...")
                self.state = "SCANNING"
            elif time.time() - self.timer_start_time > 5.0:
                 # Timeout logic
                 self.get_logger().warn("Scanner Timeout (Didn't start). Switching Direction (Auto-Correction).")
                 
                 self.scanner_at_top = not self.scanner_at_top 
                 self.target_z_end = self.scanner_at_top
                 
                 self.trigger_zscan(self.target_z_end)
                 self.timer_start_time = time.time()

        # --- STATE: SCANNING ---
        elif self.state == "SCANNING":
            self.set_motion(False)
            if not self.zscan_busy:
                self.get_logger().info("Scan Finished.")
                self.target_idx += 1
                
                # Check Rack Limit immediately after increment
                if self.scan_limit_idx != -1 and self.target_idx >= self.scan_limit_idx:
                    self.get_logger().info(f"Rack Finished.")
                    self.process_next_rack_in_queue()
                    return

                if self.target_idx < len(self.points):
                    self.state = "MOVING"
                    self.set_motion(True)
                    self.get_logger().info(f"Moving to Point {self.target_idx}")
                else:
                    self.state = "RETURNING"

        # --- STATE: RETURNING ---
        elif self.state == "RETURNING":
            target = self.points[0]
            self.publish_target(target)
            self.set_motion(True)
            
            dist = self.get_distance(self.robot_pose, target)
            if dist < self.arrival_threshold:
                # CHECK THETA THRESHOLD
                arrived = True
                
                if self.current_path_target_theta is not None:
                     current_theta = self.robot_pose[2]
                     diff = self.current_path_target_theta - current_theta
                     while diff > math.pi: diff -= 2*math.pi
                     while diff < -math.pi: diff += 2*math.pi
                     
                     if abs(diff) > self.theta_threshold:
                         arrived = False

                if arrived:
                    self.get_logger().info("Returned to Start. Settling...")
                    self.state = "RETURNING_SETTLE"
                    self.timer_start_time = time.time()

        # --- STATE: RETURNING_SETTLE ---
        elif self.state == "RETURNING_SETTLE":
            target = self.points[0]
            self.publish_target(target)
            self.set_motion(True)
            elapsed = time.time() - self.timer_start_time
            if elapsed > SETTLE_TIME:
                self.state = "COOLDOWN"
                self.set_motion(False)
                self.trigger_zscan(False) 
                self.target_idx = 1 
                self.scan_limit_idx = -1
                self.timer_start_time = time.time()
                self.get_logger().info(f"Home. Camera Reset. Cooldown {COOLDOWN_TIME}s...")

        # --- STATE: COOLDOWN ---
        elif self.state == "COOLDOWN":
            self.set_motion(False)
            elapsed = time.time() - self.timer_start_time
            if elapsed > COOLDOWN_TIME:
                if self.autoscan_on:
                    self.get_logger().info("Cooldown over. Restarting cycle.")
                    self.start_new_cycle()
                else:
                    self.state = "IDLE"
                    self.get_logger().info("Cooldown over. Autoscan OFF. Idling.")

def main(args=None):
    rclpy.init(args=args)
    node = WarehouseManager()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
