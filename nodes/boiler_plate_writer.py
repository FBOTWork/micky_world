#!/usr/bin/env python3

import rospy
from work_world.plugins import HeartbeatWriterPlugin

if __name__ == '__main__':
  rospy.init_node('boiler_plate_writer')
  plugin = HeartbeatWriterPlugin()
  plugin.run()