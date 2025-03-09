import cv2
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge

class VideoPublisher(Node):
    def __init__(self):
        super().__init__('video_publisher')
        self.publisher_ = self.create_publisher(Image, '/received_frames', 10)
        self.bridge = CvBridge()

        # Open GStreamer pipeline to receive UDP stream
        self.cap = cv2.VideoCapture(
            "udpsrc port=5004 ! application/x-rtp,encoding-name=JPEG,payload=26 ! rtpjpegdepay ! jpegdec ! videoconvert ! video/x-raw,format=BGR ! appsink",
            cv2.CAP_GSTREAMER
        )

        if not self.cap.isOpened():
            self.get_logger().error("Failed to open UDP GStreamer pipeline.")
            return

        self.timer = self.create_timer(0.033, self.publish_frame)  # ~30 FPS

    def publish_frame(self):
        ret, frame = self.cap.read()
        if ret:
            msg = self.bridge.cv2_to_imgmsg(frame, encoding="bgr8")
            self.publisher_.publish(msg)
            self.get_logger().info("Published a video frame.", throttle_duration_sec = 2)

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
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()

