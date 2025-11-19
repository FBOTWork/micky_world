from setuptools import find_packages, setup
import os
import glob

package_name = 'micky_world'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'micky_world'), glob.glob('micky_world/*.py')),
        (os.path.join('share', package_name, 'launch'), glob.glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'world_scripts'), glob.glob('world_scripts/*.py')),
        (os.path.join('share', package_name, 'config'), glob.glob('config/*.yaml'))

    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='vitoranello',
    maintainer_email='vitoranello@gmail.com',
    description='TODO: Package description',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'pose = micky_world.pose:main',
            'pose_writer = micky_world.pose_writer:main',
            ],
    },
)
