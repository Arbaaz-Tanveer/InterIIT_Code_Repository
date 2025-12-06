import React, { useState } from 'react';
import copy from 'copy-to-clipboard';
import { Terminal, Copy, CheckCircle, Wifi, Server, Globe, Shield, Code } from 'lucide-react';

// Defined OUTSIDE the component to prevent re-creation on re-renders
// This ensures the DOM element remains stable, preserving text selection
const CodeBlock = ({ code }: { code: string; id?: string }) => {
    return (
        <div className="my-4 bg-slate-900 p-4 rounded-lg border border-slate-700 overflow-x-auto">
            <pre className="font-mono text-sm text-slate-300 whitespace-pre select-text">
                {code}
            </pre>
        </div>
    );
};

// Memoized to prevent re-rendering when parent state (like robot battery) changes
export const RosGuide = React.memo(() => {
    const [copiedCode, setCopiedCode] = useState<string | null>(null);

    const copyToClipboard = (text: string, id: string) => {
        console.log('Attempting to copy text:', text.substring(0, 20) + '...');
        try {
            const result = copy(text);
            console.log('Copy result:', result);
            if (result) {
                setCopiedCode(id);
                setTimeout(() => setCopiedCode(null), 2000);
            } else {
                console.error('Copy failed (library returned false)');
                alert('Copy failed. Please select the text and copy manually.');
            }
        } catch (error) {
            console.error('Copy threw error:', error);
            alert('Copy error: ' + error);
        }
    };

    return (
        <div className="space-y-8 p-6 max-w-6xl mx-auto">
            {/* Header */}
            <div className="space-y-2">
                <h2 className="text-3xl font-bold text-white">Robot Setup Guide</h2>
                <p className="text-slate-400">
                    Complete guide to connect your robot to OmniCore from anywhere in the world via ROS Bridge
                </p>
            </div>

            {/* Architecture Overview */}
            <div className="bg-sci-panel rounded-xl border border-slate-700 p-6">
                <div className="flex items-center space-x-3 mb-4">
                    <Server className="text-sci-accent" size={24} />
                    <h3 className="text-xl font-semibold text-white">Architecture Overview</h3>
                </div>

                <div className="bg-slate-900 p-6 rounded-lg border border-slate-700 font-mono text-xs mb-4">
                    <pre className="text-slate-300 whitespace-pre overflow-x-auto">
                        {`┌─────────────────────────────────────────────────────────┐
│           Web App (Your Laptop/Desktop)                 │
│           http://localhost:3002                         │
└──────────────────────┬──────────────────────────────────┘
                       │ WebSocket (ws:// or wss://)
                       ↓
┌─────────────────────────────────────────────────────────┐
│              Internet / Cloud Tunnel                    │
│         (ngrok, CloudFlare, or Public IP)               │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ↓
┌─────────────────────────────────────────────────────────┐
│                Robot (Anywhere in World)                │
│  ┌───────────────────────────────────────────────────┐ │
│  │         rosbridge_server (Port 9090)              │ │
│  │         Converts WebSocket ↔ ROS Messages         │ │
│  └─────────────────────┬─────────────────────────────┘ │
│                        │                                │
│  ┌─────────────────────┴─────────────────────────────┐ │
│  │              ROS 1 or ROS 2 System                │ │
│  │  Topics: /robot_pose, /battery_state, /cmd_vel   │ │
│  └───────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘`}
                    </pre>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="bg-slate-800/50 p-4 rounded-lg">
                        <h4 className="font-semibold text-white mb-2">Prerequisites</h4>
                        <ul className="text-sm space-y-1 text-slate-400">
                            <li>• Ubuntu 20.04/22.04</li>
                            <li>• ROS 1 Noetic or ROS 2</li>
                            <li>• Internet connection</li>
                            <li>• Python 3.8+</li>
                        </ul>
                    </div>
                    <div className="bg-slate-800/50 p-4 rounded-lg">
                        <h4 className="font-semibold text-white mb-2">Communication</h4>
                        <ul className="text-sm space-y-1 text-slate-400">
                            <li>• WebSocket protocol</li>
                            <li>• JSON message format</li>
                            <li>• Real-time bidirectional</li>
                            <li>• Works globally</li>
                        </ul>
                    </div>
                    <div className="bg-slate-800/50 p-4 rounded-lg">
                        <h4 className="font-semibold text-white mb-2">Features</h4>
                        <ul className="text-sm space-y-1 text-slate-400">
                            <li>• Live position tracking</li>
                            <li>• Remote commands</li>
                            <li>• Battery monitoring</li>
                            <li>• Scan data sync</li>
                        </ul>
                    </div>
                </div>
            </div>

            {/* Step 1: Install ROS Bridge */}
            <div className="bg-sci-panel rounded-xl border border-slate-700 p-6">
                <div className="flex items-center space-x-3 mb-4">
                    <Terminal className="text-sci-accent" size={24} />
                    <h3 className="text-xl font-semibold text-white">Step 1: Install ROS Bridge</h3>
                </div>

                <p className="text-sm text-slate-300 mb-4">Install the rosbridge suite on your robot to enable WebSocket communication.</p>

                <div className="space-y-4">
                    <div>
                        <h4 className="font-semibold text-white mb-2">For ROS 1 (Noetic)</h4>
                        <CodeBlock
                            id="install-ros1"
                            code={`# Update package list
sudo apt-get update

# Install rosbridge suite
sudo apt-get install ros-noetic-rosbridge-suite

# Verify installation
rospack find rosbridge_server`}
                        />
                    </div>

                    <div>
                        <h4 className="font-semibold text-white mb-2">For ROS 2 (Humble)</h4>
                        <CodeBlock
                            id="install-ros2"
                            code={`# Update package list
sudo apt-get update

# Install rosbridge suite
sudo apt-get install ros-humble-rosbridge-suite

# Verify installation
ros2 pkg prefix rosbridge_server`}
                        />
                    </div>
                </div>
            </div>

            {/* Step 2: Launch ROS Bridge */}
            <div className="bg-sci-panel rounded-xl border border-slate-700 p-6">
                <div className="flex items-center space-x-3 mb-4">
                    <Server className="text-sci-accent" size={24} />
                    <h3 className="text-xl font-semibold text-white">Step 2: Launch ROS Bridge Server</h3>
                </div>

                <p className="text-sm text-slate-300 mb-4">Start the rosbridge WebSocket server on your robot.</p>

                <div className="space-y-4">
                    <div>
                        <h4 className="font-semibold text-white mb-2">For ROS 1</h4>
                        <CodeBlock
                            id="launch-ros1"
                            code={`# Source ROS environment
source /opt/ros/noetic/setup.bash

# Launch rosbridge server (listening on all interfaces)
roslaunch rosbridge_server rosbridge_websocket.launch address:=0.0.0.0`}
                        />
                        <p className="text-xs text-slate-500 mt-2">Expected output: "Rosbridge WebSocket server started on port 9090"</p>
                    </div>

                    <div>
                        <h4 className="font-semibold text-white mb-2">For ROS 2</h4>
                        <CodeBlock
                            id="launch-ros2"
                            code={`# Source ROS environment
source /opt/ros/humble/setup.bash

# Launch rosbridge server
ros2 launch rosbridge_server rosbridge_websocket_launch.xml address:=0.0.0.0`}
                        />
                    </div>

                    <div className="bg-sci-warning/10 border border-sci-warning/20 p-4 rounded-lg">
                        <h4 className="font-semibold text-sci-warning mb-2">Auto-Start on Boot (Optional)</h4>
                        <CodeBlock
                            id="systemd"
                            code={`# Create systemd service
sudo nano /etc/systemd/system/rosbridge.service

# Add this content (adjust paths):
[Unit]
Description=ROS Bridge WebSocket Server
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/home/your-username
Environment="ROS_MASTER_URI=http://localhost:11311"
ExecStart=/bin/bash -c "source /opt/ros/noetic/setup.bash && roslaunch rosbridge_server rosbridge_websocket.launch address:=0.0.0.0"
Restart=on-failure

[Install]
WantedBy=multi-user.target

# Enable and start
sudo systemctl enable rosbridge.service
sudo systemctl start rosbridge.service`}
                        />
                    </div>
                </div>
            </div>

            {/* Step 3: Expose to Internet */}
            <div className="bg-sci-panel rounded-xl border border-slate-700 p-6">
                <div className="flex items-center space-x-3 mb-4">
                    <Globe className="text-sci-accent" size={24} />
                    <h3 className="text-xl font-semibold text-white">Step 3: Expose Robot to Internet</h3>
                </div>

                <p className="text-sm text-slate-300 mb-4">Choose one of these methods to make your robot accessible from anywhere:</p>

                <div className="space-y-6">
                    {/* Option 1: ngrok */}
                    <div className="bg-slate-800/50 p-4 rounded-lg">
                        <div className="flex items-center justify-between mb-3">
                            <h4 className="font-semibold text-white">Option 1: ngrok (Easiest)</h4>
                            <span className="text-xs bg-green-500/20 text-green-400 px-2 py-1 rounded">Recommended for Testing</span>
                        </div>
                        <p className="text-sm text-slate-400 mb-3">Quick setup, no configuration needed. URL changes on restart (free tier).</p>
                        <CodeBlock
                            id="ngrok"
                            code={`# Download ngrok
wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz
tar xvzf ngrok-v3-stable-linux-amd64.tgz
sudo mv ngrok /usr/local/bin/

# Sign up at https://ngrok.com and get your auth token
ngrok config add-authtoken YOUR_AUTH_TOKEN

# Expose port 9090
ngrok tcp 9090`}
                        />
                        <p className="text-xs text-slate-500 mt-2">
                            Output will show: <code className="text-sci-accent">tcp://0.tcp.ngrok.io:12345</code><br />
                            Use in web app: <code className="text-sci-accent">ws://0.tcp.ngrok.io:12345</code>
                        </p>
                    </div>

                    {/* Option 2: Tailscale */}
                    <div className="bg-slate-800/50 p-4 rounded-lg">
                        <div className="flex items-center justify-between mb-3">
                            <h4 className="font-semibold text-white">Option 2: Tailscale VPN</h4>
                            <span className="text-xs bg-blue-500/20 text-blue-400 px-2 py-1 rounded">Secure & Private</span>
                        </div>
                        <p className="text-sm text-slate-400 mb-3">Secure private network. Best for permanent setups.</p>
                        <div className="bg-sci-accent/10 border border-sci-accent/20 p-3 rounded mb-3">
                            <p className="text-xs text-white font-medium">Important: Both devices (Robot & Laptop) must be registered on Tailscale using the same email ID.</p>
                        </div>
                        <CodeBlock
                            id="tailscale"
                            code={`# Install Tailscale
curl -fsSL https://tailscale.com/install.sh | sh

# Start Tailscale and authenticate
sudo tailscale up

# Get your robot's Tailscale IP
tailscale ip -4

# Check status (verifies both devices are active)
tailscale status

# To disable temporarily
sudo tailscale down

# To logout completely
sudo tailscale logout`}
                        />
                        <p className="text-xs text-slate-500 mt-2">
                            Use in web app: <code className="text-sci-accent">ws://YOUR_TAILSCALE_IP:9090</code>
                        </p>
                    </div>

                    {/* Option 3: Public IP */}
                    <div className="bg-slate-800/50 p-4 rounded-lg">
                        <div className="flex items-center justify-between mb-3">
                            <h4 className="font-semibold text-white">Option 3: Direct Public IP</h4>
                            <span className="text-xs bg-orange-500/20 text-orange-400 px-2 py-1 rounded">Advanced</span>
                        </div>
                        <p className="text-sm text-slate-400 mb-3">Full control, best performance. Requires public IP.</p>
                        <CodeBlock
                            id="publicip"
                            code={`# Configure firewall to allow port 9090
sudo ufw allow 9090/tcp

# Find your public IP
curl ifconfig.me`}
                        />
                        <p className="text-xs text-slate-500 mt-2">
                            Use in web app: <code className="text-sci-accent">ws://YOUR_PUBLIC_IP:9090</code>
                        </p>
                    </div>
                </div>
            </div>

            {/* Step 4: ROS Topics */}
            <div className="bg-sci-panel rounded-xl border border-slate-700 p-6">
                <div className="flex items-center space-x-3 mb-4">
                    <Wifi className="text-sci-accent" size={24} />
                    <h3 className="text-xl font-semibold text-white">Step 4: Set Up ROS Topics</h3>
                </div>

                <p className="text-sm text-slate-300 mb-4">Your robot needs to publish these topics for the web app to receive data:</p>

                <div className="space-y-4">
                    <div className="bg-slate-800/50 p-4 rounded-lg">
                        <h4 className="font-semibold text-white mb-2">Position Topic</h4>
                        <p className="text-sm text-slate-400 mb-2">Topic: <code className="text-sci-accent">/robot_pose</code> | Type: <code>geometry_msgs/PoseStamped</code></p>
                        <CodeBlock
                            id="topic-position"
                            code={`# ROS 1
rostopic pub /robot_pose geometry_msgs/PoseStamped "{
  header: {frame_id: 'map'},
  pose: {
    position: {x: 1.0, y: 2.0, z: 0.0},
    orientation: {x: 0.0, y: 0.0, z: 0.0, w: 1.0}
  }
}" -r 10

# ROS 2
ros2 topic pub /robot_pose geometry_msgs/msg/PoseStamped "{
  header: {frame_id: 'map'},
  pose: {
    position: {x: 1.0, y: 2.0, z: 0.0},
    orientation: {x: 0.0, y: 0.0, z: 0.0, w: 1.0}
  }
}" -r 10`}
                        />
                    </div>

                    <div className="bg-slate-800/50 p-4 rounded-lg">
                        <h4 className="font-semibold text-white mb-2">Battery Topic</h4>
                        <p className="text-sm text-slate-400 mb-2">Topic: <code className="text-sci-accent">/battery_state</code> | Type: <code>sensor_msgs/BatteryState</code></p>
                        <CodeBlock
                            id="topic-battery"
                            code={`# ROS 1
rostopic pub /battery_state sensor_msgs/BatteryState "{percentage: 0.85}" -r 1

# ROS 2
ros2 topic pub /battery_state sensor_msgs/msg/BatteryState "{percentage: 0.85}" -r 1`}
                        />
                    </div>

                    <div className="bg-slate-800/50 p-4 rounded-lg">
                        <h4 className="font-semibold text-white mb-2">Goal Position Topic (Subscribe)</h4>
                        <p className="text-sm text-slate-400 mb-2">Your robot should subscribe to: <code className="text-sci-accent">/goal_pose</code> | Type: <code>geometry_msgs/PoseStamped</code></p>
                        <p className="text-xs text-slate-500 mb-2">The web app sends target positions (not velocity). Your robot should navigate to these goal positions.</p>
                        <CodeBlock
                            id="topic-command"
                            code={`# ROS 1 - Subscribe to goal positions
rostopic echo /goal_pose

# Example: Robot receives goals like this
# header:
#   frame_id: "map"
# pose:
#   position: {x: 2.5, y: 3.0, z: 0.0}  # in meters
#   orientation: {x: 0, y: 0, z: 0, w: 1}

# ROS 2
ros2 topic echo /goal_pose`}
                        />
                    </div>

                    <div className="bg-slate-800/50 p-4 rounded-lg">
                        <h4 className="font-semibold text-white mb-2">Auto Scan Topic (Subscribe)</h4>
                        <p className="text-sm text-slate-400 mb-2">Topic: <code className="text-sci-accent">/auto_scan</code> | Type: <code>std_msgs/String</code></p>
                        <p className="text-xs text-slate-500 mb-2">Receives "START" or "STOP" to control autonomous scanning.</p>
                        <CodeBlock
                            id="topic-autoscan"
                            code={`# ROS 1
rostopic echo /auto_scan

# ROS 2
ros2 topic echo /auto_scan`}
                        />
                    </div>

                    <div className="bg-slate-800/50 p-4 rounded-lg">
                        <h4 className="font-semibold text-white mb-2">Status Topic (Publish)</h4>
                        <p className="text-sm text-slate-400 mb-2">Topic: <code className="text-sci-accent">/robot_status</code> | Type: <code>std_msgs/String</code></p>
                        <p className="text-xs text-slate-500 mb-2">Publish your robot's current state as a JSON string to sync with the app.</p>
                        <CodeBlock
                            id="topic-status"
                            code={`# Example JSON Payload:
# {
#   "status": "SCANNING",
#   "autoMode": true,
#   "currentTask": "Scanning Rack R-1"
# }

# ROS 1
rostopic pub /robot_status std_msgs/String "data: '{\\"status\\": \\"SCANNING\\", \\"autoMode\\": true}'" -r 1

# ROS 2
ros2 topic pub /robot_status std_msgs/msg/String "data: '{\\"status\\": \\"SCANNING\\", \\"autoMode\\": true}'" -r 1`}
                        />
                    </div>

                    <div className="bg-slate-800/50 p-4 rounded-lg">
                        <h4 className="font-semibold text-white mb-2">WiFi Signal Topic (Optional)</h4>
                        <CodeBlock
                            id="topic-wifi"
                            code={`# ROS 1
rostopic pub /wifi_signal std_msgs/Float32 "data: 75.0" -r 1

# ROS 2
ros2 topic pub /wifi_signal std_msgs/msg/Float32 "data: 75.0" -r 1`}
                        />
                    </div>
                </div>
            </div>

            {/* Step 5: Test Connection */}
            <div className="bg-sci-panel rounded-xl border border-slate-700 p-6">
                <div className="flex items-center space-x-3 mb-4">
                    <CheckCircle className="text-sci-accent" size={24} />
                    <h3 className="text-xl font-semibold text-white">Step 5: Test Connection</h3>
                </div>

                <div className="space-y-3">
                    <div className="flex items-start space-x-3">
                        <div className="bg-sci-accent text-white rounded-full w-6 h-6 flex items-center justify-center flex-shrink-0 mt-0.5 text-sm">1</div>
                        <div>
                            <p className="text-white font-medium">Start rosbridge on robot</p>
                            <code className="text-xs text-slate-400">roslaunch rosbridge_server rosbridge_websocket.launch address:=0.0.0.0</code>
                        </div>
                    </div>
                    <div className="flex items-start space-x-3">
                        <div className="bg-sci-accent text-white rounded-full w-6 h-6 flex items-center justify-center flex-shrink-0 mt-0.5 text-sm">2</div>
                        <div>
                            <p className="text-white font-medium">Expose to internet (using ngrok example)</p>
                            <code className="text-xs text-slate-400">ngrok tcp 9090</code>
                        </div>
                    </div>
                    <div className="flex items-start space-x-3">
                        <div className="bg-sci-accent text-white rounded-full w-6 h-6 flex items-center justify-center flex-shrink-0 mt-0.5 text-sm">3</div>
                        <div>
                            <p className="text-white font-medium">Open web app</p>
                            <code className="text-xs text-slate-400">http://localhost:3002</code>
                        </div>
                    </div>
                    <div className="flex items-start space-x-3">
                        <div className="bg-sci-accent text-white rounded-full w-6 h-6 flex items-center justify-center flex-shrink-0 mt-0.5 text-sm">4</div>
                        <p className="text-white font-medium">Go to Settings tab</p>
                    </div>
                    <div className="flex items-start space-x-3">
                        <div className="bg-sci-accent text-white rounded-full w-6 h-6 flex items-center justify-center flex-shrink-0 mt-0.5 text-sm">5</div>
                        <p className="text-white font-medium">Select "Real Robot Mode"</p>
                    </div>
                    <div className="flex items-start space-x-3">
                        <div className="bg-sci-accent text-white rounded-full w-6 h-6 flex items-center justify-center flex-shrink-0 mt-0.5 text-sm">6</div>
                        <div>
                            <p className="text-white font-medium">Enter WebSocket URL</p>
                            <code className="text-xs text-slate-400">ws://0.tcp.ngrok.io:12345</code>
                        </div>
                    </div>
                    <div className="flex items-start space-x-3">
                        <div className="bg-sci-accent text-white rounded-full w-6 h-6 flex items-center justify-center flex-shrink-0 mt-0.5 text-sm">7</div>
                        <p className="text-white font-medium">Click "Save Settings"</p>
                    </div>
                    <div className="flex items-start space-x-3">
                        <div className="bg-sci-success text-white rounded-full w-6 h-6 flex items-center justify-center flex-shrink-0 mt-0.5 text-sm">✓</div>
                        <p className="text-white font-medium">Check connection status shows "Connected"</p>
                    </div>
                </div>
            </div>

            {/* Example Python Node */}
            <div className="bg-sci-panel rounded-xl border border-slate-700 p-6">
                <div className="flex items-center space-x-3 mb-4">
                    <Code className="text-sci-accent" size={24} />
                    <h3 className="text-xl font-semibold text-white">Example Robot Node (Python)</h3>
                </div>

                <p className="text-sm text-slate-300 mb-4">A simple Python node that publishes all required topics for testing:</p>
                <CodeBlock
                    id="python-node"
                    code={`#!/usr/bin/env python3
import rospy
from geometry_msgs.msg import PoseStamped
from sensor_msgs.msg import BatteryState
from std_msgs.msg import Float32, String
from geometry_msgs.msg import Twist

class RobotPublisher:
    def __init__(self):
        rospy.init_node('robot_publisher')
        
        # Publishers
        self.pose_pub = rospy.Publisher('/robot_pose', PoseStamped, queue_size=10)
        self.battery_pub = rospy.Publisher('/battery_state', BatteryState, queue_size=10)
        self.wifi_pub = rospy.Publisher('/wifi_signal', Float32, queue_size=10)
        
        # Subscriber for commands
        rospy.Subscriber('/cmd_vel', Twist, self.cmd_callback)
        rospy.Subscriber('/goal_pose', PoseStamped, self.goal_callback)
        rospy.Subscriber('/auto_scan', String, self.scan_callback)
        
        # State
        self.x = 0.0
        self.y = 0.0
        self.battery = 0.85
        
    def cmd_callback(self, msg):
        rospy.loginfo(f"Received velocity command: linear={msg.linear.x}, angular={msg.angular.z}")

    def goal_callback(self, msg):
        rospy.loginfo(f"Received goal: x={msg.pose.position.x}, y={msg.pose.position.y}")
        # In a real robot, this would trigger navigation stack

    def scan_callback(self, msg):
        rospy.loginfo(f"Auto Scan Command: {msg.data}")
        
    def publish_data(self):
        rate = rospy.Rate(10)  # 10 Hz
        
        while not rospy.is_shutdown():
            # Publish pose
            pose_msg = PoseStamped()
            pose_msg.header.stamp = rospy.Time.now()
            pose_msg.header.frame_id = "map"
            pose_msg.pose.position.x = self.x
            pose_msg.pose.position.y = self.y
            pose_msg.pose.position.z = 0.0
            pose_msg.pose.orientation.w = 1.0
            self.pose_pub.publish(pose_msg)
            
            # Publish battery
            battery_msg = BatteryState()
            battery_msg.percentage = self.battery
            self.battery_pub.publish(battery_msg)
            
            # Publish WiFi
            wifi_msg = Float32()
            wifi_msg.data = 75.0
            self.wifi_pub.publish(wifi_msg)
            
            # Simulate movement
            self.x += 0.01
            self.y += 0.01
            
            rate.sleep()

if __name__ == '__main__':
    try:
        robot = RobotPublisher()
        robot.publish_data()
    except rospy.ROSInterruptException:
        pass`}
                />
                <div className="mt-4 space-y-2">
                    <p className="text-sm text-slate-300">Save as <code className="text-sci-accent">robot_publisher.py</code>, make executable, and run:</p>
                    <CodeBlock
                        id="run-python"
                        code={`chmod +x robot_publisher.py
./robot_publisher.py`}
                    />
                </div>
            </div>

            {/* Security */}
            <div className="bg-sci-panel rounded-xl border border-slate-700 p-6">
                <div className="flex items-center space-x-3 mb-4">
                    <Shield className="text-sci-accent" size={24} />
                    <h3 className="text-xl font-semibold text-white">Security Best Practices</h3>
                </div>

                <div className="space-y-3">
                    <div className="flex items-start space-x-3">
                        <div className="text-sci-warning text-xl">⚠️</div>
                        <div>
                            <p className="font-medium text-white">Use wss:// (secure WebSocket) in production</p>
                            <p className="text-sm text-slate-400">Encrypt communication with SSL/TLS</p>
                        </div>
                    </div>
                    <div className="flex items-start space-x-3">
                        <div className="text-sci-warning text-xl">⚠️</div>
                        <div>
                            <p className="font-medium text-white">Implement authentication</p>
                            <p className="text-sm text-slate-400">Use CloudFlare Access or similar at tunnel level</p>
                        </div>
                    </div>
                    <div className="flex items-start space-x-3">
                        <div className="text-sci-warning text-xl">⚠️</div>
                        <div>
                            <p className="font-medium text-white">Restrict IP access</p>
                            <p className="text-sm text-slate-400">Use firewall rules to limit connections</p>
                        </div>
                    </div>
                    <div className="flex items-start space-x-3">
                        <div className="text-sci-warning text-xl">⚠️</div>
                        <div>
                            <p className="font-medium text-white">Monitor connections</p>
                            <p className="text-sm text-slate-400">Set up alerts for unauthorized access attempts</p>
                        </div>
                    </div>
                    <div className="flex items-start space-x-3">
                        <div className="text-sci-warning text-xl">⚠️</div>
                        <div>
                            <p className="font-medium text-white">Keep rosbridge updated</p>
                            <p className="text-sm text-slate-400">Install security patches regularly</p>
                        </div>
                    </div>
                </div>
            </div>

            {/* Troubleshooting */}
            <div className="bg-sci-panel rounded-xl border border-slate-700 p-6">
                <div className="flex items-center space-x-3 mb-4">
                    <Terminal className="text-sci-accent" size={24} />
                    <h3 className="text-xl font-semibold text-white">Troubleshooting</h3>
                </div>

                <div className="space-y-4">
                    <div>
                        <h4 className="font-semibold text-white mb-2">Connection Fails</h4>
                        <CodeBlock
                            id="troubleshoot-1"
                            code={`# 1. Check if rosbridge is listening on all interfaces (0.0.0.0)
netstat -tuln | grep 9090
# Should see: tcp 0 0 0.0.0.0:9090 ...

# 2. Check Firewall (Allow 9090)
sudo ufw allow 9090/tcp
sudo ufw allow 9090/udp
sudo ufw reload

# 3. If port 9090 is blocked/busy
sudo fuser -k 9090/tcp

# 3. Verify Tailscale is Connected
tailscale status

# 4. Test connection locally on robot
# (Install wscat: npm install -g wscat)
wscat -c ws://YOUR_TAILSCALE_IP:9090`}
                        />
                    </div>

                    <div>
                        <h4 className="font-semibold text-white mb-2">Topics Not Updating</h4>
                        <CodeBlock
                            id="troubleshoot-2"
                            code={`# List available topics
rostopic list  # ROS 1
ros2 topic list  # ROS 2

# Check topic data
rostopic echo /robot_pose  # ROS 1
ros2 topic echo /robot_pose  # ROS 2

# Verify rosbridge can see topics
npm install -g wscat
wscat -c ws://localhost:9090
{"op":"topics"}`}
                        />
                    </div>

                    <div className="bg-sci-accent/10 border border-sci-accent/20 p-4 rounded-lg">
                        <p className="text-sm text-white">
                            <strong>Tip:</strong> Enable Debug Mode in Settings → Advanced Settings to see detailed console logs
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
});
