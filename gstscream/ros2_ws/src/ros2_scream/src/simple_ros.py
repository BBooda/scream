#!/usr/bin/env python3
import rclpy
from rclpy import publisher
from rclpy.node import Node
from sensor_msgs.msg import Image
import gi
import numpy as np
from gi.repository import Gst, GLib, GObject
from cv_bridge import CvBridge

gi.require_version('Gst', '1.0')

class GStreamerROS2Bridge(Node):
    def __init__(self, topic_name):
        super().__init__('gstreamer_ros2_bridge')

        # Initialize GStreamer
        Gst.init(None)

        # Define the GStreamer pipeline
        pipeline_str = """
            appsrc name=mysource is-live=true format=TIME caps=video/x-raw,format=RGB,width=1280,height=720,framerate=30/1 !
            videoconvert ! x264enc tune=zerolatency ! rtph264pay ! udpsink host=127.0.0.1 port=30000
        """
        self.pipeline = Gst.parse_launch(pipeline_str)
        self.appsrc = self.pipeline.get_by_name("mysource")

        # Subscribe to the ROS 2 topic
        self.subscription = self.create_subscription(
            Image, topic_name, self.image_callback, 10
        )

        self.publisher = self.create_publisher(
           Image, 'test_gray_scale', 10
        )

        # Start the GStreamer pipeline
        self.pipeline.set_state(Gst.State.PLAYING)

        self.bridge = CvBridge()

    def image_callback(self, msg):
        """
        Callback function to handle incoming ROS 2 Image messages.
        """
        try:
            # Convert the ROS 2 Image message to a numpy array
            # Assuming the input is in RGB8 format
            frame = np.frombuffer(msg.data, dtype=np.uint8).reshape(msg.height, msg.width, 3)

            # Ensure the frame matches the pipeline's caps (e.g., resize if necessary)
            # In this example, we assume the image is already 320x240
            if frame.shape[0] != 720 or frame.shape[1] != 1280:
                self.get_logger().error("Image size mismatch. Expected 320x240.")
                return
            
            # # transform to grayscale
            # channel_1_frame = frame[:,:,1]
            # self.publisher.publish(
            #     self.bridge.cv2_to_imgmsg(channel_1_frame, encoding="mono8")
            # )

            # Create a GStreamer buffer from the frame
            buf = Gst.Buffer.new_wrapped(frame.tobytes())

            # Push the buffer into the appsrc element
            retval = self.appsrc.emit("push-buffer", buf)
            if retval != Gst.FlowReturn.OK:
                self.get_logger().error(f"Failed to push buffer: {retval}")

        except Exception as e:
            self.get_logger().error(f"Error processing image: {e}")

    def stop(self):
        # Stop the GStreamer pipeline on shutdown
        self.pipeline.set_state(Gst.State.NULL)

def main():
    # Initialize ROS 2
    rclpy.init()

    # Create the node and pass the topic name
    topic_name = '/husky1/camera/color/image_raw'
    # topic_name = 'husky1/camera/color/image_raw'
    node = GStreamerROS2Bridge(topic_name)

    try:
        # Spin the node to process ROS 2 messages
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        # Cleanup
        node.stop()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    main()

