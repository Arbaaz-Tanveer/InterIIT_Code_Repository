#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
import math
from tf2_ros import TransformBroadcaster
# Input Message Type
from std_msgs.msg import Float32MultiArray

# Output Message Types
from nav_msgs.msg import Odometry
from sensor_msgs.msg import Imu
from geometry_msgs.msg import Quaternion, TransformStamped

class DataConverter(Node):
    def __init__(self):
        super().__init__('data_converter_node')

        # --- CONFIGURATION ---
        self.input_odom_topic = 'odom_delta'
        self.input_imu_topic = 'imu1'
        self.output_odom_topic = 'odom'
        self.output_imu_topic = 'imu'

        # Frame IDs
        self.frame_id_odom = 'odom'
        self.frame_id_base = 'base_link'
        self.frame_id_imu = 'bno_link'

        # Global Odometry State (Integrated Position)
        self.x = 0.0
        self.y = 0.0
        self.th = 0.0
        self.tf_broadcaster=TransformBroadcaster(self)

        # --- SUBSCRIBERS ---
        # 1. Listen to raw Odom data [dx, dy, dtheta, dt]
        self.sub_odom = self.create_subscription(
            Float32MultiArray,
            self.input_odom_topic,
            self.odom_callback,
            10
        )

        # 2. Listen to raw IMU data [r, p, y, ax, ay, az, gx, gy, gz]
        self.sub_imu = self.create_subscription(
            Float32MultiArray,
            self.input_imu_topic,
            self.imu_callback,
            10
        )

        # --- PUBLISHERS ---
        self.pub_odom = self.create_publisher(Odometry, self.output_odom_topic, 10)
        self.pub_imu = self.create_publisher(Imu, self.output_imu_topic, 10)

        self.get_logger().info("Data Converter Node Started. Waiting for data...")

    def get_quaternion(self, roll, pitch, yaw):
        """Convert Euler angles to ROS Quaternion"""
        qx = math.sin(roll/2) * math.cos(pitch/2) * math.cos(yaw/2) - math.cos(roll/2) * math.sin(pitch/2) * math.sin(yaw/2)
        qy = math.cos(roll/2) * math.sin(pitch/2) * math.cos(yaw/2) + math.sin(roll/2) * math.cos(pitch/2) * math.sin(yaw/2)
        qz = math.cos(roll/2) * math.cos(pitch/2) * math.sin(yaw/2) - math.sin(roll/2) * math.sin(pitch/2) * math.cos(yaw/2)
        qw = math.cos(roll/2) * math.cos(pitch/2) * math.cos(yaw/2) + math.sin(roll/2) * math.sin(pitch/2) * math.sin(yaw/2)
        return Quaternion(x=qx, y=qy, z=qz, w=qw)

    def odom_callback(self, msg):
        """
        Expects msg.data = [dx, dy, dtheta, dt]
        dx, dy: Meters (Robot Frame)
        dtheta: Radians
        dt: Seconds
        """
        if len(msg.data) < 4:
            self.get_logger().warn("Odom array too short")
            return

        dx = msg.data[1]
        dy = msg.data[2]
        dtheta = msg.data[3]
        dt = msg.data[0]/1000

        if dt <= 0.00001:
            return # Prevent division by zero

        current_time = self.get_clock().now().to_msg()

        # --- 1. INTEGRATE POSE (Global Frame) ---
        # Rotate local displacement (dx, dy) by current global heading (self.th)
        delta_x = (dx * math.cos(self.th) - dy * math.sin(self.th))
        delta_y = (dx * math.sin(self.th) + dy * math.cos(self.th))

        self.x += delta_x
        self.y += delta_y
        self.th += dtheta

        # Normalize theta to -pi to +pi
        self.th = math.atan2(math.sin(self.th), math.cos(self.th))

        # --- 2. CALCULATE TWIST (Robot Frame) ---
        vx = dx / dt
        vy = dy / dt
        vth = dtheta / dt

        # --- 3. CONSTRUCT MESSAGE ---
        odom_msg = Odometry()
        odom_msg.header.stamp = current_time
        odom_msg.header.frame_id = self.frame_id_odom
        odom_msg.child_frame_id = self.frame_id_base

        # POSE
        odom_msg.pose.pose.position.x = self.x
        odom_msg.pose.pose.position.y = self.y
        odom_msg.pose.pose.position.z = 0.0
        odom_msg.pose.pose.orientation = self.get_quaternion(0, 0, self.th)

        # POSE COVARIANCE
        # Trust X, Y, Yaw (0.01). Do not trust Z, Roll, Pitch (100.0)
        odom_msg.pose.covariance = [
            2.172e-10, 0.0, 0.0, 0.0, 0.0, 0.0,  # X
            0.0, 2.639e-14, 0.0, 0.0, 0.0, 0.0,  # Y
            0.0, 0.0, 1000.0, 0.0, 0.0, 0.0, # Z
            0.0, 0.0, 0.0, 1000.0, 0.0, 0.0, # Roll
            0.0, 0.0, 0.0, 0.0, 1000.0, 0.0, # Pitch
            0.0, 0.0, 0.0, 0.0, 0.0, 6.2945e-11   # Yaw
        ]

        # TWIST
        odom_msg.twist.twist.linear.x = vx
        odom_msg.twist.twist.linear.y = vy
        odom_msg.twist.twist.angular.z = vth

        # TWIST COVARIANCE
        # Trust vx, vy, vth
        odom_msg.twist.covariance = [
            1.1489754018395517e-11, 0.0, 0.0, 0.0, 0.0, 0.0,  # vx
            0.0, 1.726447391810001e-13, 0.0, 0.0, 0.0, 0.0,  # vy
            0.0, 0.0, 1000.0, 0.0, 0.0, 0.0, # vz
            0.0, 0.0, 0.0, 1000.0, 0.0, 0.0, # v_roll
            0.0, 0.0, 0.0, 0.0, 1000.0, 0.0, # v_pitch
            0.0, 0.0, 0.0, 0.0, 0.0, 3.8962388853584054e-13   # v_yaw
        ]

        self.pub_odom.publish(odom_msg)
        

    def imu_callback(self, msg):
        """
        Expects msg.data = [roll, pitch, yaw, ax, ay, az, gx, gy, gz]
        Units: Radians, m/s^2, rad/s
        """
        if len(msg.data) < 9:
            self.get_logger().warn("IMU array too short")
            return

        # Unpack
        roll = msg.data[0]
        pitch = msg.data[1]
        yaw = msg.data[2]
        ax = msg.data[3]
        ay = msg.data[4]
        az = msg.data[5]
        gx = msg.data[6]
        gy = msg.data[7]
        gz = msg.data[8]

        current_time = self.get_clock().now().to_msg()

        imu_msg = Imu()
        imu_msg.header.stamp = current_time
        imu_msg.header.frame_id = self.frame_id_imu

        # ORIENTATION
        imu_msg.orientation = self.get_quaternion(roll, pitch, yaw)
        imu_msg.orientation_covariance = [
            99999.0, 0.0, 0.0,
            0.0, 99999.0, 0.0,
            0.0, 0.0, 6.294e-11
        ]

        # ANGULAR VELOCITY
        imu_msg.angular_velocity.x = gx
        imu_msg.angular_velocity.y = gy
        imu_msg.angular_velocity.z = gz
        imu_msg.angular_velocity_covariance = [
            7.670963546714468e-08, 0.0, 0.0,
            0.0, 1.0919775660241004e-07, 0.0,
            0.0, 0.0, 7.959568616040036e-08
        ]

        # LINEAR ACCELERATION
        imu_msg.linear_acceleration.x = ax
        imu_msg.linear_acceleration.y = ay
        imu_msg.linear_acceleration.z = az
        imu_msg.linear_acceleration_covariance = [
            0.0006084797288351252, 0.0, 0.0,
            0.0, 0.0005998053413511586, 0.0,
            0.0, 0.0, 0.5424604470653754
        ]

        self.pub_imu.publish(imu_msg)

def main(args=None):
    rclpy.init(args=args)
    node = DataConverter()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
