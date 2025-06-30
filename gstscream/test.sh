#!/bin/bash
# source ~/gstreamer/ros2_ws/src/install/setup.bash
source ~/Documents/gitrepos/ros_scream_int/scream/gstscream/ros2_bridge/src/install/setup.bash

set -v

COLCON_PREFIX_PATH=dirname "~/Documents/gitrepos/ros_scream_int/scream/gstscream/ros2_bridge/src/install"
echo "COLCON_PREFIX_PATH="$COLCON_PREFIX_PATH
ROS_BRIDGE_PLUGIN=$COLCON_PREFIX_PATH/gst_bridge/lib/gst_bridge/
# /gstscream/ros2_bridge/src/install/gst_bridge/lib/gst_bridge/

echo "ROS_BRIDGE_PLUGIN="$ROS_BRIDGE_PLUGIN
ls $ROS_BRIDGE_PLUGIN

export GST_PLUGIN_PATH=$ROS_BRIDGE_PLUGIN

gst-inspect-1.0 rosimagesrc
