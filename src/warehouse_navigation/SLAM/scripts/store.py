#!/usr/bin/env python3
# record_odom_imu.py
# Records /wheel/odom and /imu/data for 30 seconds automatically
# Writes odom_imu_samples.csv

import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from sensor_msgs.msg import Imu
import csv
import math
import threading
import os
from collections import deque

CSV_FILE = 'odom_imu_samples.csv'
BUFFER_LEN = 2000  # keep latest imu msgs in memory for simple matching
RECORD_DURATION = 30.0  # seconds

def quaternion_to_yaw(q):
    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)

class Recorder(Node):
    def __init__(self):
        super().__init__('odom_imu_recorder')

        # Subscriptions
        self.odom_sub = self.create_subscription(Odometry, '/odom', self.odom_cb, 10)
        self.imu_sub = self.create_subscription(Imu, '/imu', self.imu_cb, 50)

        # Buffer for IMU messages
        self.imu_buf = deque(maxlen=BUFFER_LEN)

        # CSV setup
        write_header = not os.path.exists(CSV_FILE)
        self.csv_lock = threading.Lock()
        if write_header:
            with open(CSV_FILE, 'w', newline='') as f:
                w = csv.writer(f)
                w.writerow(['time', 'odom_stamp', 'imu_stamp',
                            'x', 'y', 'yaw',
                            'vx', 'vy', 'vyaw',
                            'imu_wx', 'imu_wy', 'imu_wz',
                            'imu_ax', 'imu_ay', 'imu_az'])
        self.get_logger().info(f'Writing samples to {CSV_FILE}')

        # Timer to stop recording after 30 seconds
        self.start_time = self.get_clock().now().nanoseconds / 1e9
        self.timer = self.create_timer(0.5, self.check_time)

    def check_time(self):
        now = self.get_clock().now().nanoseconds / 1e9
        if now - self.start_time >= RECORD_DURATION:
            self.get_logger().info(f"Recording finished after {RECORD_DURATION} seconds.")
            rclpy.shutdown()

    def imu_cb(self, msg: Imu):
        imu_entry = {
            'stamp_sec': msg.header.stamp.sec,
            'stamp_nanosec': msg.header.stamp.nanosec,
            'wx': msg.angular_velocity.x,
            'wy': msg.angular_velocity.y,
            'wz': msg.angular_velocity.z,
            'ax': msg.linear_acceleration.x,
            'ay': msg.linear_acceleration.y,
            'az': msg.linear_acceleration.z
        }
        self.imu_buf.append(imu_entry)

    def odom_cb(self, msg: Odometry):
        odom_sec = msg.header.stamp.sec
        odom_nsec = msg.header.stamp.nanosec

        # Get odom data
        yaw = quaternion_to_yaw(msg.pose.pose.orientation)
        x = msg.pose.pose.position.x
        y = msg.pose.pose.position.y
        vx = msg.twist.twist.linear.x
        vy = msg.twist.twist.linear.y
        vyaw = msg.twist.twist.angular.z

        # Find nearest IMU
        nearest = None
        mindt = None
        for imu in reversed(self.imu_buf):
            dt = abs((imu['stamp_sec'] - odom_sec) + (imu['stamp_nanosec'] - odom_nsec) * 1e-9)
            if mindt is None or dt < mindt:
                mindt = dt
                nearest = imu

        imu_stamp = ''
        imu_wx = imu_wy = imu_wz = imu_ax = imu_ay = imu_az = ''
        if nearest is not None:
            imu_stamp = f"{nearest['stamp_sec']}.{nearest['stamp_nanosec']}"
            imu_wx = nearest['wx']
            imu_wy = nearest['wy']
            imu_wz = nearest['wz']
            imu_ax = nearest['ax']
            imu_ay = nearest['ay']
            imu_az = nearest['az']

        # Write row
        now = self.get_clock().now().nanoseconds / 1e9
        row = [now,
               f"{odom_sec}.{odom_nsec}",
               imu_stamp,
               x, y, yaw,
               vx, vy, vyaw,
               imu_wx, imu_wy, imu_wz,
               imu_ax, imu_ay, imu_az]

        with self.csv_lock:
            with open(CSV_FILE, 'a', newline='') as f:
                w = csv.writer(f)
                w.writerow(row)

def main(args=None):
    rclpy.init(args=args)
    node = Recorder()
    try:
        rclpy.spin(node)
    except:
        pass

if __name__ == '__main__':
    main()

