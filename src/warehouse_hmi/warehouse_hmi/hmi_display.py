#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import cv2
import numpy as np
import threading

# Configuration
GIF_PATH = "/home/era/Documents/fresh_start/InterIIT_Code_Repository/eternal.gif"
WINDOW_NAME = "ETERNAL COMMAND CENTER"

# Colors (BGR)
BG_COLOR = (15, 15, 20)           # Deep Dark
OVERLAY_COLOR = (30, 30, 40)      # Slightly lighter for panels
ACCENT_CYAN = (255, 200, 0)       # Cyan-ish
ACCENT_GREEN = (100, 200, 100)
ACCENT_RED = (100, 100, 255)
TEXT_WHITE = (240, 240, 240)

class HmiDisplayNode(Node):
    def __init__(self):
        super().__init__('hmi_display')
        
        # ROS Setup
        self.sub_speak = self.create_subscription(String, '/speak', self.speak_callback, 10)
        self.pub_auto_scan = self.create_publisher(String, '/auto_scan', 10)
        
        self.latest_message = "SYSTEM ONLINE"
        self.auto_scan_active = False

        # GIF Setup
        self.gif_cap = cv2.VideoCapture(GIF_PATH)
        if not self.gif_cap.isOpened():
            self.get_logger().error(f"Failed to open GIF: {GIF_PATH}")
            self.gif_frames = []
        else:
            self.get_logger().info(f"Loaded GIF from {GIF_PATH}")

        # Window Setup
        cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
        cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN) 
        # Note: Some window managers might need toggling. 
        # For robustness, we will try to force it in the loop or set explicit geometry if needed.

        cv2.setMouseCallback(WINDOW_NAME, self.mouse_callback)

        # Interaction State
        self.btn_start_rect = None
        self.btn_stop_rect = None
        self.hover_btn = None # 'start' or 'stop' or None

        # Timer (Target ~30 FPS)
        self.timer = self.create_timer(0.033, self.update_display)
        
        self.get_logger().info("Modern HMI Display Node Started")

    def speak_callback(self, msg):
        self.latest_message = msg.data.upper()

    def mouse_callback(self, event, x, y, flags, param):
        # Hover check
        if self.btn_start_rect and self.is_inside(x, y, self.btn_start_rect):
            self.hover_btn = 'start'
        elif self.btn_stop_rect and self.is_inside(x, y, self.btn_stop_rect):
            self.hover_btn = 'stop'
        else:
            self.hover_btn = None

        # Click check
        if event == cv2.EVENT_LBUTTONDOWN:
            if self.hover_btn == 'start':
                self.publish_command("START")
            elif self.hover_btn == 'stop':
                self.publish_command("STOP")

    def is_inside(self, x, y, rect):
        rx, ry, rw, rh = rect
        return rx <= x <= rx + rw and ry <= y <= ry + rh

    def publish_command(self, cmd):
        msg = String()
        msg.data = cmd
        self.pub_auto_scan.publish(msg)
        self.get_logger().info(f"Published Command: {cmd}")
        # self.latest_message = f"COMMAND INITIATED: {cmd}" # user wants to see spoken messages mostly?
        if cmd == "START":
            self.auto_scan_active = True
        elif cmd == "STOP":
            self.auto_scan_active = False

    def draw_rounded_rect(self, img, rect, color, thickness=1, radius=10, fill=False):
        """Draws a rounded rectangle."""
        x, y, w, h = rect
        # Simply use multiple primitives for "smooth" look if advanced drawing is slow
        # But for 'modern', let's stick to clean standard rects with alpha overlays, rounded is hard in base cv2
        # Alternative: simple rectangle with alpha blend
        p1 = (x, y)
        p2 = (x+w, y+h)
        if fill:
            cv2.rectangle(img, p1, p2, color, -1)
        else:
            cv2.rectangle(img, p1, p2, color, thickness)
        return

    def draw_modern_button(self, frame, rect, text, base_color, is_hovered, is_active):
        x, y, w, h = rect
        
        # Animation / Interaction Color
        color = base_color
        if is_hovered:
            # Brighten
            color = tuple(min(c + 50, 255) for c in base_color)
        
        # 1. Background (Alpha Blending)
        roi = frame[y:y+h, x:x+w]
        overlay = roi.copy()
        cv2.rectangle(overlay, (0, 0), (w, h), color, -1)
        
        alpha = 0.6 if is_hovered or is_active else 0.3
        cv2.addWeighted(overlay, alpha, roi, 1 - alpha, 0, roi)
        frame[y:y+h, x:x+w] = roi

        # 2. Border
        border_color = (255, 255, 255) if is_hovered else color
        cv2.rectangle(frame, (x, y), (x+w, y+h), border_color, 2)

        # 3. decorative corners
        corner_len = 15
        cv2.line(frame, (x, y), (x+corner_len, y), border_color, 4)
        cv2.line(frame, (x, y), (x, y+corner_len), border_color, 4)
        
        cv2.line(frame, (x+w, y+h), (x+w-corner_len, y+h), border_color, 4)
        cv2.line(frame, (x+w, y+h), (x+w, y+h-corner_len), border_color, 4)

        # 4. Text
        font = cv2.FONT_HERSHEY_DUPLEX
        font_scale = 1.0
        thickness = 2
        text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]
        text_x = x + (w - text_size[0]) // 2
        text_y = y + (h + text_size[1]) // 2
        
        cv2.putText(frame, text, (text_x, text_y), font, font_scale, TEXT_WHITE, thickness, cv2.LINE_AA)

    def draw_hud_panel(self, frame, x, y, w, h, title):
        # Semi-transparent background
        roi = frame[y:y+h, x:x+w]
        overlay = roi.copy()
        cv2.rectangle(overlay, (0, 0), (w, h), OVERLAY_COLOR, -1)
        cv2.addWeighted(overlay, 0.4, roi, 0.6, 0, roi)
        frame[y:y+h, x:x+w] = roi

        # Border lines
        cv2.line(frame, (x, y), (x+w, y), ACCENT_CYAN, 1)
        cv2.line(frame, (x, y+h), (x+w, y+h), ACCENT_CYAN, 1)
        
        # Title
        if title:
            cv2.putText(frame, title, (x+10, y+30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, ACCENT_CYAN, 1, cv2.LINE_AA)

    def update_display(self):
        # Read GIF frame
        ret, gif_frame = self.gif_cap.read()
        if not ret:
            # Restart GIF
            self.gif_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, gif_frame = self.gif_cap.read()
            if not ret:
                gif_frame = np.zeros((400, 400, 3), dtype=np.uint8) # Fallback

        # Canvas Setup
        CANVAS_W, CANVAS_H = 1920, 1080
        frame = np.full((CANVAS_H, CANVAS_W, 3), BG_COLOR, dtype=np.uint8)

        # --- BACKGROUND EFFECTS ---
        # Grid lines?
        # for i in range(0, CANVAS_W, 100):
        #     cv2.line(frame, (i, 0), (i, CANVAS_H), (25, 25, 30), 1)
        # for i in range(0, CANVAS_H, 100):
        #     cv2.line(frame, (0, i), (CANVAS_W, i), (25, 25, 30), 1)

        # --- CENTER LOGO ---
        # Resize GIF frame if needed?
        # Let's keep it reasonable, e.g., 500px height max
        h, w = gif_frame.shape[:2]
        display_scale = 500 / h
        gif_display = cv2.resize(gif_frame, (int(w * display_scale), int(h * display_scale)))
        
        gh, gw = gif_display.shape[:2]
        gx = (CANVAS_W - gw) // 2
        gy = (CANVAS_H - gh) // 2 - 100
        
        frame[gy:gy+gh, gx:gx+gw] = gif_display

        # --- HUD LAYOUT ---
        
        # Header
        cv2.rectangle(frame, (0, 0), (CANVAS_W, 60), (0,0,0), -1)
        cv2.putText(frame, "SCANNED AREA NETWORK // SYSTEM INTERFACE", (30, 40), cv2.FONT_HERSHEY_PLAIN, 2.0, ACCENT_CYAN, 2)
        
        # --- SPEAK MESSAGE PANEL ---
        panel_w = 1200
        panel_h = 150
        panel_x = (CANVAS_W - panel_w) // 2
        panel_y = gy + gh + 50
        
        self.draw_hud_panel(frame, panel_x, panel_y, panel_w, panel_h, "COMMUNICATION LOG")
        
        # Message Text
        msg_text = f"\"{self.latest_message}\""
        font_scale = 1.3
        text_size = cv2.getTextSize(msg_text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 2)[0]
        text_x = panel_x + (panel_w - text_size[0]) // 2
        text_y = panel_y + (panel_h + text_size[1]) // 2
        cv2.putText(frame, msg_text, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), 2, cv2.LINE_AA)

        # --- BUTTONS ---
        btn_w, btn_h = 350, 80
        btn_spacing = 60
        total_btn_w = btn_w * 2 + btn_spacing
        start_btn_x = (CANVAS_W - total_btn_w) // 2
        btn_y = panel_y + panel_h + 60

        # Start Button
        self.btn_start_rect = (start_btn_x, btn_y, btn_w, btn_h)
        self.draw_modern_button(frame, self.btn_start_rect, "INITIATE SCAN", ACCENT_GREEN, (self.hover_btn == 'start'), self.auto_scan_active)

        # Stop Button
        stop_btn_x = start_btn_x + btn_w + btn_spacing
        self.btn_stop_rect = (stop_btn_x, btn_y, btn_w, btn_h)
        self.draw_modern_button(frame, self.btn_stop_rect, "ABORT OPERATION", ACCENT_RED, (self.hover_btn == 'stop'), not self.auto_scan_active)


        # Render
        cv2.imshow(WINDOW_NAME, frame)
        key = cv2.waitKey(1)
        if key == 27: # ESC
            rclpy.shutdown()

def main(args=None):
    rclpy.init(args=args)
    node = HmiDisplayNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    except SystemExit:
        pass
    finally:
        if node.gif_cap.isOpened():
            node.gif_cap.release()
        node.destroy_node()
        cv2.destroyAllWindows()
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == '__main__':
    main()
