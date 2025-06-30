import sys
if sys.prefix == '/usr':
    sys.real_prefix = sys.prefix
    sys.prefix = sys.exec_prefix = '/home/eamrgde/Documents/gitrepos/ros_scream_int/scream/gstscream/ros2_bridge/src/install/gst_pipeline'
