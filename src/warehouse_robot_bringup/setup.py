from setuptools import setup
import os
from glob import glob

package_name = 'warehouse_robot_bringup'

setup(
    name=package_name,
    version='0.0.1',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        # Include launch files
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        # Include config files (if any exist in config folder)
        # (os.path.join('share', package_name, 'config'), glob('config/*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='User',
    maintainer_email='user@example.com',
    description='Bringup package for Warehouse Robot',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            # These match the 'executable' names in your launch file
            'robot_sim = warehouse_robot_bringup.robot_sim:main',
            'main = warehouse_robot_bringup.main:main',
            'hardware = warehouse_robot_bringup.hardware:main',
        ],
    },
)
