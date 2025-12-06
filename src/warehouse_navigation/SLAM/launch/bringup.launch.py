

import os
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, ExecuteProcess, RegisterEventHandler, LogInfo
from launch.event_handlers import OnShutdown
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():

    pkg_bringup = get_package_share_directory('SLAM')
    pkg_slam = get_package_share_directory('slam_toolbox')
    pkg_rplidar = get_package_share_directory('rplidar_ros')

    localization = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_bringup, 'launch', 'localization.launch.py')
        )
    )

    slam = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_bringup, 'launch', 'online_async_launch.py')
        )
    )

    rplidar = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_bringup, 'launch', 'rplidar_a1_launch.py')
        )
    )

    rviz_config_path = os.path.join(pkg_bringup, 'rviz', 'my_robot.rviz')
    rviz = Node(
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
            ('scan', '/scan'),
            ('scan_filtered', '/scan_filtered')
        ]
    )

  
    save_map_cmd = [
        'bash', '-lc',
        "ros2 service call /slam_toolbox/save_map slam_toolbox/srv/SaveMap \"name: {data: 'final_map'}\" || echo 'save_map call failed'"
    ]
    save_map_action = ExecuteProcess(
        cmd=save_map_cmd,
        output='screen'
    )


    shutdown_handler = RegisterEventHandler(
        OnShutdown(
            on_shutdown=[
                LogInfo(msg=['Launch asked to shutdown - saving map...']),
                save_map_action
            ]
        )
    )

    return LaunchDescription([
        rplidar,
        scan_filter,
        localization,
        slam,
        rviz,
        shutdown_handler,
    ])
