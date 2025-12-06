from setuptools import find_packages
from setuptools import setup

setup(
    name='warehouse_navigation',
    version='0.0.1',
    packages=find_packages(
        include=('warehouse_navigation', 'warehouse_navigation.*')),
)
