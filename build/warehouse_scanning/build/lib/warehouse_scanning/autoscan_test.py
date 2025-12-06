#!/usr/bin/env python3
# Autoscan Test Node for QR Camera Module
# This node allows manual testing of the autoscan feature by publishing
# Bool messages to the 'autoscan' topic based on user input.



import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool


class AutoscanTestNode(Node):
    def __init__(self):
        super().__init__('autoscan_test_node')
        self.publisher = self.create_publisher(Bool, 'autoscan', 10)
        self.get_logger().info('Autoscan Test Node Started')
        self.get_logger().info('Commands: "on" to enable, "off" to disable, "quit" to exit')
    
    def publish_command(self, enable):
        msg = Bool()
        msg.data = enable
        self.publisher.publish(msg)
        status = "ON" if enable else "OFF"
        self.get_logger().info(f'Published autoscan: {status}')


def main(args=None):
    rclpy.init(args=args)
    node = AutoscanTestNode()
    
    print("\n" + "="*50)
    print("AUTOSCAN CONTROL TEST NODE")
    print("="*50)
    print("Type 'on' to enable autoscan")
    print("Type 'off' to disable autoscan")
    print("Type 'quit' to exit")
    print("="*50 + "\n")
    
    try:
        while rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.1)
            
            # Simple input (blocking)
            try:
                import sys
                import select
                if select.select([sys.stdin], [], [], 0)[0]:
                    cmd = sys.stdin.readline().strip().lower()
                    
                    if cmd == 'on':
                        node.publish_command(True)
                    elif cmd == 'off':
                        node.publish_command(False)
                    elif cmd == 'quit':
                        break
                    else:
                        print("Invalid command. Use 'on', 'off', or 'quit'")
            except Exception as e:
                pass
                
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
