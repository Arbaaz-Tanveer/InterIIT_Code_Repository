#!/usr/bin/env python3
"""
STMBridge — Improved for robustness and latency:
  - Multi-port redundancy (tries ACM0, then ACM1).
  - Decoupled writing: 'latest-only' loop at ~40Hz to avoid buffer bloat.
  - Optimized reading: minimized delays.
  - Enhanced logging.
"""
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import String, Bool, Float32MultiArray, Float32
import threading
import serial
import time
import traceback

# Stepper details
threshold_height = 16.2
distance_in_1_tick = 1/50.0

# ------------------ Configuration ------------------
SERIAL_PORTS = ["/dev/ttyACM0", "/dev/ttyACM1"]  # Ports to try in order
BAUDRATE = 115200
SERIAL_READ_TIMEOUT = 0.01   # Fast timeout for non-blocking feel
WRITE_LOOP_RATE = 50.0       # Hz (rate at which we send latest commands to STM)
ODOM_WATCHDOG_TIMEOUT = 2.0  # Seconds to wait for odom before resetting connection

# Physical parameters
WHEEL_DIAMETER_M = 0.10
MAX_WHEEL_RAD_PER_SEC = None

# zscan limits
LOWER_LIMIT = 20
UPPER_LIMIT = 170.0

def safe_float(s, default=0.0):
    try:
        return float(s)
    except Exception:
        return default

class STMBridge(Node):
    def __init__(self):
        super().__init__("stm_bridge_node")

        # Subscribers
        self.sub_cmd_vel = self.create_subscription(Twist, "local_cmd_vel", self.cb_cmd_vel, 10)
        self.sub_cmd_vel_manual = self.create_subscription(Twist, "cmdvel_manual", self.cb_cmd_vel_manual, 10)
        self.sub_autoscan = self.create_subscription(String, "auto_scan", self.cb_autoscan, 10)
        self.sub_restart = self.create_subscription(String, "restart", self.cb_restart, 10)
        self.sub_zscan = self.create_subscription(Bool, "zscan", self.cb_zscan, 10)
        self.sub_zscan_manual = self.create_subscription(Float32, "zscan_manual", self.cb_zscan_manual, 10)

        # Publishers
        self.pub_odom = self.create_publisher(Float32MultiArray, "odom_delta", 10)
        self.pub_zscanactive = self.create_publisher(Bool, "zscan_active", 10)
        self.pub_imu = self.create_publisher(Float32MultiArray, "imu", 10)

        # Logical State
        self.latest_cmd_vel = Twist()
        self.latest_cmd_vel_manual = Twist()
        self.use_autoscan = False
        self.calibrated = False
        self.last_odom_time = time.time()  # Watchdog Init

        # Internal Command State (Shared between ROS callbacks and Write Loop)
        self.cmd_lock = threading.Lock()
        self.latest_vel_string = None  # The most recent velocity command string
        self.priority_cmd_string = None # Critical commands like zscan (sent once)

        # Serial Connection
        self.ser = None
        self.serial_lock = threading.Lock()
        
        # Start Threads
        # 1. Reading thread
        self.read_thread = threading.Thread(target=self.serial_read_loop, daemon=True)
        self.read_thread.start()
        
        # 2. Writing thread
        self.write_thread = threading.Thread(target=self.serial_write_loop, daemon=True)
        self.write_thread.start()

        # Wheel params
        self.wheel_radius = WHEEL_DIAMETER_M / 2.0
        # (L + W) for mecanum. Assuming square base where L=W=0.185 (example) or derived
        self.rot_linear_factor = 0.185 + 0.148 

        self.get_logger().info(f"STMBridge initialized. Wheel Radius={self.wheel_radius:.3f}")

    # ---------------- ROS Callbacks ----------------
    def cb_cmd_vel(self, msg: Twist):
        self.latest_cmd_vel = msg
        if self.use_autoscan:
            self.update_vel_command(msg)

    def cb_cmd_vel_manual(self, msg: Twist):
        self.latest_cmd_vel_manual = msg
        if not self.use_autoscan:
            self.update_vel_command(msg)

    def cb_autoscan(self, msg: String):
        # self.queue_restart() # Send restart on any autoscan message
        text = (msg.data or "").strip()
        new_state = (text == "START" or text == "COORDINATE")
        if new_state != self.use_autoscan:
            self.use_autoscan = new_state
            self.get_logger().info(f"Autoscan mode changed to: {self.use_autoscan}")
            # Immediately refresh command source
            target = self.latest_cmd_vel if self.use_autoscan else self.latest_cmd_vel_manual
            self.update_vel_command(target)

    def cb_restart(self, msg: String):
        self.get_logger().info(f"Restart topic received: {msg.data}")
        # self.queue_restart()

    def cb_zscan(self, msg: Bool):
        if self.use_autoscan:
            target_val = UPPER_LIMIT if msg.data else LOWER_LIMIT
            self.queue_zscan(target_val)
        else:
            self.get_logger().debug("Ignored auto zscan (manual mode)")

    def cb_zscan_manual(self, msg: Float32):
        if not self.use_autoscan:
            val = msg.data
            if LOWER_LIMIT <= val <= UPPER_LIMIT:
                self.queue_zscan(val)
            else:
                self.get_logger().warn(f"Manual zscan {val} out of bounds")

    # ---------------- Command Logic ----------------
    def update_vel_command(self, twist: Twist):
        """Calculates wheel speeds and updates the latest velocity string."""
        vx, vy, omega = twist.linear.x, twist.linear.y, twist.angular.z
        w1, w2, w3, w4 = self.compute_wheel_angular_speeds(vx, vy, omega)
        
        cmd = f"vel,{w1:.4f},{w2:.4f},{w3:.4f},{w4:.4f}\n"
        with self.cmd_lock:
            self.latest_vel_string = cmd

    def queue_restart(self):
        """Queues the restart command to be sent to STM."""
        cmd = "restart\n"
        self.get_logger().info("Queueing STM RESTART command")
        with self.cmd_lock:
            self.priority_cmd_string = cmd

    def queue_zscan(self, val):
        """Updates the priority command to send zscan ASAP."""
        # Convert cm to ticks
        ticks = int((val - threshold_height) * (1/distance_in_1_tick))
        cmd = f"zscan,{ticks}\n"
        
        self.get_logger().info(f"Queueing ZScan command: {val}cm -> {ticks} ticks")
        with self.cmd_lock:
            self.priority_cmd_string = cmd

    def compute_wheel_angular_speeds(self, vx, vy, omega):
        # Mecanum kinematics
        factor = self.rot_linear_factor
        
        w1_lin = -vx - vy - omega * factor
        w2_lin =  vx - vy + omega * factor
        w3_lin =  vx - vy - omega * factor
        w4_lin = -vx - vy + omega * factor

        w1 = w1_lin / self.wheel_radius
        w2 = w2_lin / self.wheel_radius
        w3 = w3_lin / self.wheel_radius
        w4 = w4_lin / self.wheel_radius

        if MAX_WHEEL_RAD_PER_SEC:
            limit = MAX_WHEEL_RAD_PER_SEC
            w1 = max(min(w1, limit), -limit)
            w2 = max(min(w2, limit), -limit)
            w3 = max(min(w3, limit), -limit)
            w4 = max(min(w4, limit), -limit)
            
        return w1, w2, w3, w4

    # ---------------- Serial Connection ----------------
    def _connect_serial(self):
        """Attempts to connect to available ports in a loop."""
        while rclpy.ok() and self.ser is None:
            for port in SERIAL_PORTS:
                try:
                    self.get_logger().info(f"Attempting to connect to {port}...")
                    conn = serial.Serial(port=port, baudrate=BAUDRATE, 
                                         timeout=SERIAL_READ_TIMEOUT, write_timeout=0.1)
                    
                    # --- Arduino-style DTR/RTS Reset ---
                    conn.dtr = False
                    conn.rts = False
                    time.sleep(0.05)
                    conn.dtr = True
                    conn.rts = True
                    time.sleep(0.05)
                    # -----------------------------------
                    
                    conn.reset_input_buffer()
                    conn.reset_output_buffer()
                    self.ser = conn
                    
                    self.get_logger().info(f"\033[92mSuccessfully connected to {port}. Sending RESTART...\033[0m")
                    
                    # Immediately send restart to ensure STM is fresh
                    time.sleep(0.1) # Wait briefly for bootloader/startup
                    # self.queue_restart()
                    self.last_odom_time = time.time() # Reset watchdog
                    
                    return
                except Exception as e:
                    self.get_logger().warn(f"Failed {port}: {e}")
                    time.sleep(0.5) # Short pause between ports
            
            # If all failed, wait a bit before retrying cycle
            time.sleep(2.0)

    # ---------------- Write Loop ----------------
    def serial_write_loop(self):
        """
        Runs at fixed frequency (WRITE_LOOP_RATE).
        Sends priority data first (zscan/restart), then latest velocity.
        """
        period = 1.0 / WRITE_LOOP_RATE
        while rclpy.ok():
            loop_start = time.time()

            if self.ser is None:
                time.sleep(0.5)
                continue

            to_send = None
            
            # Check for commands
            with self.cmd_lock:
                if self.priority_cmd_string:
                    to_send = self.priority_cmd_string
                    self.priority_cmd_string = None  # Consumed
                elif self.latest_vel_string:
                    to_send = self.latest_vel_string
            
            if to_send:
                try:
                    with self.serial_lock:
                        self.ser.write(to_send.encode('utf-8'))
                except Exception as e:
                    self.get_logger().error(f"Write failed: {e}")
                    self.ser = None # Force reconnect logic to trigger

            # Sleep remainder of period
            elapsed = time.time() - loop_start
            sleep_time = period - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    # ---------------- Read Loop ----------------
    def serial_read_loop(self):
        """
        Continuously reads line-by-line.
        Handles reconnection if read fails or Watchdog expires.
        """
        while rclpy.ok():
            if self.ser is None:
                self._connect_serial()
                continue

            # --- Watchdog Check ---
            if time.time() - self.last_odom_time > ODOM_WATCHDOG_TIMEOUT:
                self.get_logger().error(f"WATCHDOG EXPIRED: No odom for {ODOM_WATCHDOG_TIMEOUT}s. Cycle connection.")
                try:
                    self.ser.close()
                except:
                    pass
                self.ser = None
                continue
            # ----------------------
            
            try:
                # readline blocks for at most SERIAL_READ_TIMEOUT (0.01s)
                line = self.ser.readline()
                if not line:
                    continue # Timeout, just loop
                
                try:
                    text = line.decode('utf-8', errors='ignore').strip()
                except Exception:
                    continue
                
                if text:
                    self.parse_serial_line(text)
            
            except serial.SerialException as e:
                self.get_logger().error(f"Serial disconnected: {e}")
                try:
                    self.ser.close()
                except:
                    pass
                self.ser = None
            except Exception as e:
                self.get_logger().error(f"Read error: {e}")
                time.sleep(0.1)

    def parse_serial_line(self, text):
        parts = [p.strip() for p in text.split(",")]
        if not parts:
            return
            
        head = parts[0].lower()
        
        # ODOM: odom,dx,dy,dtheta,ts
        if head == "odom" and len(parts) >= 5:
            # Refresh watchdog
            self.last_odom_time = time.time()
            
            try:
                dx = safe_float(parts[1])
                dy = safe_float(parts[2])
                dth = safe_float(parts[3])
                ts = safe_float(parts[4])
                
                msg = Float32MultiArray()
                msg.data = [ts, dx, dy, dth]
                self.pub_odom.publish(msg)

                # First-time calibration trigger
                if not self.calibrated:
                    self.get_logger().info("First odom received. Calibrating Z to 20cm.")
                    self.queue_zscan(LOWER_LIMIT)
                    self.calibrated = True

            except Exception as e:
                self.get_logger().warn(f"Odom parse error: {e}")

        # IMU: imu,sys,gyro,acc,mag,r,p,y...
        elif head == "imu" and len(parts) >= 14:
            try:
                # Just float-convert the rest
                data_vals = [safe_float(x) for x in parts[1:]]
                msg = Float32MultiArray(data=data_vals)
                self.pub_imu.publish(msg)
            except Exception as e:
                self.get_logger().warn(f"IMU parse error: {e}")

        # ZSCANACTIVE: zscanactive,bool
        elif head == "zscanactive" and len(parts) >= 2:
            val = parts[1].lower() in ("true", "1", "yes", "t")
            self.pub_zscanactive.publish(Bool(data=val))

        else:
            # Maybe useful for debug
            self.get_logger().debug(f"Unknown serial line: {text}")

def main(args=None):
    rclpy.init(args=args)
    node = STMBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Stopping node...")
    finally:
        if node.ser:
            node.ser.close()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    main()

