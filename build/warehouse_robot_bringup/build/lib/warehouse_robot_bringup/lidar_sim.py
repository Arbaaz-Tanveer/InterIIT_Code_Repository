import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
import math
import random
import time
import numpy as np

class LidarSimNode(Node):
    def __init__(self):
        super().__init__('lidar_room_simulator')
        
        # Publishers
        self.scan_pub = self.create_publisher(LaserScan, '/scan', 10)
        
        # Simulation Timer (10 Hz)
        self.timer = self.create_timer(0.1, self.timer_callback)
        
        # Room Configuration
        self.room_width = 11.3
        self.room_height = 8.0
        
        # Robot State
        self.yaw = 0.0  # Initial rotation
        self.yaw_velocity = 0.0 # Velocity for smooth drift
        
        self.get_logger().info(f"Simulating {self.room_width}x{self.room_height}m room. Robot fixed at center.")

    def get_distance_to_wall(self, angle_rad):
        """
        Calculates distance from (0,0) to the nearest rectangle wall 
        for a given global ray angle.
        
        Walls are at: x = +/- width/2, y = +/- height/2
        """
        # Avoid division by zero
        epsilon = 1e-9
        
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
        
        # Distance if hitting vertical walls (x limits)
        # x = r * cos(theta) -> r = x / cos(theta)
        if abs(cos_a) > epsilon:
            dist_x = (self.room_width / 2.0) / abs(cos_a)
        else:
            dist_x = float('inf')
            
        # Distance if hitting horizontal walls (y limits)
        # y = r * sin(theta) -> r = y / sin(theta)
        if abs(sin_a) > epsilon:
            dist_y = (self.room_height / 2.0) / abs(sin_a)
        else:
            dist_y = float('inf')
            
        # The ray hits whichever wall is closer
        return min(dist_x, dist_y)

    def timer_callback(self):
        # 1. Update Robot Rotation (Slow Random Drift)
        # We vary the velocity slightly to make movement look organic, not jittery
        self.yaw_velocity += random.uniform(-0.005, 0.005)
        
        # Clamp velocity to keep it slow
        max_vel = 0.05
        self.yaw_velocity = max(min(self.yaw_velocity, max_vel), -max_vel)
        
        # Apply rotation
        self.yaw += self.yaw_velocity
        
        # Normalize yaw to 0-2pi (optional, but good practice)
        self.yaw = self.yaw % (2 * math.pi)

        # 2. Generate Scan
        scan = LaserScan()
        scan.header.stamp = self.get_clock().now().to_msg()
        scan.header.frame_id = "laser_frame"
        
        scan.angle_min = 0.0
        scan.angle_max = 2 * math.pi
        scan.angle_increment = (2 * math.pi) / 360.0 # 1 degree resolution
        scan.time_increment = 0.0
        scan.range_min = 0.1
        scan.range_max = 20.0
        
        ranges = []
        
        # Generate 360 points
        for i in range(360):
            # Angle of the specific laser ray relative to the robot
            local_angle = i * scan.angle_increment
            
            # Global angle of the ray = Robot Yaw + Ray Angle
            global_angle = self.yaw + local_angle
            
            # Get geometric distance
            r = self.get_distance_to_wall(global_angle)
            
            # Add slight sensor noise (Gaussian noise, std_dev = 1cm)
            noise = random.gauss(0, 0.01)
            r_noisy = r + noise
            
            ranges.append(r_noisy)
            
        scan.ranges = ranges
        self.scan_pub.publish(scan)
        
        # Optional: Print status periodically
        # print(f"Published scan. Robot Yaw: {math.degrees(self.yaw):.2f} deg")

def main(args=None):
    rclpy.init(args=args)
    node = LidarSimNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()