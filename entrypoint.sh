#!/bin/bash
set -e

# setup ros2 environment
# source "/opt/ros/$ROS_DISTRO/setup.bash" && source /home/ros/dev_ws/install/local_setup.bash --
source "/opt/ros/$ROS_DISTRO/setup.bash"
# source /home/ros/simple_scream_ros_integration/gstscream/scripts/sysctl.sh

exec "$@"


