#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
import subprocess
import datetime
import os

class KeyboardMapSaver(Node):
    def __init__(self):
        super().__init__('keyboard_map_saver')
        self.get_logger().info("Keyboard Map Saver Started")
        self.run_interactive_loop()

    def run_interactive_loop(self):
        print("\n" + "="*40)
        print("  INTERACTIVE MAP SAVER")
        print("="*40)
        print("This terminal is listening for your input.")
        print("Press [ENTER] to save the map.")
        print("Press [Ctrl+C] to exit.")
        print("="*40 + "\n")

        try:
            while True:
                input(">>> Press ENTER to save map now... ")
                self.save_map()
        except KeyboardInterrupt:
            print("\nExiting Map Saver...")

    def save_map(self):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        
        # Hardcoded save path as requested
        save_dir = "/home/era/Documents/fresh_start/InterIIT_Code_Repository/src/warehouse_navigation/slam/maps"
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
            
        map_name = f"map_{timestamp}"
        full_path_prefix = os.path.join(save_dir, map_name)
        
        # Determine command
        # We assume 'nav2_map_server' map_saver_cli is available
        cmd = ["ros2", "run", "nav2_map_server", "map_saver_cli", "-f", full_path_prefix]

        self.get_logger().info(f"Saving map as {map_name}...")
        print(f"Target Directory: {save_dir}")
        print(f"Executing: {' '.join(cmd)}")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                self.get_logger().info(f"SUCCESS: Map saved to {full_path_prefix}.yaml/.pgm")
                print(f"\033[92mSUCCESS: Saved {full_path_prefix}\033[0m")
                
                # --- Auto-Open Map Aligner ---
                try:
                    from ament_index_python.packages import get_package_share_directory
                    pkg_share = get_package_share_directory('slam')
                    aligner_script = os.path.join(pkg_share, 'scripts', 'map_aligner.py')
                    
                    if os.path.exists(aligner_script):
                        self.get_logger().info(f"Opening Map Aligner...")
                        print(f"Launching: {aligner_script}")
                        # Open in background (non-blocking)
                        subprocess.Popen(["python3", aligner_script, f"{full_path_prefix}.pgm"])
                    else:
                        self.get_logger().warn(f"Map aligner not found at {aligner_script}")
                except Exception as e:
                     self.get_logger().error(f"Failed to launch aligner: {e}")

            else:
                self.get_logger().error(f"FAILURE: {result.stderr}")
                print(f"\033[91mFAILURE: {result.stderr}\033[0m")
        except FileNotFoundError:
             self.get_logger().error("nav2_map_server not found. Is it installed?")

def main(args=None):
    rclpy.init(args=args)
    # We don't spin because we are blocking on input()
    # But we need rclpy init for logging if we want to use it
    node = KeyboardMapSaver()
    # node.destroy_node() # Not reached typically due to blocking loop
    rclpy.shutdown()

if __name__ == '__main__':
    main()
