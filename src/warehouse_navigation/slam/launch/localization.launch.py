import os
import xacro
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    package_name = 'slam'
    urdf_file_name = 'final_bot.urdf.xacro'   # rename properly
    ekf_config_name = 'ekf.yaml'

    # paths
    pkg_share = get_package_share_directory(package_name)
    urdf_path = os.path.join(pkg_share, 'urdf', urdf_file_name)
    ekf_config_path = os.path.join(pkg_share, 'config', ekf_config_name)

    # PROCESS XACRO → URDF XML
    robot_description_raw = xacro.process_file(urdf_path)
    robot_desc = robot_description_raw.toxml()
    
    joint_state_pub = Node(
        package='joint_state_publisher',
        executable='joint_state_publisher',
        name='joint_state_publisher'
    )
    # Robot State Publisher
    rsp_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description': robot_desc}]
    )

    # Data Converter Node
    data_converter_node = Node(
        package=package_name,
        executable='data_converter',
        name='data_converter_node',
        output='screen'
    )

    # EKF Node
    ekf_node = Node(
        package='robot_localization',
        executable='ekf_node',
        name='ekf_filter_node',
        output='screen',
        parameters=[ekf_config_path]
    )

    return LaunchDescription([
        joint_state_pub,
        rsp_node,
        data_converter_node,
        ekf_node
    ])

