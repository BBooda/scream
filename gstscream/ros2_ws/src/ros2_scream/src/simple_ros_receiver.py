import cv2
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
from builtin_interfaces.msg import Time


class VideoPublisher(Node):
    def __init__(self):
        super().__init__('video_publisher')
        self.publisher_ = self.create_publisher(Image, '/received_frames', 10)
        self.bridge = CvBridge()

        # Open GStreamer pipeline to receive UDP stream
        self.cap = cv2.VideoCapture(
            "udpsrc port=30112 ! application/x-rtp,encoding-name=JPEG,payload=26 ! rtpjpegdepay ! jpegdec ! videoconvert ! video/x-raw,format=BGR ! appsink",
            cv2.CAP_GSTREAMER
        )

        if not self.cap.isOpened():
            self.get_logger().error("Failed to open UDP GStreamer pipeline.")
            return

        self.timer = self.create_timer(0.033, self.publish_frame)  # ~30 FPS

        # this is the period of the Image messages that is stable and defined by the camera configuration
        # there are certain assumptions that lead to this. Use with caution
        # here we have 15 Hz and around 66 [ms] between each message
        self.period = 0.066
        self.previous_timestamp = None

    def publish_frame(self):
        ret, frame = self.cap.read()
        if ret:
            msg = self.bridge.cv2_to_imgmsg(frame, encoding="bgr8")
            msg.header.stamp = self.get_clock().now().to_msg()
            if self.previous_timestamp != None:
                delay = self.calculate_delay(self.previous_timestamp, msg.header.stamp)
                self.get_logger().info(f"Current delay: {delay}")
            self.previous_timestamp = msg.header.stamp
            self.publisher_.publish(msg)
            self.get_logger().info("Published a video frame.", throttle_duration_sec = 2)


    def calculate_delay(self, prev: Time, curr: Time) -> float:
        """Calculate delay in seconds between two ROS2 Time messages."""
        prev_sec = prev.sec + prev.nanosec * 1e-9
        curr_sec = curr.sec + curr.nanosec * 1e-9
        return curr_sec - prev_sec + self.period

    def destroy_node(self):
        self.cap.release()
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    node = VideoPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        print("Terminating script...")
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()

