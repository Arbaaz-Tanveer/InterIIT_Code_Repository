#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Bool
from std_srvs.srv import Trigger
import cv2
import os
import csv
import torch
import numpy as np
import multiprocessing as mp 
import time 
import re
from datetime import datetime
from pyzbar.pyzbar import decode
from ultralytics import YOLO
import threading
import glob

class QRCameraModule(Node):
    def __init__(self):
        super().__init__('camera_module')
        
        # ROS2 Publishers and Subscribers
        self.scan_result_pub = self.create_publisher(String, 'scan_data', 10)
        self.autoscan_sub = self.create_subscription(
            String,
            'auto_scan',
            self.autoscan_callback,
            10
        )
        
        # NEW: Subscribe to session control for loop restarts
        self.session_sub = self.create_subscription(
             String,
             'session_control',
             self.session_control_callback,
             10
        )
        
        # ROS2 Service to clear saved QR codes
        self.clear_srv = self.create_service(Trigger, 'clear_qr_codes', self.clear_qr_codes_callback)
        
        # Monitor State
        self.current_mode = "MANUAL" # MANUAL, AUTOSCAN, COORDINATE
        self.autoscan_enabled = False
        
        self.get_logger().info('Camera Module Initialized. Mode: MANUAL')
        
        # --- PATH AND SESSION CONFIGURATION ---
        repo_path = os.path.dirname(os.path.abspath(__file__))
        self.base_folder = "qr_session_logs"
        os.makedirs(self.base_folder, exist_ok=True)
        
        # Tracking decoded QR codes (Per Session)
        self.decoded_qr_set = set() # Cleared on new session
        self.invalid_format_count = 0
        
        # Session Counter Logic
        self.session_date = datetime.now().strftime("%Y%m%d")
        self.session_counter = self.get_next_session_counter()
        self.current_csv_path = None
        
        # Start initial session
        self.start_new_session("MANUAL")
        
        # YOLO Setup
        self.get_logger().info("Loading YOLO model...")
        model_path = "src/warehouse_scanning/config/qr_yolov11.pt"
        if not os.path.exists(model_path):
            model_path = "qr_yolov11.pt" 

        self.model = YOLO(model_path) 
        
        if torch.cuda.is_available():
            self.device = "cuda"
            device_name = torch.cuda.get_device_name(0)
            self.model.to(self.device)
            self.get_logger().info(f"GPU: {device_name}")
        else:
            self.device = "cpu"
            self.model.to(self.device)
            self.get_logger().info("Running on CPU")
        
        # Camera setup
        self.setup_camera()
        
        # Shared state for display thread
        self.display_frame = None
        self.frame_lock = threading.Lock()
        self.running = True
        
        self.frame_id = 0
        
        # Multiprocessing setup
        # Note: 'seen_qr_codes' in worker is less useful if we rotate sessions often, 
        # so we will rely on main thread filtering for file writing.
        # Worker just decodes everything it sees.
        
        self.queue = mp.Queue()
        self.result_queue = mp.Queue()
        self.worker = mp.Process(
            target=decode_worker, 
            args=(self.queue, self.result_queue)
        )
        self.worker.start()
        
        # Start result handler thread
        self.result_thread = threading.Thread(target=self.handle_results, daemon=True)
        self.result_thread.start()
        
        # Start display thread
        self.display_thread = threading.Thread(target=self.display_loop, daemon=True)
        self.display_thread.start()
        
        # Timer for processing frames at 30 FPS
        self.timer = self.create_timer(0.033, self.process_frame)
        
        self.get_logger().info('Camera Module Ready!')
    
    def get_next_session_counter(self):
        """Find the next available session number for today"""
        pattern = os.path.join(self.base_folder, f"{self.session_date}_*")
        existing_files = glob.glob(pattern)
        max_count = 0
        for f in existing_files:
            basename = os.path.basename(f)
            parts = basename.split('_')
            # Expecting YYYYMMDD_COUNTER_MODE.csv
            if len(parts) >= 2:
                try:
                    count = int(parts[1])
                    if count > max_count:
                        max_count = count
                except: pass
        return max_count + 1

    def start_new_session(self, mode_name):
        """Rotates the CSV file and clears tracking for a new session/mode"""
        
        # 1. Update State
        self.current_mode = mode_name
        
        # 2. Reset Tracking
        self.decoded_qr_set.clear()
        self.invalid_format_count = 0
        
        # 3. Generate New Filename
        # Format: YYYYMMDD_<number>_<mode>.csv
        filename = f"{self.session_date}_{self.session_counter}_{mode_name}.csv"
        self.current_csv_path = os.path.join(self.base_folder, filename)
        
        # 4. Create File with Headers
        try:
            with open(self.current_csv_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Timestamp", "Frame_ID", "Detection_Phase", "Decoder", 
                               "Status", "Decoded_Text", "Confidence", "Method_Used"])
            self.get_logger().info(f"📁 STARTED SESSION #{self.session_counter}: {filename}")
        except Exception as e:
            self.get_logger().error(f"Failed to create CSV session: {e}")

        # 5. Increment counter for NEXT session
        self.session_counter += 1

    def autoscan_callback(self, msg):
        """Handle Mode Changes via AutoScan topic"""
        cmd = msg.data.upper()
        
        new_mode = self.current_mode
        self.autoscan_enabled = (cmd == "START")
        
        if cmd == "START":
            new_mode = "AUTOSCAN"
        elif cmd == "COORDINATE":
            new_mode = "COORDINATE"
        elif cmd == "STOP":
            new_mode = "MANUAL"
            
        # If mode changed, start new session
        if new_mode != self.current_mode:
            self.start_new_session(new_mode)
            
    def session_control_callback(self, msg):
        """Force specific session actions (e.g. Loop Restart)"""
        if msg.data == "NEW":
            self.get_logger().info("Session Reset Triggered via Topic.")
            # Even if mode is same (Autoscan), we force a new file
            self.start_new_session(self.current_mode)
            
    def clear_qr_codes_callback(self, request, response):
        """Service callback to clear current session data"""
        count = len(self.decoded_qr_set)
        self.decoded_qr_set.clear()
        
        # Re-create current file
        if self.current_csv_path and os.path.exists(self.current_csv_path):
            with open(self.current_csv_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Timestamp", "Frame_ID", "Detection_Phase", "Decoder", 
                               "Status", "Decoded_Text", "Confidence", "Method_Used"])
                               
        response.success = True
        response.message = f"Cleared {count} codes from Current Session"
        return response
    
    def setup_camera(self):
        """Initialize camera"""
        # (Camera setup code remains mostly same, condensed for replacement)
        CAP_BACKEND = cv2.CAP_V4L2
        indices = range(7)
        for idx in indices:
            self.cap = cv2.VideoCapture(idx, CAP_BACKEND)
            if self.cap.isOpened():
                ret, _ = self.cap.read()
                if ret:
                    self.get_logger().info(f"Camera opened at index {idx}")
                    break
                self.cap.release()
        else:
            self.get_logger().warn("No Camera Found!")
            return

        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 960)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 0) 
        self.cap.set(cv2.CAP_PROP_FOCUS, 0)
        
    def handle_results(self):
        """Process results in Main Thread: Check Duplicates & Write CSV"""
        qr_pattern = re.compile(r'^[A-Za-z0-9]+_[A-Za-z0-9]+_[A-Za-z0-9]+$')
        
        while self.running:
            try:
                if not self.result_queue.empty():
                    # Get result from worker
                    # format: (decoded_text, frame_id, box_id, conf, method)
                    result_data = self.result_queue.get(timeout=0.1)
                    decoded_text, f_id, b_id, conf, method = result_data
                    
                    # 1. Determine Status
                    qr_status = "Decoded"
                    if not qr_pattern.match(decoded_text):
                        qr_status = "Non Decoded" # As requested by user
                        
                    # 2. Check Duplicate (Per Session)
                    if decoded_text in self.decoded_qr_set:
                        continue # Skip duplicates within this file
                    
                    # 3. Mark as Seen
                    self.decoded_qr_set.add(decoded_text)
                    
                    # 4. Write to CSV
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    try:
                        if self.current_csv_path:
                            with open(self.current_csv_path, "a", newline="") as f:
                                writer = csv.writer(f)
                                writer.writerow([timestamp, f_id, "BG", method, qr_status,
                                               decoded_text, round(float(conf), 3), method])
                        self.get_logger().info(f"LOGGED: {decoded_text} [{qr_status}] -> {os.path.basename(self.current_csv_path)}")
                    except Exception as e:
                        self.get_logger().error(f"CSV Write Error: {e}")

                    # 5. Publish to ROS (Always publish everything unique)
                    msg = String()
                    msg.data = decoded_text
                    self.scan_result_pub.publish(msg)
                    
                else:
                    time.sleep(0.01)
            except Exception:
                pass
    
    def display_loop(self):
        while self.running:
            with self.frame_lock:
                if self.display_frame is not None:
                    cv2.imshow("YOLO Live QR Detection", self.display_frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                self.running = False
            time.sleep(0.01)
            
    def process_frame(self):
        if not hasattr(self, 'cap') or not self.cap.isOpened(): return
        ret, frame = self.cap.read()
        if not ret: return
        self.frame_id += 1
        
        # Display logic
        # Only detect if required or always? User said "continuously scans".
        # Assuming we always scan but autoscan flag controls robot mode.
        # WAIT, previously autoscan flag disabled processing.
        # "if not self.autoscan_enabled: return" was in old code.
        # BUT user says "manual mode" should also scan and log.
        # So we should process frames ALWAYS, but log to "MANUAL" file.
        
        original = frame.copy()
        
        # YOLO
        results = self.model.predict(source=frame, verbose=False, device=self.device)
        for r in results:
            boxes = r.boxes
            coords = boxes.xyxy.cpu().numpy()
            confs = boxes.conf.cpu().numpy()
            for i, (box, conf) in enumerate(zip(coords, confs)):
                x1, y1, x2, y2 = box.astype(int)
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                
                pad = 40
                h, w = original.shape[:2]
                crop = original[max(y1-pad,0):min(y2+pad,h), max(x1-pad,0):min(x2+pad,w)]
                
                if crop.size > 0:
                    self.queue.put((crop.copy(), self.frame_id, i, conf))
                    
        with self.frame_lock:
            self.display_frame = frame

    def cleanup(self):
        self.running = False
        self.queue.put(None)
        self.worker.join()
        if hasattr(self, 'cap'): self.cap.release()
        cv2.destroyAllWindows()

def decode_worker(input_queue, result_queue):
    """Background worker - Pure Decoding"""
    qr_detector = cv2.QRCodeDetector()
    
    while True:
        data = input_queue.get()
        if data is None: break
        
        crop, f_id, box_id, conf = data
        
        # ... Image Logic (Same as before) ...
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        decoded_text = None
        method = None
        
        # Quick ZBar
        results = decode(gray)
        if results:
            decoded_text = results[0].data.decode()
            method = "ZBar"
        else:
             # Try OpenCV
             d, _, _ = qr_detector.detectAndDecode(crop)
             if d:
                 decoded_text = d
                 method = "OpenCV"
        
        if decoded_text:
            # Send everything to main thread
            result_queue.put((decoded_text, f_id, box_id, conf, method))

def main(args=None):
    rclpy.init(args=args)
    node = QRCameraModule()
    try: rclpy.spin(node)
    except KeyboardInterrupt: pass
    finally:
        node.cleanup()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
