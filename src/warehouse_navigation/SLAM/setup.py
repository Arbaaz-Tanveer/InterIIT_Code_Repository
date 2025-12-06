from setuptools import find_packages, setup
from glob import glob
import os

package_name = 'SLAM'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        # Required for ROS 2 package indexing
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),

        # Install package.xml
        ('share/' + package_name, ['package.xml']),

        # Install ALL launch files
        ('share/' + package_name + '/launch', glob('launch/*.py')),

        # Install URDF/XACRO files
        ('share/' + package_name + '/urdf', glob('urdf/*')),
        ('share/' + package_name + '/rviz', glob('rviz/*')),
        
        # Install YAML config files (including ekf.yaml)
        ('share/' + package_name + '/config', glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='shivansh',
    maintainer_email='shivanshg23@iitk.ac.in',
    description='Robot bringup package',
    license='Apache License 2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'data_converter = my_robot_bringup.data_converter:main',
        ],
    },
)

