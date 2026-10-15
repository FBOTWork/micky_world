#!/usr/bin/env python3

import rclpy
import yaml
from pathlib import Path

from rclpy.qos import QoSProfile, QoSDurabilityPolicy, QoSReliabilityPolicy
from ament_index_python.packages import get_package_share_directory
from rclpy.exceptions import ROSInterruptException
from rclpy.wait_for_message import wait_for_message
from geometry_msgs.msg import PoseWithCovarianceStamped
from collections import OrderedDict
from rclpy.node import Node

'''
Save the current pose in the specified topic to a yaml file.
Created by Gabriel Dorneles on 2024-10-06.
Port to ROS2 by Vitor Anello on 2025-05-07.
Improved by Erick Manetti on 2026-10-07 
'''


class OrderedDumper(yaml.SafeDumper):
    '''
    @brief Custom YAML dumper to handle OrderedDict.
    '''
    def represent_ordereddict(self, data):
        return self.represent_dict(data.items())
    
class OrderedLoader(yaml.SafeLoader):
    pass

def construct_ordered_dict(loader, node):
    '''
    @brief Custom YAML loader to handle OrderedDict.
    '''
    return OrderedDict(loader.construct_pairs(node))

OrderedLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    construct_ordered_dict
)

class PoseWriter (Node):
    '''
    @class PoseWriter
    @brief A ROS 2 node that saves the current pose of a robot to a YAML file.
    This node subscribes to a specified pose topic and allows the user to save the current pose
    by entering a name. The saved poses are stored in a YAML file for later use.
    '''
    
    def __init__(self):
        '''
        @brief Constructor for the PoseWriter node.
        '''

        super().__init__(node_name='pose_writer')
    
        self.poses = {'pose': {'targets': OrderedDict()}}
        self.current_pose = None

        package_share = Path(get_package_share_directory('micky_world'))
        package_name = package_share.name
        workspace_dir = package_share.parents[3]
        self.config_path = workspace_dir / "src" / package_name / package_name / "config"

        while True:
            self.yaml_file = input("Enter the name of the file to save the poses (e.g., 'pose_inspection.yaml'): ").strip()
            if not self.yaml_file:
                self.get_logger().warning("No file name provided. Please try again.")
                continue
            if not self.yaml_file.endswith('.yaml'):
                self.yaml_file += '.yaml'
            break
        self.yaml_path = self.config_path / self.yaml_file
        if self.yaml_path.exists():
            self.get_logger().info(f"File '{self.yaml_file}' already exists. New poses will be appended to it.")
        self.declare_parameter('~pose_topic', '/amcl_pose')
        self.pose_topic = self.get_parameter('~pose_topic').get_parameter_value().string_value

        qos_profile = QoSProfile(
            depth=1,
            reliability=QoSReliabilityPolicy.RELIABLE,
            durability=QoSDurabilityPolicy.TRANSIENT_LOCAL
        )

        self.subscription = self.create_subscription(
            PoseWithCovarianceStamped,
            self.pose_topic,
            self.pose_callback,
            qos_profile
        )

    def pose_callback(self, msg):
        self.current_pose = msg.pose.pose

    def save_pose(self) -> None:
        '''
        @brief Save the current pose in the specified topic to a yaml file.
        '''

        while rclpy.ok():
            self.get_logger().info("Ready to save a new pose.")
            pose_name = input("Move the robot to the desired pose and enter its name (e.g., 'garbage_1', 'exit'): ")

            if not pose_name:
                self.get_logger().warning("No name provided, skipping pose.")
                continue

            current_pose = self.current_pose
            self.get_logger().info(f"Received pose: {current_pose}")
            if current_pose is None:
                self.get_logger().warning("No pose received from topic yet. Make sure AMCL is running and publishing to /amcl_pose.")
                continue

            self.poses['pose']['targets'][pose_name] = OrderedDict([
                ('px', current_pose.position.x),
                ('py', current_pose.position.y),
                ('pz', current_pose.position.z),
                ('ox', current_pose.orientation.x),
                ('oy', current_pose.orientation.y),
                ('oz', current_pose.orientation.z),
                ('ow', current_pose.orientation.w)
            ])

            self.get_logger().info(f"Pose '{pose_name}' saved.")

            while True:
                save_now = input("Do you want to add more poses? (Y/n): ").strip().lower()
                if save_now == 'n':
                    self.write_to_yaml()
                    self.get_logger().info(f"Poses saved to {self.yaml_file}. Shutting down node.")
                    return

                elif save_now in ('', 'y'):
                    break
                else:
                    self.get_logger().warning("Invalid input. Please enter 'y' or 'n'.")

    def write_to_yaml(self):
        '''
        @brief Write the collected poses to a YAML file.
        '''
        OrderedDumper.add_representer(OrderedDict, OrderedDumper.represent_ordereddict)

        if self.yaml_path.exists():
            self.get_logger().info(f"{self.yaml_file} already exists. The new poses will be appended to the existing data.")

            with open(self.yaml_path, 'r') as yaml_file:
                try:
                    existing_data = yaml.load(yaml_file, Loader=OrderedLoader) or OrderedDict()
                except yaml.YAMLError as e:
                    self.get_logger().error(f"Error reading {self.yaml_file}: {e}")
                    existing_data = OrderedDict()
        else:
            self.get_logger().info(f"{self.yaml_file} does not exist. Creating a new file at {self.yaml_path}.")
            existing_data = OrderedDict()

        if not isinstance(existing_data, dict):
            existing_data = OrderedDict()

        if 'pose' not in existing_data or not isinstance(existing_data['pose'], dict):
            existing_data['pose'] = OrderedDict()

        if 'targets' not in existing_data['pose'] or not isinstance(existing_data['pose']['targets'], dict):
            if 'targets' in existing_data and isinstance(existing_data['targets'], dict):
                existing_data['pose']['targets'] = existing_data.pop('targets')
            else:
                existing_data['pose']['targets'] = OrderedDict()
        elif 'targets' in existing_data:
            existing_data['pose']['targets'].update(existing_data.pop('targets'))

        existing_data['pose']['targets'].update(self.poses['pose']['targets'])
        self.config_path.mkdir(parents=True, exist_ok=True)
        with open(self.yaml_path, 'w') as yaml_file:
            yaml.dump(existing_data, yaml_file, default_flow_style=False, Dumper=OrderedDumper)

        return


def main(args=None) -> None:
    try:
        rclpy.init(args=args)
        saver = PoseWriter()

        import threading
        spin_thread = threading.Thread(target=rclpy.spin, args=(saver,))
        spin_thread.start()
        
        try:
            saver.save_pose()
        except KeyboardInterrupt:
            pass

        saver.destroy_node()
        rclpy.try_shutdown()
        spin_thread.join()

    except ROSInterruptException:
        pass

if __name__ == '__main__':
    main()