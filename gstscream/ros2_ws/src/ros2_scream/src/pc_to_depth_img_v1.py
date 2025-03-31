from numpy import uint8
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
        self.publisher_test = self.create_publisher(Image, '/test_depth_image_topic', 10)
        self.bridge = CvBridge()

        # stacking settings
        self.stack_settings = {
            's_width': 1024,
            's_height': 32,
            'number_r': 2
        }

    def pointcloud_callback(self, msg):
        # self.get_logger().info(msg)
        points = []
        for p in pc2.read_points(msg, field_names=("x", "y", "z"), skip_nans=True):
            points.append([p[0], p[1], p[2]])
        points = np.array(points, dtype=np.float32)
        
        
        # self.get_logger().info(points)
        # print(points)

        depth_image = range_projection(points, proj_W=2048, proj_H=32)
        # self.get_logger().info(depth_image)
        
        print("Shape without NaN: " + str(depth_image[~np.isnan(depth_image)].shape))

        print("max: " + str(np.max(depth_image[~np.isnan(depth_image)])) + " min: " + str(np.min(depth_image[~np.isnan(depth_image)])))

        
        # here we need to normalize the image. 
        # then it is encoded in uint8
        max_lidar_depth = 25
        depth_image = ((depth_image / max_lidar_depth) * 255).astype(np.uint8)  # Normalize
        
        # here we can stack them to fit 720x1280, then we can unstack them on the receiver.
        # we need this to be compatible with the current scream implementation
       
        # # ---------------------------------------------------------------
        # print("Shape: " + str(depth_image.shape))
        #
        # temp_a = np.concatenate((np.zeros((32,128), dtype=uint8), depth_image[:, 0:1024], np.zeros((32,128), dtype=uint8)), axis=1)
        # temp_b = np.concatenate((np.zeros((32,128), dtype=uint8), depth_image[:, 1024:2048], np.zeros((32,128), dtype=uint8)), axis=1)
        # temp_c = np.zeros((656, 1280), dtype=uint8)
        #
        # self.get_logger().info("temp_a" + str(temp_a.shape))
        # self.get_logger().info("temp_b" + str(temp_b.shape))
        # self.get_logger().info("temp_c" + str(temp_c.shape))
        #
        # # create a vertical 720x1280 image from the wide range image
        # depth_image_vertical = np.vstack((temp_a, temp_b, temp_c))

        # ---------------------------------------------------------------

        depth_image_vertical = self.stack_image(depth_image, self.stack_settings)

        channel_2_3 = np.zeros((720, 1280), dtype=uint8)
        # channel_2_3 = depth_image_vertical 

        rgb = np.stack((depth_image_vertical, channel_2_3, channel_2_3), axis=-1)

        self.get_logger().info("rgb test" + str(rgb.shape))

        # depth_msg = self.bridge.cv2_to_imgmsg(depth_image_vertical, encoding="mono8")
        depth_msg = self.bridge.cv2_to_imgmsg(rgb)
        # depth_msg = self.bridge.cv2_to_imgmsg(depth_image_vertical)


        # publish 64x2080 for testing
        # depth_image_vertical = self.encoding_test(depth_image_vertical, 99)
        # depth_image_vertical = np.reshape(depth_image_vertical, (720, 1280))
        # self.get_logger().info("Encoded shape: " + str(depth_image_vertical.shape))
        gray_scale_msg = self.bridge.cv2_to_imgmsg(depth_image_vertical, encoding="mono8")
        gray_scale_msg.header = msg.header
        self.publisher_test.publish(gray_scale_msg)
        
        # publish the image to be transmitted
        self.publisher.publish(depth_msg)

    def stack_image(self, wide_image, stack_settings):
        '''
        We need to stack the wide range image into 1024 x some height
        Width stacking is static. We are stacking and zero padding 1024 slices

        stack_shape := dictionary with the following values
        stack_shape['s_width'] := width of slice  
        stack_shape['s_height'] := height of slice 
        stack_shape['number_r'] := number of image row slices
        '''
        self.get_logger().info("Long image shape: " + str(wide_image.shape))
        
        image_slices = dict()
        for i in range(stack_settings['number_r']):
            image_slices[i] = np.concatenate(
                                (np.zeros((stack_settings['s_height'],128), dtype=uint8), 
                                wide_image[:, i*stack_settings['s_width']:(i+1)*stack_settings['s_width']], 
                                np.zeros((stack_settings['s_height'],128), dtype=uint8))
                                , axis=1)

            self.get_logger().info(f"Row slice {i}, shape: {image_slices[i].shape}")

        # apply vertical and horizontal padding for the empty space
        height = 720 - (stack_settings['s_height'] * stack_settings['number_r'])
        image_slices[i+1] = np.zeros((height, 1280), dtype=uint8) 
        self.get_logger().info(f"Row slice {i+1}, shape: {image_slices[i+1].shape}")

        # stack the images slices here
        depth_image_vertical = None
        for i in image_slices:
            if i != 0:
                depth_image_vertical = np.vstack((depth_image_vertical, image_slices[i]))
            else:
                depth_image_vertical = image_slices[i]

            # self.get_logger().info(f"Dict idx {i}, shape: {image_slices[i].shape}")
            # self.get_logger().info(f"Vertical shape: {depth_image_vertical.shape}")
        return depth_image_vertical
        # depth_image_vertical = np.vstack((temp_a, temp_b, temp_c))

        # temp_a = np.concatenate((np.zeros((32,128), dtype=uint8), 
        #                          wide_image[:, 0:1024], np.zeros((32,128), dtype=uint8)), axis=1)
        #
        # temp_b = np.concatenate((np.zeros((32,128), dtype=uint8), 
        #                          wide_image[:, 1024:2048], np.zeros((32,128), dtype=uint8)), axis=1)
        # temp_c = np.zeros((656, 1280), dtype=uint8)
        #
        # self.get_logger().info("temp_a" + str(temp_a.shape))
        # self.get_logger().info("temp_b" + str(temp_b.shape))
        # self.get_logger().info("temp_c" + str(temp_c.shape))

        # create a vertical 720x1280 image from the wide range image

    def encoding_test(self, image, quality=90):
        '''
        This is a simple encoding test
        '''
        # Encode in memory as JPEG
        # self.get_logger().info("Shape before compression: " + str(image.shape))
        self.get_logger().info("Bytes before compression: " + str(len(image.tobytes())))
        success, encoded_image = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, quality])
        decoded_img = cv2.imdecode(encoded_image, cv2.IMREAD_GRAYSCALE)
        self.get_logger().info("Bytes after compression: " + str(len(encoded_image.tobytes())) + f" Compression state: {success}")

        if success:
            return decoded_img
        else:
            self.get_logger().info("Endoding of grayscale image failed!")
            return -1

def main(args=None):
    rclpy.init(args=args)
    node = PointCloudToDepthImage()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
