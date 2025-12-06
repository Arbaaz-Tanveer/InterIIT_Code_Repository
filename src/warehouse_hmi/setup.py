from setuptools import setup
import os
from glob import glob

package_name = 'warehouse_hmi'

setup(
    name=package_name,
    version='0.0.1',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='User',
    maintainer_email='user@example.com',
    description='HMI package for Warehouse Robot',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'target_gui = warehouse_hmi.target_gui:main',
            'keyboard_controller = warehouse_hmi.keyboard_controller:main',
            'speaker_module = warehouse_hmi.speaker_module:main',
        ],
    },
)
