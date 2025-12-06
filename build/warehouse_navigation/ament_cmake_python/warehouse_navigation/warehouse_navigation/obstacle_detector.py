#!/usr/bin/env python3
#!/usr/bin/env python3
"""
lidar_circle_detector_cv.py

ROS2 node that detects circular obstacles from a 2D LIDAR.
Includes a 'Max Range' filter to ignore far-away noise.
"""

import math
import time
import threading

import numpy as np
import cv2

import rclpy
from rclpy.node import Node

from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import PointStamped, Point
from visualization_msgs.msg import Marker, MarkerArray
from std_msgs.msg import Header, ColorRGBA

# -------------------------
# Detection Parameters
# -------------------------
CLUSTER_DIST_THRESHOLD = 0.05   # meters: max distance between consecutive points
MIN_CLUSTER_POINTS = 5         
MAX_CLUSTER_POINTS = 30

# "Roundness" check. Lower = Stricter (must be very round). Higher = Looser.
MAX_FIT_RESIDUAL = 0.02       

MIN_RADIUS = 0.05             # meters (Too small? Noise)
MAX_RADIUS = 0.5              # meters (Too big? Wall)

# NEW: Maximum distance the robot "sees" for detection
MAX_LIDAR_RANGE = 4.0         # meters. Ignore everything beyond this.

# -------------------------
# Visualization Parameters
# -------------------------
IMG_WIDTH = 800
IMG_HEIGHT = 800
METERS_PER_PIXEL = 0.01       # 1 pixel = 2cm (Zoom level)
# -------------------------

def polar_to_cartesian(ranges, angle_min, angle_increment, range_max):
    """Convert LaserScan ranges to (x,y) points filtering invalid ranges."""
    pts = []
    n = len(ranges)
    # Ensure we don't exceed the hardware limit OR our software limit
    effective_max_range = min(range_max, MAX_LIDAR_RANGE)
    
    for i in range(n):
        r = ranges[i]
        # Filter: Must be finite, > 1cm, and < MAX_LIDAR_RANGE
        if math.isfinite(r) and r > 0.01 and r <= effective_max_range:
            theta = angle_min + i * angle_increment
            x = r * math.cos(theta)
            y = r * math.sin(theta)
            pts.append((x, y))
    return pts

def euclidean_clusters(points, threshold=CLUSTER_DIST_THRESHOLD):
    """Simple clustering of contiguous points."""
    if not points:
        return []
    clusters = []
    current = [points[0]]
    for prev, curr in zip(points[:-1], points[1:]):
        dx = curr[0] - prev[0]
        dy = curr[1] - prev[1]
        d = math.hypot(dx, dy)
        if d <= threshold:
            current.append(curr)
        else:
            clusters.append(current)
            current = [curr]
    if current:
        clusters.append(current)
    return clusters

def fit_circle_least_squares(xy_points):
    """
    Fit circle x^2 + y^2 + a*x + b*y + c = 0
    Returns (x0, y0, r, mean_residual).
    """
    pts = np.array(xy_points)
    x = pts[:,0]
    y = pts[:,1]
    A = np.column_stack((x, y, np.ones_like(x)))
    b = -(x**2 + y**2)
    try:
        params, *_ = np.linalg.lstsq(A, b, rcond=None)
    except Exception:
        return None
    a, b_param, c = params
    x0 = -a / 2.0
    y0 = -b_param / 2.0
    r_sq = x0**2 + y0**2 - c
    if r_sq <= 0:
        return None
    r = math.sqrt(r_sq)
    dists = np.sqrt((x - x0)**2 + (y - y0)**2)
    residuals = np.abs(dists - r)
    mean_res = float(np.mean(residuals))
    return (float(x0), float(y0), float(r), mean_res)

class LidarCircleDetector(Node):
    def __init__(self):
        super().__init__('lidar_circle_detector')
        self.scan_sub = self.create_subscription(LaserScan, '/scan', self.scan_callback, 10)
        self.center_pub = self.create_publisher(PointStamped, '/detected_circle_center', 10)
        self.markers_pub = self.create_publisher(MarkerArray, '/detected_circles_markers', 10)
        self.get_logger().info(f'LidarCircleDetector started. Max Range: {MAX_LIDAR_RANGE}m')

        # Data storage for the GUI thread
        self.latest_points = []
        self.detected_circles = []  # list of (x0,y0,r, residual)
        
        self._stop_gui = False
        self._gui_thread = threading.Thread(target=self._gui_loop, daemon=True)
        self._gui_thread.start()

        self.frame_id = 'laser'

    def scan_callback(self, scan: LaserScan):
        # PASSING MAX_LIDAR_RANGE Logic happens inside polar_to_cartesian now
        pts = polar_to_cartesian(scan.ranges, scan.angle_min, scan.angle_increment, scan.range_max)
        if not pts:
            self.latest_points = []
            return
        
        self.latest_points = pts 
        
        clusters = euclidean_clusters(pts, threshold=CLUSTER_DIST_THRESHOLD)
        detected = []
        marker_array = MarkerArray()
        marker_id = 0
        now = self.get_clock().now().to_msg()

        for cluster in clusters:
            if len(cluster) < MIN_CLUSTER_POINTS or len(cluster) > MAX_CLUSTER_POINTS:
                continue
            
            fit = fit_circle_least_squares(cluster)
            if not fit:
                continue
            x0, y0, r, mean_res = fit

            # Filters
            if mean_res > MAX_FIT_RESIDUAL:
                continue
            if r < MIN_RADIUS or r > MAX_RADIUS:
                continue

            detected.append((x0, y0, r, mean_res))

            # --- ROS Publishing Logic ---
            ps = PointStamped()
            ps.header.stamp = now
            ps.header.frame_id = self.frame_id
            ps.point = Point(x=x0, y=y0, z=0.0)
            self.center_pub.publish(ps)

            # Markers
            m = Marker()
            m.header.frame_id = self.frame_id
            m.header.stamp = now
            m.ns = 'centers'
            m.id = marker_id
            marker_id += 1
            m.type = Marker.SPHERE
            m.action = Marker.ADD
            m.pose.position.x = x0
            m.pose.position.y = y0
            m.scale.x = 0.1; m.scale.y = 0.1; m.scale.z = 0.1
            m.color = ColorRGBA(r=1.0, g=0.0, b=0.0, a=1.0)
            marker_array.markers.append(m)

            m2 = Marker()
            m2.header.frame_id = self.frame_id
            m2.header.stamp = now
            m2.ns = 'outlines'
            m2.id = marker_id
            marker_id += 1
            m2.type = Marker.LINE_STRIP
            m2.action = Marker.ADD
            m2.scale.x = 0.02
            m2.color = ColorRGBA(r=0.0, g=1.0, b=0.0, a=1.0)
            for i in range(33): 
                theta = 2.0 * math.pi * i / 32.0
                m2.points.append(Point(x=x0 + r*math.cos(theta), y=y0 + r*math.sin(theta), z=0.0))
            marker_array.markers.append(m2)

        if marker_array.markers:
            self.markers_pub.publish(marker_array)

        self.detected_circles = detected

    def _world_to_pixel(self, x, y):
        """
        Converts world coordinates (meters) to image pixel coordinates.
        Robot is at (IMG_WIDTH/2, IMG_HEIGHT/2).
        """
        cx = IMG_WIDTH // 2
        cy = IMG_HEIGHT // 2
        
        # ROS X (Forward) -> Screen Up (-Y)
        # ROS Y (Left)    -> Screen Left (-X)
        
        screen_x = cx - int(y / METERS_PER_PIXEL)
        screen_y = cy - int(x / METERS_PER_PIXEL)
        
        return screen_x, screen_y

    def _gui_loop(self):
        cv2.namedWindow("LIDAR Circle Detector", cv2.WINDOW_AUTOSIZE)
        
        while not self._stop_gui and rclpy.ok():
            img = np.zeros((IMG_HEIGHT, IMG_WIDTH, 3), dtype=np.uint8)
            
            cx, cy = IMG_WIDTH//2, IMG_HEIGHT//2
            
            # Draw Range Circle (Visual guide for MAX_LIDAR_RANGE)
            range_px = int(MAX_LIDAR_RANGE / METERS_PER_PIXEL)
            cv2.circle(img, (cx, cy), range_px, (50, 50, 50), 1)

            # Draw Robot Center
            cv2.drawMarker(img, (cx, cy), (0, 0, 255), cv2.MARKER_CROSS, 20, 2)

            # Draw LIDAR Points
            local_pts = list(self.latest_points) 
            for (x, y) in local_pts:
                px, py = self._world_to_pixel(x, y)
                if 0 <= px < IMG_WIDTH and 0 <= py < IMG_HEIGHT:
                    img[py, px] = (255, 255, 255) 

            # Draw Detected Circles
            local_circles = list(self.detected_circles)
            for (x0, y0, r, res) in local_circles:
                px, py = self._world_to_pixel(x0, y0)
                radius_px = int(r / METERS_PER_PIXEL)
                
                cv2.circle(img, (px, py), radius_px, (0, 255, 0), 2)
                cv2.circle(img, (px, py), 4, (0, 0, 255), -1)
                label = f"R:{r:.2f}m"
                cv2.putText(img, label, (px + 10, py), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

            cv2.imshow("LIDAR Circle Detector", img)
            
            key = cv2.waitKey(100) 
            if key == 27 or key == ord('q'): 
                rclpy.shutdown()
                break

        cv2.destroyAllWindows()

    def destroy_node(self):
        self._stop_gui = True
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    node = LidarCircleDetector()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    except SystemExit:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == "__main__":
    main()