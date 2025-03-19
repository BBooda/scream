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

        print("CVBridge initialized")
        # Open GStreamer pipeline (NO CHANGES TO PIPELINE)
        self.cap = cv2.VideoCapture(
            "udpsrc port=5004 ! application/x-rtp,encoding-name=JPEG,payload=26 ! rtpjpegdepay ! jpegdec ! videoconvert ! video/x-raw,format=BGR ! appsink",
            cv2.CAP_GSTREAMER
        )

        # print("check if cap is open")
        if not self.cap.isOpened():
            self.get_logger().error("Failed to open GStreamer video source.")
            return

        # Event-based frame publishing (No fixed timer)
        self.run_event_loop()

    def run_event_loop(self):
        """Continuously checks for new frames and publishes them as soon as they arrive."""
        while rclpy.ok():
            ret, frame = self.cap.read()
            # print(frame)
            if ret:  # If a new frame is available
                msg = self.bridge.cv2_to_imgmsg(frame, encoding="bgr8")
                self.publisher_.publish(msg)
                self.get_logger().info("Published a video frame.")

    def destroy_node(self):
        """Cleanup on shutdown."""
        self.cap.release()
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    node = VideoPublisher()
    try:
        node.run_event_loop()  # Event-based loop runs instead of fixed timer
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()

