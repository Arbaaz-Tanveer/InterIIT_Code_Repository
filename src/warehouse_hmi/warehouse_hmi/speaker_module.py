import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, String
from gtts import gTTS
import os


RACKPOINTS = 3
NUMBEROFRACKS = 2
class GoogleSpeakerNode(Node):
    def __init__(self):
        super().__init__('google_speaker_node')
        
        # 1. Initialize variables
        self.count_active = 0
        self.language = 'en' # 'en' = English
        self.tld = 'com'     # 'com' = US Accent 

        # 2. Create Subscribers
        
        # Topic: zscan_active
        self.zscan_sub = self.create_subscription(
            Bool,
            'zscan_active', 
            self.zscan_callback,
            10)
            
        # Topic: auto_scan
        self.autoscan_sub = self.create_subscription(
            String,
            'auto_scan', 
            self.autoscan_callback,
            10)

        # 3. Create Publisher for /speak
        self.speak_pub = self.create_publisher(String, '/speak', 10)

        self.get_logger().info("Google Speaker (High Quality) Initialized...")

    def speak(self, text):
        """Generates MP3 from Google, plays it, and publishes the text."""
        
        # --- NEW: Print to console ---
        print(f"🗣️  SPEAKING: {text}")
        self.get_logger().info(f"Speaking: {text}")

        # --- NEW: Publish to /speak topic ---
        msg = String()
        msg.data = text
        self.speak_pub.publish(msg)

        try:
            # Generate the audio file from Google
            tts = gTTS(text=text, lang=self.language, tld=self.tld, slow=False)
            
            # Save it to a temporary file
            filename = "/tmp/ros_voice.mp3"
            tts.save(filename)
            
            # Play the file using mpg123
            os.system(f"mpg123 -q {filename}")
            
        except Exception as e:
            self.get_logger().error(f"Error generating voice: {str(e)}")

    def zscan_callback(self, msg):
        if msg.data is True:
            self.speak("Started scanning")
            # self.count_active = 0
        else:
            self.count_active += 1
            
            # Case A: Exactly 2 Racks completed (2 * 3 = 6 counts)
            if self.count_active == NUMBEROFRACKS*RACKPOINTS:
                # The Final Message
                self.speak("All racks scanning completed. Going back to home position.")
                
            # Case B: Standard Rack Completion (e.g., Rack 1)
            elif self.count_active % RACKPOINTS == 0:
                rack_number = self.count_active // RACKPOINTS
                self.speak(f"rack {rack_number} scanned")
                self.speak("moving to next rack")
            
            # Case C: Intermediate steps (Between racks)
            else:
                self.speak("Moving")

    def autoscan_callback(self, msg):
        command = msg.data.upper()
        if command == "START":
            self.speak("Starting autonomous scan")
        elif command == "STOP":
            self.speak("Stopping Scanning operations")

def main(args=None):
    rclpy.init(args=args)
    node = GoogleSpeakerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()