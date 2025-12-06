import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Bool, Float32MultiArray, Int32MultiArray
from geometry_msgs.msg import PoseStamped
import math
import time
import json
import os

# Thresholds & Timers
ARRIVAL_THRESHOLD = 0.15   # meters
CONFIG_FILE = "planner_config.json"
SETTLE_TIME = 1.0          # Seconds to wait to stabilize
STOP_POINT_WAIT_TIME = 5.0 # Seconds to wait at the last point (No Scan)
COOLDOWN_TIME = 10.0       # Seconds to wait at Start before restart

# Rack Configuration
POINTS_PER_RACK = 1        # Number of scan points per rack

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
        self.sub_scan_rack = self.create_subscription(
            Int32MultiArray, 'scan_rack', self.scan_rack_callback, 10)

        # --- PUBLISHERS ---
        self.pub_target = self.create_publisher(
            Float32MultiArray, '/decision_target_data', 10)
        
        self.pub_motion = self.create_publisher(
            Bool, 'motion_active', 10)
        
        self.pub_zscan_trigger = self.create_publisher(
            Bool, 'zscan', 10)

        # --- INTERNAL STATE ---
        self.points = []          
        self.robot_pose = None    
        self.autoscan_on = False  
        self.zscan_busy = False   
        
        # State Machine
        self.state = "IDLE"
        self.target_idx = 1       
        self.timer_start_time = 0.0
        
        # Execution Control
        self.scan_limit_idx = -1  # -1 means run to end
        self.rack_queue = []      # Queue for rack sequence [1, 2, 3...]

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
                    self.get_logger().info(f"Loaded {len(self.points)} initial points.")
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
        self.robot_pose = [msg.pose.position.x, msg.pose.position.y]

    def autoscan_callback(self, msg):
        cmd = msg.data
        if cmd == "START":
            if not self.autoscan_on:
                self.get_logger().info("AUTOSCAN ON (Full Loop Mode).")
                self.autoscan_on = True
                self.scan_limit_idx = -1 # Full loop
                self.rack_queue = []     # Clear specific rack requests
                
                if self.state == "IDLE":
                    if self.target_idx >= len(self.points) - 1 or self.target_idx == 0:
                        self.target_idx = 1
                    self.state = "MOVING"
                    self.set_motion(True)

        elif cmd == "STOP":
            self.get_logger().info("AUTOSCAN DISABLED. Stopping.")
            self.autoscan_on = False
            self.state = "IDLE"
            self.rack_queue = []
            self.stop_robot()

    def zscan_status_callback(self, msg):
        self.zscan_busy = msg.data

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
            
            dist = self.get_distance(self.robot_pose, target)
            if dist < ARRIVAL_THRESHOLD:
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
            if dist < ARRIVAL_THRESHOLD:
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
            z_val = (self.target_idx % 2 != 0) 
            self.trigger_zscan(z_val) 
            self.state = "WAITING_FOR_SCAN_START"
            self.timer_start_time = time.time()

        # --- STATE: WAITING_FOR_SCAN_START ---
        elif self.state == "WAITING_FOR_SCAN_START":
            self.set_motion(False)
            if self.zscan_busy:
                self.get_logger().info("Scanner Active...")
                self.state = "SCANNING"
            elif time.time() - self.timer_start_time > 5.0:
                 self.get_logger().warn("Scanner Timeout. Retrying...")
                 z_val = (self.target_idx % 2 != 0)
                 self.trigger_zscan(z_val)
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
            if dist < ARRIVAL_THRESHOLD:
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