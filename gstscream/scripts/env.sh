export ECN_ENABLED=0
echo "------------------------------------------------------------------------------------"
echo "------------------------------------------------------------------------------------"
# source ~/gstreamer/ros2_ws/src/install/setup.bash
# export ROS_BRIDGE_PLUGIN="/home/eamrgde/Documents/gitrepos/jacob_l4s_ros/ros2_ws/src/install/gst_bridge/lib/gst_bridge"
# echo "COLCON_PREFIX_PATH="$COLCON_PREFIX_PATH
# ROS_BRIDGE_PLUGIN=$COLCON_PREFIX_PATH/gst_bridge/lib/gst_bridge
# echo "ROS_BRIDGE_PLUGIN="$ROS_BRIDGE_PLUGIN
# source ~/gstreamer/ros2_ws/src/install/setup.bash
# echo "COLCON_PREFIX_PATH="$COLCON_PREFIX_PATH
# ROS_BRIDGE_PLUGIN=$COLCON_PREFIX_PATH/gst_bridge/lib/gst_bridge
#
# echo "ROS_BRIDGE_PLUGIN="$ROS_BRIDGE_PLUGIN
# export GST_PLUGIN_PATH=$ROS_BRIDGE_PLUGIN

source ~/Documents/gitrepos/ros_scream_int/scream/gstscream/ros2_bridge/src/install/setup.bash
COLCON_PREFIX_PATH=dirname "~/Documents/gitrepos/ros_scream_int/scream/gstscream/ros2_bridge/src/install"
echo "COLCON_PREFIX_PATH="$COLCON_PREFIX_PATH
ROS_BRIDGE_PLUGIN=$COLCON_PREFIX_PATH/gst_bridge/lib/gst_bridge/
# export GST_PLUGIN_PATH=$ROS_BRIDGE_PLUGIN
ls $ROS_BRIDGE_PLUGIN

# gst-inspect-1.0 rosimagesrc
echo "ROS_BRIDGE_PLUGIN="$ROS_BRIDGE_PLUGIN
echo "------------------------------------------------------------------------------------"
echo "------------------------------------------------------------------------------------"

# gst-inspect-1.0 rosimagesrc


if (($ECN_ENABLED == 1)); then
export SET_ECN="set-ecn=1"
export SCREAMTX_PARAM_ECT="-ect 1"
export RETRIEVE_ECN="retrieve-ecn=true"

MY_GST_INSTALL=$(readlink -f $SCRIPT_DIR/../../../udp_gstreamer/install)
echo "MY_GST_INSTALL=$MY_GST_INSTALL"

# export GST_PLUGIN_PATH=$ROS_BRIDGE_PLUGIN
# export GST_PLUGIN_PATH=$GST_PLUGIN_PATH:$MY_GST_INSTALL/lib/x86_64-linux-gnu
export GST_PLUGIN_PATH=$MY_GST_INSTALL/lib/x86_64-linux-gnu
export GST_PLUGIN_PATH=$GST_PLUGIN_PATH:$MY_GST_INSTALL/lib/x86_64-linux-gnu/gstreamer-1.0
export GST_PLUGIN_PATH=$GST_PLUGIN_PATH:/usr/lib/x86_64-linux-gnu/gstreamer-1.0
export GST_PLUGIN_PATH=$GST_PLUGIN_PATH:$ROS_BRIDGE_PLUGIN

gst-inspect-1.0 rosimagesrc
exit

export LD_LIBRARY_PATH=$MY_GST_INSTALL/lib/x86_64-linux-gnu
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$MY_GST_INSTALL/lib/x86_64-linux-gnu/gstreamer-1.0
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/lib/x86_64-linux-gnu/gstreamer-1.0

export PATH=$MY_GST_INSTALL/bin:$PATH
export PKG_CONFIG_PATH=$MY_GST_INSTALL/lib/x86_64-linux-gnu/pkgconfig
export PYTHONPATH=${PYTHONPATH}:$MY_GST_INSTALL/lib/python3/site-packages/
LP=$(pkg-config --libs-only-L  gstreamer-1.0 )
export RUSTFLAGS="$LP $RUSTFLAGS"
fi

SCREAMLIB_DIR=$SCRIPT_DIR/../../code/wrapper_lib
SCREAM_TARGET_DIR=$SCRIPT_DIR/../target/debug/
export GST_PLUGIN_PATH=$SCREAM_TARGET_DIR:$GST_PLUGIN_PATH
export GST_PLUGIN_PATH=$GST_PLUGIN_PATH:$ROS_BRIDGE_PLUGIN
export LD_LIBRARY_PATH=$SCREAMLIB_DIR:$LD_LIBRARY_PATH

# gst-inspect-1.0 rosimagesrc
# exit
echo "LD_LIBRARY_PATH=$LD_LIBRARY_PATH"
echo "GST_PLUGIN_PATH=$GST_PLUGIN_PATH"

export ENC_ID=264

SENDER_IP=127.0.0.2
RECEIVER_IP=127.0.0.1

PORT0_RTP=30112
PORT0_RTCP=30113

PORT1_RTP=30114
PORT1_RTCP=30115

PORT2_RTP=30116
PORT2_RTCP=30117

#ENCODER="x${ENC_ID}enc speed-preset=ultrafast tune=zerolatency key-int-max=10000 "
#only for x264:
ENCODER="x264enc speed-preset=ultrafast tune=fastdecode+zerolatency key-int-max=10000 "

#ENCODER="nvh${ENC_ID}enc zerolatency=true preset=low-latency-hq rc-mode=cbr-ld-hq gop-size=-1 "

DECODER=avdec_h${ENC_ID}
#DECODER=nvh${ENC_ID}dec
#

USE_SCREAM=1
#if you set USE_SCREAM=0, modify key-int-max or gop-size in ENCODER above to periodically resend I frames
