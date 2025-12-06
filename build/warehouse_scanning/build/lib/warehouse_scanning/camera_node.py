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


class QRCameraModule(Node):
    def __init__(self):
        super().__init__('camera_module')
        
        # ROS2 Publishers and Subscribers
        self.scan_result_pub = self.create_publisher(String, 'scan_result', 10)
        self.autoscan_sub = self.create_subscription(
            Bool,
            'auto_scan',
            self.autoscan_callback,
            10
        )
        
        # ROS2 Service to clear saved QR codes
        self.clear_srv = self.create_service(Trigger, 'clear_qr_codes', self.clear_qr_codes_callback)
        
        # Autoscan state
        self.autoscan_enabled = True
        self.get_logger().info('Camera Module Initialized. Autoscan: OFF')
        
        # Setting up the folders and CSV with absolute path for logging the qr codes
        self.base_folder = os.path.expanduser("~/qr_yolo_live_output_minimal")
        self.csv_path = os.path.join(self.base_folder, "onbot_1.csv")
        os.makedirs(self.base_folder, exist_ok=True)
        
        self.get_logger().info(f"CSV will be saved to: {self.csv_path}")
        
        # Initializing CSV
        if not os.path.exists(self.csv_path):
            with open(self.csv_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Timestamp", "Frame_ID", "Detection_Phase", "Decoder", 
                               "Status", "Decoded_Text", "Confidence", "Method_Used"])
        
        # YOLO Setup
        self.get_logger().info("Loading YOLO model...")
        self.model = YOLO(r"qr_yolov11.pt")  #  absolute path to the model
        

        # using gpu
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
        
        # Frame counter
        self.frame_id = 0
        
        # Tracking  decoded QR codes to avoid duplicates (PERSISTENT across ON/OFF)
        self.decoded_qr_set = set()
        self.invalid_format_count = 0
        
        # Multiprocessing setup - CREATE MANAGER FIRST
        self.seen_qr_codes = mp.Manager().dict()
        
        # Load previously saved unique QR codes from CSV (if exists)
        self.load_existing_qr_codes()
        
        # Multiprocessing queues and worker
        self.queue = mp.Queue()
        self.result_queue = mp.Queue()
        self.worker = mp.Process(
            target=decode_worker, 
            args=(self.queue, self.csv_path, self.result_queue, self.seen_qr_codes)
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
    
    
    def load_existing_qr_codes(self):
        """Load previously decoded QR codes from CSV to maintain uniqueness"""
        if os.path.exists(self.csv_path):
            try:
                with open(self.csv_path, "r") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row['Status'] == 'Decoded' and row['Decoded_Text'] != 'N/A':
                            self.decoded_qr_set.add(row['Decoded_Text'])
                            self.seen_qr_codes[row['Decoded_Text']] = True
                
                self.get_logger().info(f"Loaded {len(self.decoded_qr_set)} unique QR codes from previous sessions")
            except Exception as e:
                self.get_logger().warn(f"Could not load existing QR codes: {e}")
        else:
            self.get_logger().info("No previous CSV found - starting fresh")
    
    
    def autoscan_callback(self, msg):
        """Callback for autoscan topic"""
        self.autoscan_enabled = msg.data
        status = "ON" if self.autoscan_enabled else "OFF"
        self.get_logger().info(f'Autoscan: {status}')
        
        if self.autoscan_enabled:
            self.get_logger().info(f"Continuing scan session - {len(self.decoded_qr_set)} unique QR codes already scanned")
    
    
    def clear_qr_codes_callback(self, request, response):
        """Service callback to clear all saved QR codes"""
        try:
            # Getting the  count before clearing
            count = len(self.decoded_qr_set)
            
            # Clearing  in-memory sets
            self.decoded_qr_set.clear()
            self.seen_qr_codes.clear()
            self.invalid_format_count = 0
            
            # Deleting and recreating  CSV file
            if os.path.exists(self.csv_path):
                os.remove(self.csv_path)
            
            with open(self.csv_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Timestamp", "Frame_ID", "Detection_Phase", "Decoder", 
                               "Status", "Decoded_Text", "Confidence", "Method_Used"])
            
            self.get_logger().info(f"Cleared {count} QR codes. Starting fresh!")
            response.success = True
            response.message = f"Cleared {count} unique QR codes"
        except Exception as e:
            self.get_logger().error(f"Failed to clear QR codes: {e}")
            response.success = False
            response.message = f"Error: {str(e)}"
        
        return response
    
    
    def setup_camera(self):
        """Initialize camera with optimized settings"""
        self.get_logger().info("Initializing camera...")
        
        CAP_BACKEND = cv2.CAP_V4L2
        self.cap = cv2.VideoCapture(0, CAP_BACKEND) # Here we are putting the cam (0 for default cam, 2 for external cam)
        
        if not self.cap.isOpened():
            self.get_logger().error("Failed to open camera!")
            return
        
        # Full HD settings(as per PS we need high res for better detection)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        
        # Flush buffer
        for _ in range(10):
            self.cap.read()
            time.sleep(0.01)
        
        self.get_logger().info("Camera ready!")
    
    
    def handle_results(self):
        """Thread to handle results from decode worker and publish to ROS2"""
        # QR Code format validation pattern: RACKID_SHELFID_ITEMCODE
        qr_pattern = re.compile(r'^[A-Za-z0-9]+_[A-Za-z0-9]+_[A-Za-z0-9]+$')
        
        while self.running:
            try:
                if not self.result_queue.empty():
                    decoded_text = self.result_queue.get(timeout=0.1)
                    
                    # Validate format: RACKID_SHELFID_ITEMCODE
                    if not qr_pattern.match(decoded_text):
                        self.invalid_format_count += 1
                        self.get_logger().warn(f"INVALID FORMAT #{self.invalid_format_count} (skipped): {decoded_text}")
                        self.get_logger().warn(f"   Expected format: RACKID_SHELFID_ITEMCODE (e.g., R03_S2_ITM430)")
                        continue
                    
                    # Check if this QR code is already decoded (duplicate check)
                    if decoded_text in self.decoded_qr_set:
                        self.get_logger().info(f"Duplicate detected (skipped): {decoded_text}")
                        continue
                    
                    # Add to set (mark as seen)
                    self.decoded_qr_set.add(decoded_text)
                    
                    # Publish to ROS2 topic (only unique and valid format) we will publish only unique and valid qr codes
                    msg = String()
                    msg.data = decoded_text
                    self.scan_result_pub.publish(msg)
                    self.get_logger().info(f"NEW QR Published: {decoded_text} | Total Unique: {len(self.decoded_qr_set)}")
                else:
                    time.sleep(0.01)
            except:
                pass
    
    
    def display_loop(self):
        """Separate thread for CV2 display - prevents freezing"""
        while self.running:
            with self.frame_lock:
                if self.display_frame is not None:
                    cv2.imshow("YOLO Live QR Detection", self.display_frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                self.get_logger().info("Q pressed - shutting down")
                self.running = False
                break
            
            time.sleep(0.01)
    
    
    def process_frame(self):
        """Main processing loop"""
        # Always read frames to prevent buffer buildup
        ret, frame = self.cap.read()
        if not ret:
            return
        
        self.frame_id += 1
        
        # Only process if autoscan is ON
        if not self.autoscan_enabled:
            with self.frame_lock:
                self.display_frame = frame.copy()
            return
        
        original_frame_copy = frame.copy()
        
        # YOLO Detection
        results = self.model.predict(source=frame, verbose=False, device=self.device)
        
        for r in results:
            boxes = r.boxes
            coords = boxes.xyxy.cpu().numpy()
            confs = boxes.conf.cpu().numpy()
            
            for i, (box, conf) in enumerate(zip(coords, confs)):
                x1, y1, x2, y2 = box.astype(int)
                
                # Draw bounding box
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                
                # Crop QR region
                pad = 40
                qr_crop = original_frame_copy[
                    max(y1 - pad, 0):min(y2 + pad, original_frame_copy.shape[0]),
                    max(x1 - pad, 0):min(x2 + pad, original_frame_copy.shape[1])
                ]
                
                if qr_crop.size > 0:
                    # Send to background worker for decoding
                    self.queue.put((qr_crop.copy(), self.frame_id, i, conf))
                    
                    cv2.putText(frame, f"QR DETECTED (Box {i})", (x1, y2 + 20),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
        
        # Update display frame
        with self.frame_lock:
            self.display_frame = frame
    
    
    def cleanup(self):
        """Cleanup resources"""
        self.get_logger().info("Shutting down...")
        self.running = False
        
        # Stop worker
        self.queue.put(None)
        self.worker.join()
        
        if hasattr(self, 'cap'):
            self.cap.release()
        cv2.destroyAllWindows()
        self.get_logger().info("Shutdown complete")


def decode_worker(input_queue, csv_path, result_queue, seen_qr_codes):
    """Background worker for QR decoding"""
    print("Worker Process started: Ready for decoding (Format: RACKID_SHELFID_ITEMCODE)")
    
    # QR Code format validation pattern
    qr_pattern = re.compile(r'^[A-Za-z0-9]+_[A-Za-z0-9]+_[A-Za-z0-9]+$')
    qr_detector = cv2.QRCodeDetector()
    
    while True:
        frame_data = input_queue.get()
        if frame_data is None:
            break
        
        qr_crop, frame_id, box_id, conf = frame_data
        
        # Robust decoding pipeline
        gray = cv2.cvtColor(qr_crop, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(4, 4))
        enhanced = clahe.apply(gray)
        blur = cv2.bilateralFilter(enhanced, 5, 75, 75)
        sharpened = cv2.addWeighted(enhanced, 1.5, blur, -0.5, 0)
        binary = cv2.adaptiveThreshold(sharpened, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)

        decoded_text = None
        used_method = None
        success = False

        for img_variant, method_name in [(enhanced, "CLAHE"), (sharpened, "Sharpened"), (binary, "Binary")]:
            for scale in [0.5, 1.0, 1.5, 2.0]:
                resized = cv2.resize(img_variant, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

                results_bar = decode(resized)
                if results_bar:
                    decoded_text = results_bar[0].data.decode()
                    used_method = f"pyzbar_{method_name}_x{scale}"
                    success = True
                    break
                
                data, pts, _ = qr_detector.detectAndDecode(resized)
                if data:
                    decoded_text = data
                    used_method = f"opencv_{method_name}_x{scale}"
                    success = True
                    break
            if success:
                break
        
        # Validate Format and Log Results
        if success:
            # Validate format: RACKID_SHELFID_ITEMCODE
            if not qr_pattern.match(decoded_text):
                print(f"[INVALID FORMAT REJECTED] {decoded_text} (Expected: RACKID_SHELFID_ITEMCODE)")
                continue
            
            # Check if already seen (duplicate check)
            if decoded_text in seen_qr_codes:
                print(f"[DUPLICATE SKIPPED] {decoded_text}")
                continue
            
            # Mark as seen
            seen_qr_codes[decoded_text] = True
            
            print(f"[NEW QR DECODED] Frame {frame_id} | Box {box_id}: {decoded_text}")
            
            # Send result back to main process for ROS2 publishing
            result_queue.put(decoded_text)
            
            # Write ONLY unique and valid format to CSV
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            try:
                with open(csv_path, "a", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow([timestamp, frame_id, "Decoding (BG)", used_method, "Decoded",
                                     decoded_text, round(float(conf), 3), used_method])
                print(f"[CSV LOGGED - VALID FORMAT] {decoded_text}")
            except Exception as e:
                print(f"[CSV ERROR] {e}")
        else:
            print(f"[DECODE FAILED] Frame {frame_id} | Box {box_id}")


def main(args=None):
    rclpy.init(args=args)
    
    camera_module = None
    try:
        camera_module = QRCameraModule()
        rclpy.spin(camera_module)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        if camera_module:
            camera_module.get_logger().error(f"Error: {e}")
    finally:
        if camera_module:
            camera_module.cleanup()
            camera_module.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
