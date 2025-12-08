import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import sys
import cv2
import numpy as np
from PIL import Image, ImageTk
import math
import os
import threading
import time

# --- ROS 2 Imports ---
try:
    import rclpy
    from rclpy.node import Node
    from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy
    from nav_msgs.msg import OccupancyGrid, MapMetaData
    from std_msgs.msg import Header
    from geometry_msgs.msg import Pose
    ROS_AVAILABLE = True
except ImportError:
    ROS_AVAILABLE = False
    print("Warning: ROS 2 (rclpy) not found. 'Send to ROS' will be disabled.")

# --- Scipy Import ---
try:
    from scipy.ndimage import distance_transform_edt
except ImportError:
    messagebox.showerror("Missing Dependency", "Please install scipy: pip install scipy")
    raise

# --- ROS Node Class (FIXED QoS) ---
class MapPublisherNode(Node):
    def __init__(self):
        super().__init__('lidar_alignment_tool_node')
        # FIX: Set topic to 'map' so it works with default RViz configs
        self.topic_name = 'aligned_map'
        
        # --- FIX: Use Transient Local QoS (Latched) ---
        # This ensures Rviz receives the map even if Rviz is opened AFTER the button is clicked.
        qos = QoSProfile(
            depth=1,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            reliability=ReliabilityPolicy.RELIABLE
        )
        
        self.publisher_ = self.create_publisher(OccupancyGrid, self.topic_name, qos)
        self.get_logger().info(f'Node Started. Publishing latched map to /{self.topic_name}')

    def publish_map(self, binary_img, resolution, origin_x, origin_y, width, height):
        msg = OccupancyGrid()
        msg.header = Header()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "map"

        msg.info = MapMetaData()
        msg.info.resolution = float(resolution)
        msg.info.width = int(width)
        msg.info.height = int(height)
        msg.info.origin = Pose()
        msg.info.origin.position.x = float(origin_x)
        msg.info.origin.position.y = float(origin_y)
        msg.info.origin.position.z = 0.0
        msg.info.origin.orientation.w = 1.0

        # Flip for ROS (Bottom-Left origin standard)
        flipped_img = cv2.flip(binary_img, 0)
        flat_data = flipped_img.flatten()
        
        # ROS Map: 100=Occupied, 0=Free
        # binary_img input: 255=Obstacle, 0=Free
        grid_data = np.where(flat_data > 127, 100, 0).astype(np.int8)
        msg.data = grid_data.tolist()

        # FIX: Actually publish the message
        self.publisher_.publish(msg)
        self.get_logger().info(f'Successfully published map ({width}x{height}) to /{self.topic_name}')

# --- Main Application Class ---
class LidarMapTool:
    def __init__(self, root, initial_map_path=None):
        self.root = root
        self.root.title("LIDAR Map Tool (Fixed ROS QoS)")
        self.root.geometry("1400x950")

        # --- ROS Setup (Lazy Init) ---
        self.ros_node = None
        self.ros_thread = None
        # We delay init until "Send to ROS" is clicked

        # --- State Variables ---
        self.original_image = None
        self.input_resolution = 0.05 
        self.generated_distance_field = None 
        
        # Transform
        self.rotation_angle = 0.0
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.zoom_scale = 1.0
        
        # Interactive
        self.selected_points = [] 
        self.last_click_point = None 
        self.detected_lines = [] 
        self.show_lines_mode = False
        
        self._setup_ui()

        if initial_map_path:
            self.load_image(initial_map_path)

    def _setup_ui(self):
        # --- Left Panel ---
        control_frame = tk.Frame(self.root, width=320, bg="#f0f0f0")
        control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        
        # 1. File
        tk.Label(control_frame, text="1. File", font=("Arial", 10, "bold"), bg="#f0f0f0").pack(pady=5)
        tk.Button(control_frame, text="Load PGM Map", command=self.load_image).pack(fill=tk.X, pady=2)
        self.lbl_res = tk.Label(control_frame, text="Res: N/A", fg="green", bg="#f0f0f0")
        self.lbl_res.pack(pady=2)
        
        # 2. Alignment
        tk.Frame(control_frame, height=2, bg="grey").pack(fill=tk.X, pady=5)
        tk.Label(control_frame, text="2. Alignment", font=("Arial", 10, "bold"), bg="#f0f0f0").pack(pady=5)
        tk.Button(control_frame, text="Detect Lines (Click to Align)", command=self.toggle_line_detection, bg="lightblue").pack(fill=tk.X, pady=2)
        
        # Manual Adjust + 90 Deg
        man_frame = tk.Frame(control_frame, bg="#f0f0f0")
        man_frame.pack(fill=tk.X, pady=(5,0))
        tk.Label(man_frame, text="Manual Adjust:", bg="#f0f0f0").pack(side=tk.LEFT)
        tk.Button(man_frame, text="+90° Rotate", command=self.rotate_90, bg="#ffcc80", width=10, font=("Arial", 8)).pack(side=tk.RIGHT)
        
        self.slider_rotate = tk.Scale(control_frame, from_=-180, to=180, resolution=0.1, orient=tk.HORIZONTAL, command=self.on_transform_change)
        self.slider_rotate.pack(fill=tk.X)
        self.slider_x = tk.Scale(control_frame, from_=-500, to=500, orient=tk.HORIZONTAL, command=self.on_transform_change)
        self.slider_x.pack(fill=tk.X)
        self.slider_y = tk.Scale(control_frame, from_=-500, to=500, orient=tk.HORIZONTAL, command=self.on_transform_change)
        self.slider_y.pack(fill=tk.X)

        # 3. Center Align
        tk.Frame(control_frame, height=2, bg="grey").pack(fill=tk.X, pady=5)
        tk.Label(control_frame, text="3. Center Align", font=("Arial", 10, "bold"), bg="#f0f0f0").pack(pady=5)
        self.lbl_points = tk.Label(control_frame, text="Points: 0/4", fg="blue", bg="#f0f0f0")
        self.lbl_points.pack()
        tk.Button(control_frame, text="Align to Center (4 clicks)", command=self.align_to_center).pack(fill=tk.X, pady=2)
        tk.Button(control_frame, text="Clear Points", command=self.clear_points).pack(fill=tk.X, pady=2)
        
        # 4. Distance Field
        tk.Frame(control_frame, height=2, bg="grey").pack(fill=tk.X, pady=5)
        tk.Label(control_frame, text="4. Distance Field", font=("Arial", 10, "bold"), bg="#f0f0f0").pack(pady=5)
        
        tk.Label(control_frame, text="Decay Param:", bg="#f0f0f0").pack(anchor="w")
        self.decay_val = tk.DoubleVar(value=0.1)
        tk.Scale(control_frame, variable=self.decay_val, from_=0.01, to=1.0, resolution=0.01, orient=tk.HORIZONTAL).pack(fill=tk.X)
        
        tk.Button(control_frame, text="Preview Field (Grayscale)", command=self.preview_distance_field, bg="#e1bee7").pack(fill=tk.X, pady=2)
        tk.Button(control_frame, text="Back to Edit View", command=self.update_display, bg="#f0f0f0").pack(fill=tk.X, pady=2)

        # 5. Export
        tk.Frame(control_frame, height=2, bg="grey").pack(fill=tk.X, pady=5)
        tk.Label(control_frame, text="5. Export", font=("Arial", 10, "bold"), bg="#f0f0f0").pack(pady=5)
        
        ros_txt = "ROS: Standby (Click 'Send' to Init)" if ROS_AVAILABLE else "ROS Unavailable"
        self.lbl_ros_status = tk.Label(control_frame, text=ros_txt, fg="purple", bg="#f0f0f0", font=("Arial", 8))
        self.lbl_ros_status.pack()
        
        btn_ros = tk.Button(control_frame, text="Send to ROS", command=self.send_to_ros, bg="orange", fg="black")
        if not ROS_AVAILABLE: btn_ros.config(state=tk.DISABLED)
        btn_ros.pack(fill=tk.X, pady=2)
        
        tk.Button(control_frame, text="Save Locally (Binary & Grayscale)", command=self.save_map_dialog, bg="lightgreen").pack(fill=tk.X, pady=2)

        # --- Right Panel (Canvas) ---
        self.canvas_container = tk.Frame(self.root, bg="#333333")
        self.canvas_container.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.v_scroll = tk.Scrollbar(self.canvas_container, orient=tk.VERTICAL)
        self.h_scroll = tk.Scrollbar(self.canvas_container, orient=tk.HORIZONTAL)

        self.canvas = tk.Canvas(self.canvas_container, bg="#333333",
                                 xscrollcommand=self.h_scroll.set,
                                 yscrollcommand=self.v_scroll.set)

        self.v_scroll.config(command=self.canvas.yview)
        self.h_scroll.config(command=self.canvas.xview)
        self.v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        self.canvas.bind("<Button-4>", self.on_mouse_wheel)
        self.canvas.bind("<Button-5>", self.on_mouse_wheel)

        # Zoom Controls
        zoom_frame = tk.Frame(self.canvas, bg="white", bd=1, relief=tk.RAISED)
        zoom_frame.place(x=10, y=10)
        
        self.lbl_zoom = tk.Label(zoom_frame, text="100%", bg="white", width=5)
        self.lbl_zoom.pack(side=tk.LEFT, padx=2)
        tk.Button(zoom_frame, text="-", width=2, command=self.zoom_out, bg="#ddd").pack(side=tk.LEFT)
        tk.Button(zoom_frame, text="+", width=2, command=self.zoom_in, bg="#ddd").pack(side=tk.LEFT)

    # --- Zoom Logic ---
    def zoom_in(self): self._apply_zoom(1.2)
    def zoom_out(self): self._apply_zoom(0.8)
    def on_mouse_wheel(self, event):
        if event.num == 5 or event.delta < 0: self._apply_zoom(0.9)
        else: self._apply_zoom(1.1)

    def _apply_zoom(self, factor):
        if self.original_image is None: return
        self.zoom_scale *= factor
        if self.zoom_scale < 0.1: self.zoom_scale = 0.1
        if self.zoom_scale > 10.0: self.zoom_scale = 10.0
        
        if self.generated_distance_field is not None:
            self.render_preview(self.generated_distance_field, is_field=True)
        else:
            self.update_display()

    # --- Core Logic ---
    def load_image(self, file_path=None):
        if not file_path:
            file_path = filedialog.askopenfilename(filetypes=[("PGM/PNG Files", "*.pgm *.png"), ("All Files", "*.*")])
        if file_path:
            self.original_image = cv2.imread(file_path, cv2.IMREAD_GRAYSCALE)
            if self.original_image is None: return

            base_path = os.path.splitext(file_path)[0]
            yaml_path = base_path + ".yaml"
            loaded_res = None
            if os.path.exists(yaml_path):
                try:
                    with open(yaml_path, 'r') as f:
                        for line in f:
                            if "resolution" in line:
                                loaded_res = float(line.split(':')[1].strip())
                                break
                except: pass
            
            self.input_resolution = loaded_res if loaded_res else 0.05
            self.lbl_res.config(text=f"Res: {self.input_resolution} m/px")

            h, w = self.original_image.shape
            limit = max(h, w) // 2
            self.slider_x.config(from_=-limit, to=limit)
            self.slider_y.config(from_=-limit, to=limit)
            
            self.reset_transform()
            self.fit_zoom()

    def fit_zoom(self):
        if self.original_image is None: return
        cw = self.canvas.winfo_width()
        if cw < 100: cw = 800
        h, w = self.original_image.shape
        scale = cw / w
        if scale > 1: scale = 1.0
        self.zoom_scale = scale
        self.update_display()

    def get_transformed_image(self):
        if self.original_image is None: return None
        img = self.original_image.copy()
        h, w = img.shape
        center = (w // 2, h // 2)
        M_rot = cv2.getRotationMatrix2D(center, self.rotation_angle, 1.0)
        M_rot[0, 2] += self.offset_x
        M_rot[1, 2] += self.offset_y
        rotated = cv2.warpAffine(img, M_rot, (w, h), flags=cv2.INTER_LINEAR, borderValue=205)
        return rotated

    # --- Distance Field ---
    def create_distance_field(self, binary_img, decay_param=0.1):
        # binary_img input: 255=Obstacle, 0=Free
        binary_mask = (binary_img > 127).astype(np.uint8)
        distances = distance_transform_edt(1 - binary_mask)
        normalized = np.exp(-decay_param * distances)
        normalized[binary_mask > 0] = 1.0
        grayscale_img = (normalized * 255).astype(np.uint8)
        return grayscale_img

    def preview_distance_field(self):
        if self.original_image is None: return
        current_img = self.get_transformed_image()
        # Invert so 255=Obstacle for calc
        _, binary = cv2.threshold(current_img, 127, 255, cv2.THRESH_BINARY_INV)

        decay = self.decay_val.get()
        dist_field = self.create_distance_field(binary, decay_param=decay)
        
        self.generated_distance_field = dist_field
        self.render_preview(dist_field, is_field=True)

    def render_preview(self, img_data, is_field=False):
        img_rgb = cv2.cvtColor(img_data, cv2.COLOR_GRAY2RGB)
        h, w = img_rgb.shape[:2]
        new_w = int(w * self.zoom_scale)
        new_h = int(h * self.zoom_scale)
        resized = cv2.resize(img_rgb, (new_w, new_h), interpolation=cv2.INTER_NEAREST)
        pil_img = Image.fromarray(resized)
        self.tk_img = ImageTk.PhotoImage(pil_img) 
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, image=self.tk_img, anchor="nw")
        self.canvas.config(scrollregion=(0, 0, new_w, new_h))
        self.lbl_zoom.config(text=f"{int(self.zoom_scale*100)}%")

    # --- Standard Display ---
    def update_display(self):
        self.generated_distance_field = None
        transformed = self.get_transformed_image()
        if transformed is None: return

        img_rgb = cv2.cvtColor(transformed, cv2.COLOR_GRAY2RGB)
        
        if self.show_lines_mode and self.detected_lines:
            for line in self.detected_lines:
                pt1, pt2 = line
                cv2.line(img_rgb, pt1, pt2, (0, 255, 0), 2)

        if self.last_click_point:
            cv2.circle(img_rgb, self.last_click_point, 10, (0, 255, 255), 2) 
            cv2.circle(img_rgb, self.last_click_point, 2, (0, 255, 255), -1)

        for pt in self.selected_points:
            cv2.circle(img_rgb, pt, 5, (0, 0, 255), -1)

        h, w = img_rgb.shape[:2]
        new_w = int(w * self.zoom_scale)
        new_h = int(h * self.zoom_scale)
        resized = cv2.resize(img_rgb, (new_w, new_h), interpolation=cv2.INTER_NEAREST)
        pil_img = Image.fromarray(resized)
        self.tk_img = ImageTk.PhotoImage(pil_img)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, image=self.tk_img, anchor="nw")
        self.canvas.config(scrollregion=(0, 0, new_w, new_h))
        self.lbl_zoom.config(text=f"{int(self.zoom_scale*100)}%")

    # --- Click Handling ---
    def on_canvas_click(self, event):
        if self.original_image is None: return
        if self.generated_distance_field is not None: return 
        
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        real_x = int(canvas_x / self.zoom_scale)
        real_y = int(canvas_y / self.zoom_scale)
        h, w = self.original_image.shape
        if real_x < 0 or real_y < 0 or real_x >= w or real_y >= h: return

        self.last_click_point = (real_x, real_y)
        self.update_display() 

        if self.show_lines_mode:
            target_line = self.find_nearest_line((real_x, real_y))
            if target_line: self.align_specific_line(target_line)
        else:
            if len(self.selected_points) < 4:
                self.selected_points.append((real_x, real_y))
                self.lbl_points.config(text=f"Points: {len(self.selected_points)}/4")
                self.update_display()

    def clear_points(self):
        self.selected_points = []
        self.lbl_points.config(text="Points: 0/4")
        self.update_display()

    def align_to_center(self):
        if len(self.selected_points) != 4:
            messagebox.showwarning("Warning", "Select 4 points first.")
            return
        pts = np.array(self.selected_points)
        center_x = np.mean(pts[:, 0])
        center_y = np.mean(pts[:, 1])
        h, w = self.original_image.shape
        shift_x = (w // 2) - center_x
        shift_y = (h // 2) - center_y
        self.slider_x.set(self.slider_x.get() + shift_x)
        self.slider_y.set(self.slider_y.get() + shift_y)
        self.selected_points = []
        self.lbl_points.config(text="Points: 0/4")
        self.on_transform_change()

    # --- Line Logic ---
    def toggle_line_detection(self):
        if self.original_image is None: return
        self.generated_distance_field = None 
        if self.show_lines_mode:
            self.show_lines_mode = False
            self.detected_lines = []
            self.update_display()
            return
        current_view = self.get_transformed_image()
        blurred = cv2.GaussianBlur(current_view, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150, apertureSize=3)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=80, minLineLength=60, maxLineGap=20)
        self.detected_lines = []
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                self.detected_lines.append(((x1, y1), (x2, y2)))
            self.show_lines_mode = True
            self.update_display()
        else:
            messagebox.showinfo("Result", "No lines found.")

    def find_nearest_line(self, click_pt):
        if not self.detected_lines: return None
        h, w = self.original_image.shape
        tolerance = w * 0.015 
        if tolerance < 20: tolerance = 20
        cx, cy = click_pt
        min_dist = float('inf')
        best_line = None
        for line in self.detected_lines:
            (x1, y1), (x2, y2) = line
            px = x2 - x1
            py = y2 - y1
            norm_sq = px*px + py*py
            if norm_sq == 0: continue
            u = ((cx - x1) * px + (cy - y1) * py) / norm_sq
            if u > 1: u = 1
            elif u < 0: u = 0
            x = x1 + u * px
            y = y1 + u * py
            dx = x - cx
            dy = y - cy
            dist = math.sqrt(dx*dx + dy*dy)
            if dist < min_dist:
                min_dist = dist
                best_line = line
        if min_dist < tolerance: return best_line
        return None

    def align_specific_line(self, line):
        (x1, y1), (x2, y2) = line
        angle_deg = math.degrees(math.atan2(y2 - y1, x2 - x1))
        if angle_deg > 90: angle_deg -= 180
        if angle_deg < -90: angle_deg += 180
        correction = 0
        if -45 <= angle_deg <= 45: correction = angle_deg 
        elif angle_deg > 45: correction = angle_deg - 90
        else: correction = angle_deg + 90
        new_rot = self.slider_rotate.get() + correction
        if new_rot > 180: new_rot -= 360
        if new_rot < -180: new_rot += 360
        self.slider_rotate.set(new_rot)
        self.on_transform_change()
        messagebox.showinfo("Aligned", f"Correction: {correction:.2f}°")

    def rotate_90(self):
        current = self.slider_rotate.get()
        new_angle = current + 90
        if new_angle > 180: new_angle -= 360
        self.slider_rotate.set(new_angle)
        self.on_transform_change()

    def reset_transform(self):
        self.rotation_angle = 0
        self.offset_x = 0
        self.offset_y = 0
        self.detected_lines = []
        self.show_lines_mode = False
        self.last_click_point = None
        self.slider_rotate.set(0)
        self.slider_x.set(0)
        self.slider_y.set(0)
        self.update_display()

    def on_transform_change(self, _=None):
        if self.original_image is None: return
        self.rotation_angle = self.slider_rotate.get()
        self.offset_x = self.slider_x.get()
        self.offset_y = self.slider_y.get()
        self.detected_lines = [] 
        self.show_lines_mode = False 
        self.last_click_point = None
        if self.generated_distance_field is None:
            self.update_display()

    # --- Export Logic ---
    def send_to_ros(self):
        if not ROS_AVAILABLE:
            messagebox.showerror("Error", "ROS 2 is not available.")
            return

        # Lazy Init
        if self.ros_node is None:
            try:
                if not rclpy.ok():
                    rclpy.init(args=None)
                self.ros_node = MapPublisherNode()
                self.ros_thread = threading.Thread(target=rclpy.spin, args=(self.ros_node,), daemon=True)
                self.ros_thread.start()
                self.lbl_ros_status.config(text=f"Topic: /{self.ros_node.topic_name}")
            except Exception as e:
                messagebox.showerror("ROS Error", f"Failed to init ROS: {e}")
                return

        target_w_m = simpledialog.askfloat("ROS Publish", "Target Map Width (m):", initialvalue=8.0)
        if not target_w_m: return
        target_h_m = simpledialog.askfloat("ROS Publish", "Target Map Height (m):", initialvalue=8.0)
        if not target_h_m: return
        
        target_res = self.input_resolution
        
        current_img = self.get_transformed_image()
        _, binary = cv2.threshold(current_img, 127, 255, cv2.THRESH_BINARY_INV) 
        
        target_w_px = int(target_w_m / target_res)
        target_h_px = int(target_h_m / target_res)
        final_canvas = np.zeros((target_h_px, target_w_px), dtype=np.uint8) 
        
        h_c, w_c = binary.shape
        x_off = (target_w_px - w_c) // 2
        y_off = (target_h_px - h_c) // 2
        
        y1, y2 = max(0, y_off), min(target_h_px, y_off + h_c)
        x1, x2 = max(0, x_off), min(target_w_px, x_off + w_c)
        img_y1 = max(0, -y_off)
        img_y2 = img_y1 + (y2 - y1)
        img_x1 = max(0, -x_off)
        img_x2 = img_x1 + (x2 - x1)
        
        if (y2 > y1) and (x2 > x1):
            final_canvas[y1:y2, x1:x2] = binary[img_y1:img_y2, img_x1:img_x2]
            
        origin_x = -target_w_m / 2.0
        origin_y = -target_h_m / 2.0
        
        self.ros_node.publish_map(final_canvas, target_res, origin_x, origin_y, target_w_px, target_h_px)
        messagebox.showinfo("ROS", f"Map sent to topic '/{self.ros_node.topic_name}'")

    def save_map_dialog(self):
        if self.original_image is None: return
        
        target_w_m = simpledialog.askfloat("Input", "Target Map Width (m):", initialvalue=8.0)
        if not target_w_m: return
        target_h_m = simpledialog.askfloat("Input", "Target Map Height (m):", initialvalue=8.0)
        if not target_h_m: return
        
        ppm = simpledialog.askfloat("Input", "Output Pixels per Meter:", initialvalue=100.0)
        if not ppm: return

        # Default save location
        default_dir = "/home/era/Documents/fresh_start/InterIIT_Code_Repository/src/warehouse_navigation/mission_planner/config/maps"
        if not os.path.exists(default_dir):
            try:
                os.makedirs(default_dir)
            except: pass

        # Hardcode filename
        file_path = os.path.join(default_dir, "test_field.png")
        
        self.process_and_save(file_path, target_w_m, target_h_m, ppm)

    def process_and_save(self, path, width_m, height_m, ppm):
        current_img = self.get_transformed_image()
        _, binary_high = cv2.threshold(current_img, 127, 255, cv2.THRESH_BINARY_INV)
        
        decay = self.decay_val.get()
        dist_field = self.create_distance_field(binary_high, decay_param=decay)
        
        input_res = self.input_resolution
        target_res = 1.0 / ppm
        scale = input_res / target_res
        
        if scale != 1.0:
            binary_high = cv2.resize(binary_high, None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)
            dist_field = cv2.resize(dist_field, None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR)
            
        target_w_px = int(width_m * ppm)
        target_h_px = int(height_m * ppm)
        
        canvas_bin = np.full((target_h_px, target_w_px), 0, dtype=np.uint8) # Changed default to 0 (Black)
        canvas_dist = np.full((target_h_px, target_w_px), 0, dtype=np.uint8)

        h_c, w_c = binary_high.shape
        x_off = (target_w_px - w_c) // 2
        y_off = (target_h_px - h_c) // 2
        
        y1, y2 = max(0, y_off), min(target_h_px, y_off + h_c)
        x1, x2 = max(0, x_off), min(target_w_px, x_off + w_c)
        img_y1 = max(0, -y_off)
        img_y2 = img_y1 + (y2 - y1)
        img_x1 = max(0, -x_off)
        img_x2 = img_x1 + (x2 - x1)
        
        if (y2 > y1) and (x2 > x1):
            # REMOVED bitwise_not to fix inversion
            binary_save = binary_high 
            canvas_bin[y1:y2, x1:x2] = binary_save[img_y1:img_y2, img_x1:img_x2]
            canvas_dist[y1:y2, x1:x2] = dist_field[img_y1:img_y2, img_x1:img_x2]

        dir_name = os.path.dirname(path)
        
        # Enforce Fixed Naming Convention
        binary_path = os.path.join(dir_name, "test_field.png")
        cv2.imwrite(binary_path, canvas_bin)
        
        dist_path = os.path.join(dir_name, "distance_test_field.png")
        cv2.imwrite(dist_path, canvas_dist)
        
        yaml_path = os.path.join(dir_name, "test_field.yaml")
        with open(yaml_path, 'w') as f:
            f.write(f"image: {os.path.basename(binary_path)}\n")
            f.write(f"resolution: {target_res:.6f}\n")
            f.write(f"origin: [{-width_m/2:.6f}, {-height_m/2:.6f}, 0.000000]\n")
            f.write("negate: 0\noccupied_thresh: 0.65\nfree_thresh: 0.196\n")

        messagebox.showinfo("Success", f"Saved:\n1. {binary_path}\n2. {dist_path}\n3. {yaml_path}")

if __name__ == "__main__":
    root = tk.Tk()
    initial_map = sys.argv[1] if len(sys.argv) > 1 else None
    app = LidarMapTool(root, initial_map)
    root.mainloop()