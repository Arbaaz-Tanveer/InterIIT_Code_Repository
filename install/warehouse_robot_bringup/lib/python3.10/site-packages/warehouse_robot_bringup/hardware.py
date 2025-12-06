#!/usr/bin/env python3
"""
STMBridge — improved auto port scan + reconnect:
 - scans /dev/ttyACM{i} (i=0..9)
 - reconnects automatically if disconnected
 - thread-safe writer queue for STM commands
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import String, Bool, Float32MultiArray, Float32
import threading
import serial
import time
import traceback
import queue
import os

# ------------------ Hardware/Geometry ------------------
threshold_height = 16.9
distance_in_1_tick = 1/50.0
WHEEL_DIAMETER_M = 0.10
MAX_WHEEL_RAD_PER_SEC = None
LOWER_LIMIT = threshold_height
UPPER_LIMIT = 170.5

# Serial config
BAUDRATE = 115200
SERIAL_READ_TIMEOUT = 0.05
RECONNECT_INTERVAL = 1.0     # seconds between attempts

def safe_float(s, default=0.0):
    try:
        return float(s)
    except:
        return default


def find_serial_port():
    """
    Scan and return first /dev/ttyACM{i}, i=0..9 that exists.
    """
    for i in range(10):
        port = f"/dev/ttyACM{i}"
        if os.path.exists(port):
            return port
    return None


class STMBridge(Node):
    def __init__(self):
        super().__init__("stm_bridge_node")

        # ROS Subscribers
        self.create_subscription(Twist, "local_cmd_vel", self.cb_cmd_vel, 10)
        self.create_subscription(Twist, "cmdvel_manual", self.cb_cmd_vel_manual, 10)
        self.create_subscription(String, "auto_scan", self.cb_autoscan, 10)
        self.create_subscription(Bool, "zscan", self.cb_zscan, 10)
        self.create_subscription(Float32, "zscan_manual", self.cb_zscan_manual, 10)

        # Publishers
        self.pub_odom = self.create_publisher(Float32MultiArray, "odom_delta", 10)
        self.pub_zscanactive = self.create_publisher(Bool, "zscan_active", 10)
        self.pub_imu = self.create_publisher(Float32MultiArray, "imu", 10)

        # State
        self.latest_cmd_vel = Twist()
        self.latest_cmd_vel_manual = Twist()
        self.use_autoscan = False
        self.latest_zscan_bool = False
        self.latest_zscan_value = LOWER_LIMIT

        # Serial
        self.ser = None
        self.serial_lock = threading.Lock()

        # Outgoing command queue
        self.out_queue = queue.Queue()
        self.writer_thread = threading.Thread(target=self.serial_write_loop, daemon=True)
        self.writer_thread.start()

        # Try opening serial
        self.current_port = None
        self._open_serial()

        # Reader thread
        self.serial_thread = threading.Thread(target=self.serial_read_loop, daemon=True)
        self.serial_thread.start()

        # Precompute wheel params
        self.wheel_radius = WHEEL_DIAMETER_M / 2.0
        self.rot_linear_factor = 0.185 + 0.148

        self.get_logger().info("STMBridge initialized")

    # ---------- Try Opening Serial ----------
    def _open_serial(self):
        """
        Detects first available /dev/ttyACM{i} and try opening it.
        Called continuously during read loop when ser is None.
        """
        try:
            port = find_serial_port()
            if port is None:
                self.get_logger().warn("No /dev/ttyACM* devices found...")
                return False

            # Avoid reopening same port repeatedly
            if port == self.current_port and self.ser:
                return True

            # Close previous
            if self.ser:
                try: self.ser.close()
                except: pass

            self.ser = serial.Serial(
                port=port,
                baudrate=BAUDRATE,
                timeout=SERIAL_READ_TIMEOUT,
                write_timeout=0.5
            )
            self.ser.reset_input_buffer()
            self.current_port = port
            self.get_logger().info(f"Serial connected: {port}@{BAUDRATE}")
            return True

        except Exception as e:
            self.get_logger().error(f"Failed to open serial: {e}")
            self.ser = None
            return False

    # ---------- Serial Read Loop ----------
    def serial_read_loop(self):
        """
        Continuously read from serial.
        If disconnected, attempt reconnect.
        """
        while rclpy.ok():
            if not self.ser:
                ok = self._open_serial()
                if not ok:
                    time.sleep(RECONNECT_INTERVAL)
                continue

            try:
                line = self.ser.readline()
                if not line:
                    continue
                text = line.decode("utf-8", errors="replace").strip()
                if text:
                    self.handle_serial_line(text)

            except Exception as e:
                self.get_logger().warn(f"Serial read error: {e}")
                # Force reconnect
                try:
                    if self.ser:
                        self.ser.close()
                except:
                    pass
                self.ser = None
                time.sleep(RECONNECT_INTERVAL)

    # ---------- Parse STM Messages ----------
    def handle_serial_line(self, text):
        parts = [p.strip() for p in text.split(",")]
        if not parts:
            return
        key = parts[0].lower()

        if key == "zscanactive" and len(parts) >= 2:
            val = parts[1].lower()
            msg = Bool()
            msg.data = (val in ("true","1","t","yes","y"))
            self.pub_zscanactive.publish(msg)
            return

        if key == "imu":
            try:
                arr = Float32MultiArray()
                arr.data = [ safe_float(p) for p in parts[1:14] ]
                self.pub_imu.publish(arr)
            except:
                pass
            return

        if key == "odom" and len(parts) >= 5:
            try:
                dx = safe_float(parts[1])
                dy = safe_float(parts[2])
                dtheta = safe_float(parts[3])
                ts = safe_float(parts[4])
                arr = Float32MultiArray()
                arr.data = [ts, dx, dy, dtheta]
                self.pub_odom.publish(arr)
            except:
                pass
            return

    # ---------- ROS Callbacks ----------
    def cb_cmd_vel(self, msg):
        self.latest_cmd_vel = msg
        if self.use_autoscan:
            self.process_and_send_twist(msg, "auto")

    def cb_cmd_vel_manual(self, msg):
        self.latest_cmd_vel_manual = msg
        if not self.use_autoscan:
            self.process_and_send_twist(msg, "manual")

    def cb_autoscan(self, msg):
        self.use_autoscan = (msg.data.strip() == "START")
        if self.use_autoscan:
            self.process_and_send_twist(self.latest_cmd_vel, "auto")
        else:
            self.process_and_send_twist(self.latest_cmd_vel_manual, "manual")

    def cb_zscan(self, msg):
        if self.use_autoscan:
            self.send_zscan(msg.data)

    def cb_zscan_manual(self, msg):
        if self.use_autoscan:
            return
        val = msg.data
        if LOWER_LIMIT <= val <= UPPER_LIMIT:
            ticks = int((val - threshold_height) * (1.0 / distance_in_1_tick))
            self.send_zscan(ticks)

    # ---------- Twist -> Wheel Speeds ----------
    def process_and_send_twist(self, msg, src):
        vx, vy, omega = msg.linear.x, msg.linear.y, msg.angular.z
        w1, w2, w3, w4 = self.compute_wheel(vx, vy, omega)

        if MAX_WHEEL_RAD_PER_SEC:
            w1 = max(min(w1, MAX_WHEEL_RAD_PER_SEC), -MAX_WHEEL_RAD_PER_SEC)
            w2 = max(min(w2, MAX_WHEEL_RAD_PER_SEC), -MAX_WHEEL_RAD_PER_SEC)
            w3 = max(min(w3, MAX_WHEEL_RAD_PER_SEC), -MAX_WHEEL_RAD_PER_SEC)
            w4 = max(min(w4, MAX_WHEEL_RAD_PER_SEC), -MAX_WHEEL_RAD_PER_SEC)

        self.send_vel(w1, w2, w3, w4)

    def compute_wheel(self, vx, vy, omega):
        rx = self.rot_linear_factor
        w1 = (-vx - vy - omega * rx) / self.wheel_radius
        w2 = ( vx - vy + omega * rx) / self.wheel_radius
        w3 = ( vx - vy - omega * rx) / self.wheel_radius
        w4 = (-vx - vy + omega * rx) / self.wheel_radius
        return float(w1), float(w2), float(w3), float(w4)

    # ---------- Outgoing Commands ----------
    def send_vel(self, w1,w2,w3,w4):
        s = f"vel,{w1:.4f},{w2:.4f},{w3:.4f},{w4:.4f}\n"
        self._serial_write(s)

    def send_zscan(self, value):
        if isinstance(value, bool):
            v = UPPER_LIMIT if value else LOWER_LIMIT
            v = int((v - threshold_height) * (1.0 / distance_in_1_tick))
        else:
            v = value
        s = f"zscan,{v}\n"
        self._serial_write(s)

    def _serial_write(self, s):
        try:
            self.out_queue.put_nowait(s)
        except:
            pass

    def serial_write_loop(self):
        while rclpy.ok():
            try:
                s = self.out_queue.get(timeout=0.1)
            except:
                continue

            # ensure serial open
            if not self.ser:
                # requeue? -> drop
                continue

            try:
                with self.serial_lock:
                    self.ser.write(s.encode("utf-8"))
                    self.ser.flush()
            except:
                # force reconnect next read
                try: self.ser.close()
                except: pass
                self.ser = None


def main(args=None):
    rclpy.init(args=args)
    node = STMBridge()
    executor = rclpy.executors.MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        try:
            if node.ser: node.ser.close()
        except: pass
        executor.shutdown()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()

