#!/usr/bin/env python3
"""
STMBridge — improved to avoid delays when sending commands to STM:
  - outgoing serial writes are performed by a dedicated writer thread (queue)
  - use MultiThreadedExecutor for concurrent callbacks
  - flush serial after write; warn/drop messages if serial unavailable for long
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

# Stepper details
threshold_height = 16.9
distance_in_1_tick = 1/50.0

# ------------------ Configuration (change as needed) ------------------
SERIAL_PORT = "/dev/ttyACM0"
BAUDRATE = 115200
SERIAL_READ_TIMEOUT = 0.05  # reduce read timeout for responsiveness

# Physical parameters (user-provided)
WHEEL_DIAMETER_M = 0.10    # 10 cm

# Optional saturation (rad/s) to avoid insane values; set to None to disable
MAX_WHEEL_RAD_PER_SEC = None  # e.g., 50.0 or None

# zscan integer limits (global variables)
LOWER_LIMIT = 20
UPPER_LIMIT = 170.0

# ------------------ End configuration -------------------------------

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
        self.sub_zscan = self.create_subscription(Bool, "zscan", self.cb_zscan, 10)
        # keep Float32 to match your teleop (change to Int32 if upstream uses int)
        self.sub_zscan_manual = self.create_subscription(Float32, "zscan_manual", self.cb_zscan_manual, 10)

        # Publishers
        self.pub_odom = self.create_publisher(Float32MultiArray, "odom_delta", 10)
        self.pub_zscanactive = self.create_publisher(Bool, "zscan_active", 10)
        self.pub_imu = self.create_publisher(Float32MultiArray, "imu", 10)  # IMU as Float32MultiArray

        # State
        self.latest_cmd_vel = Twist()         # autonomous
        self.latest_cmd_vel_manual = Twist()  # manual
        self.use_autoscan = False             # default: use manual until "on" received
        self.latest_zscan_bool = False
        self.latest_zscan_value = LOWER_LIMIT  # last integer zscan value (manual)

        # Serial and threading
        self.ser = None
        self.serial_lock = threading.Lock()

        # Outgoing queue + writer thread (KEY: decouple ROS callbacks from blocking serial I/O)
        self.out_queue = queue.Queue()
        self.writer_thread = threading.Thread(target=self.serial_write_loop, daemon=True)
        self.writer_thread.start()

        self._open_serial()
        self.serial_thread = threading.Thread(target=self.serial_read_loop, daemon=True)
        self.serial_thread.start()

        # Precompute wheel params
        self.wheel_radius = WHEEL_DIAMETER_M / 2.0
        # For mecanum rotation linear contribution, typical factor is (L + W).
        # Given distance_from_center from centre along both axes is D, L = W = D so L+W = 2*D
        self.rot_linear_factor = 0.185 + 0.148

        self.get_logger().info(
            f"STM bridge started. serial={SERIAL_PORT}@{BAUDRATE}, wheel_r={self.wheel_radius:.3f} m, rot_fac={self.rot_linear_factor:.3f} m"
        )

    # ---------------- ROS callbacks ----------------
    def cb_cmd_vel(self, msg: Twist):
        self.latest_cmd_vel = msg
        if self.use_autoscan:
            self.get_logger().debug("cmd_vel (autonomous) received and autoscan=on -> sending")
            self.process_and_send_twist(msg, source="autonomous")
        else:
            self.get_logger().debug("cmd_vel (autonomous) received but autoscan=off -> ignored")

    def cb_cmd_vel_manual(self, msg: Twist):
        self.latest_cmd_vel_manual = msg
        if not self.use_autoscan:
            self.get_logger().debug("cmd_vel_manual received and autoscan=off -> sending")
            self.process_and_send_twist(msg, source="manual")
        else:
            self.get_logger().debug("cmd_vel_manual received but autoscan=on -> ignored")

    def cb_autoscan(self, msg: String):
        text = (msg.data or "").strip()
        new_state = (text == "START")
        prev = self.use_autoscan
        self.use_autoscan = new_state
        self.get_logger().info(f"autoscan set to {self.use_autoscan} (raw='{msg.data}')")
        if self.use_autoscan:
            self.get_logger().debug("autoscan turned ON -> sending latest autonomous cmd_vel")
            self.process_and_send_twist(self.latest_cmd_vel, source="autonomous")
        else:
            self.get_logger().debug("autoscan turned OFF -> sending latest manual cmd_vel")
            self.process_and_send_twist(self.latest_cmd_vel_manual, source="manual")

    def cb_zscan(self, msg: Bool):
        self.latest_zscan_bool = bool(msg.data)
        if self.use_autoscan:
            if self.latest_zscan_bool:
                self.get_logger().debug("Autonomous zscan True -> sending UPPER_LIMIT")
                self.send_zscan(True)
            else:
                self.get_logger().debug("Autonomous zscan False -> sending LOWER_LIMIT")
                self.send_zscan(False)
        else:
            self.get_logger().debug("Received Bool zscan but autoscan=off -> ignored (manual integer topic expected)")

    def cb_zscan_manual(self, msg: Float32):
        try:
            val = msg.data
        except Exception:
            self.get_logger().warn(f"Received non-number on zscan_manual: {msg}")
            return

        if self.use_autoscan:
            self.get_logger().debug(f"Received manual integer zscan {val} but autoscan=on -> ignoring")
            return

        if val < LOWER_LIMIT or val > UPPER_LIMIT:
            self.get_logger().warn(f"zscan_manual value {val} out of allowed range [{LOWER_LIMIT},{UPPER_LIMIT}] -> ignored")
            return

        self.latest_zscan_value = val
        self.get_logger().debug(f"Manual zscan value accepted: {val} -> sending to STM")
        # convert to ticks as your previous code did
        ticks = int((val - threshold_height) * (1/distance_in_1_tick))
        self.send_zscan(ticks)

    # ---------------- Serial management & parsing -----------------
    def _open_serial(self):
        try:
            self.ser = serial.Serial(port=SERIAL_PORT, baudrate=BAUDRATE,
                                     timeout=SERIAL_READ_TIMEOUT, write_timeout=0.5)
            self.ser.reset_input_buffer()
            self.get_logger().info(f"Opened serial port {SERIAL_PORT} @ {BAUDRATE}")
        except Exception as e:
            self.get_logger().error(f"Failed to open serial {SERIAL_PORT}: {e}")
            self.ser = None

    def serial_read_loop(self):
        while rclpy.ok():
            if not self.ser:
                # try reopen periodically
                try:
                    self._open_serial()
                except Exception:
                    pass
                time.sleep(1.0)
                continue

            try:
                line = self.ser.readline()
                if not line:
                    continue
                try:
                    text = line.decode("utf-8", errors="replace").strip()
                except Exception:
                    text = str(line).strip()
                if text == "":
                    continue
                self.handle_serial_line(text)
            except Exception as e:
                self.get_logger().warn(f"Serial read error: {e}\n{traceback.format_exc()}")
                time.sleep(0.2)

    def handle_serial_line(self, text: str):
        parts = [p.strip() for p in text.split(",")]
        if len(parts) == 0:
            return
        key = parts[0].lower()

        if key == "zscanactive" and len(parts) >= 2:
            val = parts[1].lower()
            b = (val in ("true", "1", "t", "yes", "y"))
            msg = Bool()
            msg.data = b
            self.pub_zscanactive.publish(msg)
            self.get_logger().debug(f"Published zscanactive: {b}")

        elif key == "imu" and len(parts) >= 4:
            try:
                sys = safe_float(parts[1])
                gyro = safe_float(parts[2])
                accel = safe_float(parts[3])
                mag = safe_float(parts[4])
                roll = safe_float(parts[5])
                pitch = safe_float(parts[6])
                yaw = safe_float(parts[7])
                linax = safe_float(parts[8])
                linay = safe_float(parts[9])
                linaz = safe_float(parts[10])
                gyrox = safe_float(parts[11])
                gyroy = safe_float(parts[12])
                gyroz = safe_float(parts[13])

                arr = Float32MultiArray()
                arr.data = [
                    float(sys),     # 0  System Calibration Status
                    float(gyro),    # 1  Gyro Calib
                    float(accel),   # 2  Accel Calib
                    float(mag),     # 3  Mag Calib
                    float(roll),    # 4
                    float(pitch),   # 5
                    float(yaw),     # 6
                    float(linax),   # 7  Linear Acc X
                    float(linay),   # 8  Linear Acc Y
                    float(linaz),   # 9  Linear Acc Z
                    float(gyrox),   # 10 Gyro X
                    float(gyroy),   # 11 Gyro Y
                    float(gyroz)    # 12 Gyro Z
                ]
                self.pub_imu.publish(arr)
                self.get_logger().debug(f"Published IMU array: {arr.data}")
            except Exception:
                self.get_logger().warn(f"Failed to parse IMU: {text}")

        elif key == "odom" and len(parts) >= 5:
            try:
                dx = safe_float(parts[1])
                dy = safe_float(parts[2])
                dtheta = safe_float(parts[3])
                ts = safe_float(parts[4])
                arr = Float32MultiArray()
                # keep the order you intended; adjust if you prefer [dx,dy,dtheta,timestamp]
                arr.data = [float(ts), float(dx), float(dy), float(dtheta)]
                self.pub_odom.publish(arr)
                self.get_logger().debug(f"Published odom array: {arr.data}")
            except Exception:
                self.get_logger().warn(f"Failed to parse odom: {text}")

        else:
            self.get_logger().debug(f"Serial unknown line: '{text}'")

    # ----------------- Command sending ----------------------
    def process_and_send_twist(self, twist_msg: Twist, source: str = "manual"):
        vx = float(twist_msg.linear.x)
        vy = float(twist_msg.linear.y)
        omega = float(twist_msg.angular.z)

        w1, w2, w3, w4 = self.compute_wheel_angular_speeds(vx, vy, omega)

        if MAX_WHEEL_RAD_PER_SEC is not None:
            w1 = max(min(w1, MAX_WHEEL_RAD_PER_SEC), -MAX_WHEEL_RAD_PER_SEC)
            w2 = max(min(w2, MAX_WHEEL_RAD_PER_SEC), -MAX_WHEEL_RAD_PER_SEC)
            w3 = max(min(w3, MAX_WHEEL_RAD_PER_SEC), -MAX_WHEEL_RAD_PER_SEC)
            w4 = max(min(w4, MAX_WHEEL_RAD_PER_SEC), -MAX_WHEEL_RAD_PER_SEC)

        self.send_vel(w1, w2, w3, w4)
        self.get_logger().debug(
            f"[{source}] vx={vx:.3f} vy={vy:.3f} omega={omega:.3f} -> wheel_rad_s: {w1:.3f},{w2:.3f},{w3:.3f},{w4:.3f}"
        )

    def compute_wheel_angular_speeds(self, vx: float, vy: float, omega: float):
        # keep your mapping or adjust if necessary
        w1_lin = -vx - vy - omega * self.rot_linear_factor
        w2_lin =  vx - vy + omega * self.rot_linear_factor
        w3_lin =  vx - vy - omega * self.rot_linear_factor
        w4_lin = -vx - vy + omega * self.rot_linear_factor

        try:
            wr1 = w1_lin / self.wheel_radius
            wr2 = w2_lin / self.wheel_radius
            wr3 = w3_lin / self.wheel_radius
            wr4 = w4_lin / self.wheel_radius
        except Exception:
            self.get_logger().error("Invalid wheel radius (zero?)")
            wr1 = wr2 = wr3 = wr4 = 0.0

        return float(wr1), float(wr2), float(wr3), float(wr4)

    def send_vel(self, w1, w2, w3, w4):
        s = f"vel,{w1:.4f},{w2:.4f},{w3:.4f},{w4:.4f}\n"
        # enqueue instead of writing directly
        self._serial_write(s)
        self.get_logger().debug(f"Enqueued to STM: {s.strip()}")

    def send_zscan(self, value):
        if isinstance(value, bool):
            v = UPPER_LIMIT if value else LOWER_LIMIT # in cm
            v = int((v - threshold_height) * (1 / distance_in_1_tick)) # in ticks
        else:
            try:
                v = value
            except Exception:
                self.get_logger().warn(f"Invalid zscan value (not bool or int): {value}")
                return

        s = f"zscan,{v}\n"
        self._serial_write(s)
        self.get_logger().info(f"Enqueued to STM: {s.strip()}")

    # ---------------- outgoing writer thread ----------------
    def _serial_write(self, s: str):
        """Enqueue outgoing serial string (non-blocking from callbacks)."""
        try:
            self.out_queue.put_nowait(s)
        except queue.Full:
            self.get_logger().warn("Outgoing serial queue full — dropping message")

    def serial_write_loop(self):
        """Consume outgoing queue and write to serial in a dedicated thread."""
        while rclpy.ok():
            try:
                s = self.out_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            # wait for serial to be available for a short period
            wait_start = time.time()
            while self.ser is None and rclpy.ok():
                if time.time() - wait_start > 5.0:
                    # drop message after waiting to avoid infinite backlog if serial never opens
                    self.get_logger().warn(f"Serial not open for 5s; dropping outgoing: {s.strip()}")
                    s = None
                    break
                time.sleep(0.1)

            if s is None:
                continue

            try:
                with self.serial_lock:
                    # write and flush — write_timeout was set in _open_serial
                    self.ser.write(s.encode("utf-8"))
                    try:
                        self.ser.flush()
                    except Exception:
                        pass
            except Exception as e:
                self.get_logger().warn(f"Serial write error: {e} (dropping message): {s.strip()}")

def main(args=None):
    rclpy.init(args=args)
    node = STMBridge()

    # Use a multithreaded executor to avoid single-threaded callback delays
    executor = rclpy.executors.MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        node.get_logger().info("Shutting down STM Bridge (KeyboardInterrupt)")
    finally:
        try:
            if node.ser and node.ser.is_open:
                node.ser.close()
        except Exception:
            pass
        executor.shutdown()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    main()