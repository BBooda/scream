from numpy.core.memmap import uint8
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2, Image
import numpy as np
import cv2
import struct
import sensor_msgs_py.point_cloud2 as pc2
from cv_bridge import CvBridge

from point_to_image import range_projection  # Ensure this function is accessible

class PointCloudToDepthImage(Node):
    def __init__(self):
        super().__init__('pointcloud_to_depthimage')
        self.subscription = self.create_subscription(
            PointCloud2,
            '/husky1/ouster/points',  # Replace with your actual topic
            self.pointcloud_callback,
            10)
        self.publisher = self.create_publisher(Image, '/depth_image_topic', 10)
        self.publisher_test = self.create_publisher(Image, '/long_image', 10)
        self.bridge = CvBridge()

    def pointcloud_callback(self, msg):
        # self.get_logger().info(msg)
        points = []
        for p in pc2.read_points(msg, field_names=("x", "y", "z"), skip_nans=True):
            points.append([p[0], p[1], p[2]])
        points = np.array(points, dtype=np.float32)
        
        
        # self.get_logger().info(points)
        # print(points)

        depth_image = range_projection(points)
        # self.get_logger().info(depth_image)
        
        print("Shape without NaN: " + str(depth_image[~np.isnan(depth_image)].shape))

        print("max: " + str(np.max(depth_image[~np.isnan(depth_image)])) + " min: " + str(np.min(depth_image[~np.isnan(depth_image)])))
        # depth_image = (depth_image / np.max(depth_image[~np.isnan(depth_image)]) * 255).astype(np.uint8)  # Normalize
        depth_image = ((depth_image / 100) * 255).astype(np.uint8)  # Normalize
        
        # here we can stack them to fit 720x1280, then we can unstack them on the receiver.
        # we need this to be compatible with the current scream implementation
        
        print("Shape: " + str(depth_image.shape))

        print(np.zeros((64,178)).shape)
        print(depth_image[:, 0:1024].shape)
        
        temp_a = np.concatenate((np.zeros((64,128), dtype=uint8), depth_image[:, 0:1024], np.zeros((64,128), dtype=uint8)), axis=1)
        temp_b = np.concatenate((np.zeros((64,128), dtype=uint8), depth_image[:, 1024:2048], np.zeros((64,128), dtype=uint8)), axis=1)
        temp_c = np.zeros((592, 1280), dtype=uint8)

        self.get_logger().info("temp_a" + str(temp_a.shape))
        self.get_logger().info("temp_b" + str(temp_b.shape))
        depth_image_vertical = np.vstack((temp_a,temp_b, temp_c))

        # channel_2_3 = np.zeros((720, 1280), dtype=uint8)
        channel_2_3 = depth_image_vertical 

        rgb = np.stack((depth_image_vertical, channel_2_3, channel_2_3), axis=-1)

        self.get_logger().info("rgb test" + str(rgb.shape))

        # depth_msg = self.bridge.cv2_to_imgmsg(depth_image_vertical, encoding="mono8")
        depth_msg = self.bridge.cv2_to_imgmsg(rgb)


        # publish 64x2080 for testing
        self.publisher_test.publish(self.bridge.cv2_to_imgmsg(depth_image))

        self.publisher.publish(depth_msg)


def main(args=None):
    rclpy.init(args=args)
    node = PointCloudToDepthImage()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
