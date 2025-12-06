import os
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch_ros.actions import Node
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():

    pkg_bringup = get_package_share_directory('SLAM')
    pkg_slam = get_package_share_directory('slam_toolbox')
    pkg_rplidar = get_package_share_directory('rplidar_ros')

    # 1. Localization (your file)
    localization = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_bringup, 'launch', 'localization.launch.py')
        )
    )

    # 2. SLAM Toolbox online_async
    slam = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_bringup, 'launch', 'online_async_launch.py')
        )
    )

    # 3. RPLIDAR A1 driver
    rplidar = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_bringup, 'launch', 'rplidar_a1_launch.py')
        )
    )
    
    rviz_config_path=os.path.join(pkg_bringup, 'rviz', 'my_robot.rviz')
    rviz=Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', rviz_config_path]
    )
    scan_filter = Node(
        package='laser_filters',
        executable='scan_to_scan_filter_chain',
        name='scan_filter',
        parameters=[
            {'filter_chain_parameter_name': 'laser_scan_filter_chain'},
            os.path.join(pkg_bringup, 'config', 'scan_filters.yaml')
        ],
        remappings=[
            ('scan', '/scan'),                  # input from lidar
            ('scan_filtered', '/scan_filtered') # output of filter
        ]
    )

    return LaunchDescription([
        rplidar,
        scan_filter,
        localization,
        slam,
        rviz,
    ])
