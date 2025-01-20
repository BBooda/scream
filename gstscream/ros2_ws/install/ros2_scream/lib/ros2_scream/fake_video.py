#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import numpy as np
import cv2


class FakeVideoPublisher(Node):
    def __init__(self):
        super().__init__('fake_video_publisher')

        # Create a publisher for the "video_frames" topic
        self.publisher_ = self.create_publisher(Image, 'video_frames', 10)

        # Initialize OpenCV-to-ROS bridge
        self.bridge = CvBridge()

        # Timer to publish frames at 30 FPS
        self.timer = self.create_timer(1 / 30.0, self.publish_fake_frame)

        self.get_logger().info("FakeVideoPublisher node has been started.")

    def publish_fake_frame(self):
        # Create a synthetic video frame (e.g., random noise)
        # height, width = 720, 1280

        height, width = 720, 1280
        frame = np.random.randint(0, 256, (height, width, 3), dtype=np.uint8)  # Random noise

        # Alternatively, create a gradient pattern (replace above line with this):
        # frame = np.tile(np.linspace(0, 255, width, dtype=np.uint8), (height, 1))
        # frame = cv2.merge([frame, frame, frame])  # Create a grayscale gradient

        # Convert the frame to a ROS Image message
        msg = self.bridge.cv2_to_imgmsg(frame, encoding="bgr8")

        # Publish the message
        self.publisher_.publish(msg)

        self.get_logger().info("Published a fake video frame.")


def main(args=None):
    rclpy.init(args=args)

    fake_video_publisher = FakeVideoPublisher()

    try:
        rclpy.spin(fake_video_publisher)
    except KeyboardInterrupt:
        pass

    fake_video_publisher.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()

