from setuptools import find_packages
from setuptools import setup

setup(
    name='warehouse_msgs',
    version='0.0.1',
    packages=find_packages(
        include=('warehouse_msgs', 'warehouse_msgs.*')),
)
