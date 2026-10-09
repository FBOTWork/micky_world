#!/usr/bin/env python3

import os

import rclpy
import yaml

from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy
from visualization_msgs.msg import Marker, MarkerArray
from ament_index_python.packages import get_package_share_directory

'''
Read the poses from a yaml file and publish them as markers to view in RViz.
Each pose is an arrow plus a text with its key. The file is read again on every
publish, so poses saved by pose_writer show up without restarting the node.
'''

# One color per group set (r, g, b), repeated if there are more groups.
GROUP_COLORS = [
  (0.1, 0.6, 1.0),
  (1.0, 0.5, 0.1),
  (0.2, 0.8, 0.3),
  (0.9, 0.2, 0.6),
]


class PoseMarkers(Node):
  """
    @class: PoseMarkers
    @brief: Publishes the poses of a yaml file as a MarkerArray.
  """

  def __init__(self, node_name: str = 'pose_markers'):
    """
    @brief: Constructor for PoseMarkers.
    @param: node_name: The name of the ROS2 node.
    """
    super().__init__(node_name)
    self.declareParameters()
    self.readParameters()

    qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
    self.publisher = self.create_publisher(MarkerArray, '/micky_world/pose_markers', qos)
    self.timer = self.create_timer(1.0 / self.rate, self.publishMarkers)
    self.get_logger().info(f"Publishing markers from: {self.file_path}")

  def declareParameters(self):
    """
    @brief: Declares parameters for the PoseMarkers node.
    """
    self.declare_parameter('config_file_name', 'poses')
    self.declare_parameter('frame_id', 'map')
    self.declare_parameter('rate', 1.0)

  def readParameters(self):
    """
    @brief: Reads parameters for the PoseMarkers node.
    The config_file_name can be a name inside the package config folder or a full path,
    with or without the .yaml extension.
    """
    name = self.get_parameter('config_file_name').get_parameter_value().string_value
    if not name.endswith('.yaml'):
      name += '.yaml'
    if os.path.isabs(name):
      self.file_path = name
    else:
      self.file_path = os.path.join(get_package_share_directory('micky_world'), 'config', name)
    self.frame_id = self.get_parameter('frame_id').get_parameter_value().string_value
    self.rate = self.get_parameter('rate').get_parameter_value().double_value

  def readPoses(self):
    '''
    @brief: Reads the yaml file.
    @return: A dict {group_set: {key: {px, py, pz, ox, oy, oz, ow}}}, empty if the file can not be read.
    '''
    try:
      with open(self.file_path, 'r') as file:
        return yaml.safe_load(file) or {}
    except (OSError, yaml.YAMLError) as e:
      self.get_logger().error(f"Could not read {self.file_path}: {e}", throttle_duration_sec=10.0)
      return {}

  def makeMarker(self, group_set: str, key: str, pose: dict, marker_id: int, color: tuple, text: bool):
    '''
    @brief: Creates the arrow (or text) marker of one pose.
    @param: group_set: The group set of the pose, used as marker namespace.
    @param: key: The key of the pose.
    @param: pose: Dict with px, py, pz, ox, oy, oz, ow.
    @param: marker_id: The id of the marker.
    @param: color: (r, g, b) of the marker.
    @param: text: True for the label, False for the arrow.
    @return: Marker
    '''
    marker = Marker()
    marker.header.frame_id = self.frame_id
    marker.header.stamp = self.get_clock().now().to_msg()
    marker.ns = group_set + ('/labels' if text else '/arrows')
    marker.id = marker_id
    marker.action = Marker.ADD
    marker.pose.position.x = float(pose.get('px', 0.0))
    marker.pose.position.y = float(pose.get('py', 0.0))
    marker.pose.position.z = float(pose.get('pz', 0.0))
    marker.pose.orientation.x = float(pose.get('ox', 0.0))
    marker.pose.orientation.y = float(pose.get('oy', 0.0))
    marker.pose.orientation.z = float(pose.get('oz', 0.0))
    marker.pose.orientation.w = float(pose.get('ow', 1.0))
    marker.color.r, marker.color.g, marker.color.b = color
    marker.color.a = 1.0

    if text:
      marker.type = Marker.TEXT_VIEW_FACING
      marker.text = key
      marker.pose.position.z += 0.3
      marker.scale.z = 0.2
      marker.color.r = marker.color.g = marker.color.b = 1.0
    else:
      marker.type = Marker.ARROW
      marker.scale.x = 0.5
      marker.scale.y = 0.08
      marker.scale.z = 0.08
    return marker

  def publishMarkers(self):
    '''
    @brief: Reads the yaml file and publishes one arrow and one label per pose.
    '''
    markers = MarkerArray()
    clear = Marker()
    clear.action = Marker.DELETEALL
    markers.markers.append(clear)

    for i, (group_set, poses) in enumerate(self.readPoses().items()):
      if not isinstance(poses, dict):
        continue
      color = GROUP_COLORS[i % len(GROUP_COLORS)]
      for marker_id, (key, pose) in enumerate(poses.items()):
        if not isinstance(pose, dict):
          continue
        markers.markers.append(self.makeMarker(group_set, str(key), pose, marker_id, color, False))
        markers.markers.append(self.makeMarker(group_set, str(key), pose, marker_id, color, True))

    self.publisher.publish(markers)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = PoseMarkers('pose_markers')

    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
