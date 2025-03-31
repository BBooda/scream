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
            'image_compressed_decoded',  # Replace with your actual topic
            self.depth_image_callback,
            10)
        self.publisher = self.create_publisher(PointCloud2, '/pointcloud_reconstructed', 10)
        self.bridge = CvBridge()


        # stacking settings
        self.stack_settings = {
            's_width': 1024,
            's_height': 32,
            'number_r': 2
        }

    def depth_image_callback(self, msg):
        # depth_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='mono8')
        depth_image = self.bridge.imgmsg_to_cv2(msg)
        self.get_logger().info("Received frame shape: " + str(depth_image.shape))
        
        # for 3 channel images
        # depth_image = depth_image[0:32,128:1152,0]

        # depth_image = cv2.cvtColor(depth_image, cv2.COLOR_RGB2GRAY) 

        # incase of grayscale
        # depth_image = depth_image[0:32,128:1152]


        # return back to 2048x32
        depth_image = self.reverse_stacking(depth_image[:,:,0], self.stack_settings)

        self.get_logger().info("Unstacked frame shape: " + str(depth_image.shape))



        depth_image = depth_image.astype(np.float32) / 255.0  # Normalize
        depth_image *= 25.0  # Scale depth values appropriately
        
        point_cloud = undo_projection(depth_image, proj_W=2048, proj_H=32)
        header = Header()
        header.stamp = self.get_clock().now().to_msg()
        header.frame_id = "hesai_lidar"
        
        cloud_msg = pc2.create_cloud_xyz32(header, point_cloud)
        self.publisher.publish(cloud_msg)


    def reverse_stacking(self, stacked_image, stack_shape):
        '''
        stack_shape := dictionary with the following values
        stack_shape['s_width'] := width of slice  
        stack_shape['s_height'] := height of slice 
        stack_shape['number_r'] := number of image row slices
        '''
        # make this dynamic
        # Extract the first 64 rows (temp_a) and next 64 rows (temp_b)
        image_slices = dict()
        row_start = 0
        for i in range(stack_shape['number_r']):
            image_slices[i] = stacked_image[row_start:row_start + stack_shape['s_height'], 128:1152]
            row_start += stack_shape['s_height'] 
            # second_row = stacked_image[32:64, 128:1152]
        
        count = 0
        restored_image = None
        for row in image_slices:
            count += 1
            self.get_logger().info(f"Row {count} shape {image_slices[row].shape}")
            if count != 1:
                restored_image = np.concatenate((restored_image, image_slices[row]), axis=1)
            else:
                restored_image = image_slices[row]

        # self.get_logger().info(f"Second row shape {second_row.shape}")

        # restored_image = np.concatenate((first_row, second_row), axis=1)
        return restored_image

def main(args=None):
    rclpy.init(args=args)
    node = DepthImageToPointCloud()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()

