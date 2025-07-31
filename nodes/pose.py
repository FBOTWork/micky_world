#!/usr/bin/env python

import rospy
from work_world.plugins import PosePlugin

if __name__ == '__main__':
  rospy.init_node('pose_plugin')
  plugin = PosePlugin()
  plugin.run()