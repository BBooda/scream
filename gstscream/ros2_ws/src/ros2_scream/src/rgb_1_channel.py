#!/usr/bin/env python3
import rclpy
from rclpy import publisher
from rclpy.node import Node
from sensor_msgs.msg import Image
import gi
import numpy as np
from cv_bridge import CvBridge


class RGB_to_gray(Node):
    def __init__(self, topic_name):
        super().__init__('gstreamer_ros2_bridge')


        self.bridge = CvBridge()

        self.subscription = self.create_subscription(
            Image, topic_name, self.image_callback, 10
        )

        self.publisher = self.create_publisher(
           Image, 'test_gray_scale', 10
        )


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

            # transform to grayscale
            channel_1_frame = frame[:,:,1]
            gray_image_msg = self.bridge.cv2_to_imgmsg(channel_1_frame, encoding="mono8")
            # self.get_logger().info(msg, once=True)
            gray_image_msg.header = msg.header
            print(gray_image_msg.header)
            self.publisher.publish(
               gray_image_msg 
            )

        except Exception as e:
            self.get_logger().error(f"Error processing image: {e}")



def main():
    # Initialize ROS 2
    rclpy.init()

    # Create the node and pass the topic name
    topic_name = 'husky1/camera/color/image_raw'
    # topic_name = 'husky1/camera/color/image_raw'
    node = RGB_to_gray(topic_name)

    try:
        # Spin the node to process ROS 2 messages
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        # Cleanup
        node.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    main()




