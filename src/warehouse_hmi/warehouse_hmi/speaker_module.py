import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, String, Float32MultiArray
from gtts import gTTS
import os
import json
import math

# CONFIGURATION
CONFIG_FILE = "/home/era/Documents/fresh_start/InterIIT_Code_Repository/planner_config.json"
POINTS_PER_RACK = 3
ARRIVAL_TOLERANCE = 0.15

class GoogleSpeakerNode(Node):
    def __init__(self):
        super().__init__('google_speaker_node')
        
        # 1. Initialize variables
        self.language = 'en'
        self.tld = 'com' 
        self.scan_points = []
        self.current_rack = -1
        self.current_point = -1
        
        # Load Config
        self.load_config()

        # 2. Subscribers
        self.zscan_sub = self.create_subscription(Bool, 'zscan_active', self.zscan_callback, 10)
        self.autoscan_sub = self.create_subscription(String, 'auto_scan', self.autoscan_callback, 10)
        self.target_sub = self.create_subscription(Float32MultiArray, '/decision_target_data', self.target_callback, 10)

        # 3. Publisher
        self.speak_pub = self.create_publisher(String, '/speak', 10)
        self.get_logger().info("Google Speaker Node Ready.")

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    self.scan_points = data.get("scan_points", [])
                    self.get_logger().info(f"Loaded {len(self.scan_points)} points from config.")
            except Exception as e:
                self.get_logger().error(f"Failed to load config: {e}")
        else:
            self.get_logger().warn(f"Config file not found: {CONFIG_FILE}")

    def speak(self, text):
        """Generates MP3 and plays it."""
        print(f"🗣️  SPEAKING: {text}")
        self.get_logger().info(f"Speaking: {text}")

        msg = String()
        msg.data = text
        self.speak_pub.publish(msg)

        try:
            tts = gTTS(text=text, lang=self.language, tld=self.tld, slow=False)
            filename = "/tmp/ros_voice.mp3"
            tts.save(filename)
            os.system(f"mpg123 -q {filename}")
        except Exception as e:
            self.get_logger().error(f"TTS Error: {e}")

    def get_distance(self, p1, p2):
        return math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)

    def target_callback(self, msg):
        if len(msg.data) < 2: return
        target = [msg.data[0], msg.data[1]]
        
        # Match target to known points
        match_idx = -1
        for i, pt in enumerate(self.scan_points):
            # scan_points in json are lists [x, y]
            if self.get_distance(target, pt) < ARRIVAL_TOLERANCE:
                match_idx = i
                break
        
        if match_idx != -1:
            # Logic: Index 0 = Start/Home. Index 1..N = Rack Points.
            if match_idx == 0 or match_idx == len(self.scan_points) - 1:
                 if self.current_rack != -1:
                     self.speak("Moving to Home Position")
                     self.current_rack = -1
            else:
                # 0 is Home. 1 is Rack 1 Point 1.
                # Adjusted Index = match_idx - 1
                adj_idx = match_idx - 1
                rack_num = (adj_idx // POINTS_PER_RACK) + 1
                point_num = (adj_idx % POINTS_PER_RACK) + 1
                
                # Avoid repeating if same target re-published
                if rack_num != self.current_rack or point_num != self.current_point:
                    self.speak(f"Moving to Rack {rack_num}, Point {point_num}")
                    self.current_rack = rack_num
                    self.current_point = point_num
        else:
            # Unknown target (Manual or Transition)
            pass

    def zscan_callback(self, msg):
        if msg.data is True:
            self.speak("Scanning Started")
        else:
            self.speak("Scanning Completed")

    def autoscan_callback(self, msg):
        command = msg.data.upper()
        if command == "START":
            self.speak("Autonomous Mode Activated")
        elif command == "STOP":
            self.speak("Stopping Operations")
        elif command == "COORDINATE":
            self.speak("Coordinate Mode Activated")

def main(args=None):
    rclpy.init(args=args)
    node = GoogleSpeakerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt: pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()