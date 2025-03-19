import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, PointCloud2, PointField
import numpy as np
import cv2
import sensor_msgs_py.point_cloud2 as pc2
from cv_bridge import CvBridge
from std_msgs.msg import Header

from point_to_image import undo_projection  # Ensure this function is accessible

class DepthImageToPointCloud(Node):
    def __init__(self):
        super().__init__('depthimage_to_pointcloud')
        self.subscription = self.create_subscription(
            Image,
            '/received_frames',  # Replace with your actual topic
            self.depth_image_callback,
            10)
        self.publisher = self.create_publisher(PointCloud2, '/pointcloud_reconstructed', 10)
        self.bridge = CvBridge()

    def depth_image_callback(self, msg):
        depth_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='mono8')
        depth_image = depth_image.astype(np.float32) / 255.0  # Normalize
        depth_image *= 100.0  # Scale depth values appropriately
        
        point_cloud = undo_projection(depth_image)
        header = Header()
        header.stamp = self.get_clock().now().to_msg()
        header.frame_id = "hesai_lidar"
        
        cloud_msg = pc2.create_cloud_xyz32(header, point_cloud)
        self.publisher.publish(cloud_msg)


def main(args=None):
    rclpy.init(args=args)
    node = DepthImageToPointCloud()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()

