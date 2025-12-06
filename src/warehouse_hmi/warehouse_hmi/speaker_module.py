import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, String
from gtts import gTTS
import os

class GoogleSpeakerNode(Node):
    def __init__(self):
        super().__init__('google_speaker_node')
        
        # 1. Initialize variables
        self.count_active = 0
        self.language = 'en' # 'en' = English
        self.tld = 'com'     # 'com' = US Accent 

        # 2. Create Subscribers
        
        # CHANGED TOPIC NAME: zscanactive -> zscan_active
        self.zscan_sub = self.create_subscription(
            Bool,
            'zscan_active', 
            self.zscan_callback,
            10)
            
        # CHANGED TOPIC NAME: autoscan -> auto_scan
        self.autoscan_sub = self.create_subscription(
            String,
            'auto_scan', 
            self.autoscan_callback,
            10)

        self.get_logger().info("Google Speaker (High Quality) Initialized...")

    def speak(self, text):
        """Generates MP3 from Google and plays it"""
        self.get_logger().info(f'Downloading audio for: "{text}"')
        
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
            self.count_active = 0
        else:
            self.count_active += 1
            
            # --- MODIFIED LOGIC START ---
            
            # Case A: Exactly 2 Racks completed (2 * 3 = 6 counts)
            if self.count_active == 6:
                # The Final Message
                self.speak("All racks scanning completed. Going back to home position.")
                
            # Case B: Standard Rack Completion (e.g., Rack 1)
            elif self.count_active % 3 == 0:
                rack_number = self.count_active // 3
                self.speak(f"rack {rack_number} scanned")
                self.speak("moving to next rack")
            
            # Case C: Intermediate steps (Between racks)
            else:
                self.speak("Moving")
            
            # --- MODIFIED LOGIC END ---

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