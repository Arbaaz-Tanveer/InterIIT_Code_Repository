from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        # 1. Controller (C++) - Located in warehouse_navigation
        Node(
            package="warehouse_navigation", 
            executable="controller1", 
            output="screen"
        ),

        # 2. Robot Simulation - Located in warehouse_robot_bringup
        # Note: Assuming entry point is 'robot_sim'. If it fails, check setup.py in bringup
        Node(
            package="warehouse_robot_bringup", 
            executable="robot_sim", 
            output="screen"
        ),

        # 3. Target GUI - Located in warehouse_hmi
        Node(
            package="warehouse_hmi", 
            executable="target_gui", 
            output="screen"
        ),

        # 4. Path Planner (Python) - Located in warehouse_navigation
        # Note: Since we installed it via CMake, the name includes .py
        Node(
            package="warehouse_navigation", 
            executable="path_planner.py", 
            output="screen"
        ),

        # 5. Main Logic - Located in warehouse_robot_bringup
        Node(
            package="warehouse_robot_bringup", 
            executable="main", 
            output="screen"
        ),

        # 6. Keyboard Controller - Located in warehouse_hmi
        Node(
            package="warehouse_hmi", 
            executable="keyboard_controller", 
            output="screen"
        ),
    ])
