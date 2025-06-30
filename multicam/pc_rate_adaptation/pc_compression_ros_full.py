import rclpy
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2
from sensor_msgs_py import point_cloud2
import numpy as np
import struct
from DracoPy import encode, decode

class PointCloudCompressor(Node):
    def __init__(self):
        super().__init__('pointcloud_compressor')
        # Subscriber: raw LIDAR points
        self.subscription = self.create_subscription(
            PointCloud2,
            '/husky1/lidar_points',
            # self.callback_testing,
            self.listener_callback,
            10)

        # Publisher: decoded LIDAR points
        self.decoded_publisher = self.create_publisher(
            PointCloud2,
            '/husky1/lidar_points_decoded',
            10)

    def callback_testing(self, msg: PointCloud2):

        # Convert incoming PointCloud2 to Nx3 numpy array
        # points = self.pointcloud2_to_xyz_array(msg)
        names = [f.name for f in msg.fields]
        write_fields = [n for n in names if n in ('x', 'y', 'z')]
        print(write_fields)
        # points = list(point_cloud2.read_points(msg, field_names=write_fields, skip_nans=True)) 
        # points = list(point_cloud2.read_points(msg, field_names=['x', 'y', 'z'], skip_nans=True)) 
        # points = np.array(points)

        pts = [ (p[0], p[1], p[2]) 
        for p in point_cloud2.read_points(msg,
                                          field_names=['x','y','z'],
                                          skip_nans=True) ]
        points = np.array(pts, dtype=np.float32)
        if points.size == 0:
            self.get_logger().warn('No points received.')
            return

        # print(f"Shape before compression: {points.shape}")
        # # Determine quantization parameters
        # # min_vals = points.min(axis=0)
        # # max_vals = points.max(axis=0)
        # # max_range = float(np.max(max_vals - min_vals))
        # max_range = 100.0
        # min_vals = None
        # # min_vals = 1.
        #
        # # ----- ENCODE -----
        # compressed = encode(
        #     points=points,
        #     faces=None,
        #     quantization_bits=10, # [1 - 30]
        #     compression_level=1, # [1, 10]
        #     quantization_range=max_range,
        #     quantization_origin=min_vals,
        #     create_metadata=True,
        #     preserve_order=True,
        #     colors=None,
        #     tex_coord=None,
        #     normals=None
        # )
        # self.get_logger().info(f'Compressed size: {len(compressed)} bytes')
        #
        # # ----- DECODE -----
        # decoded = decode(compressed)
        decoded_points = np.array(points, dtype=np.float32)
        self.get_logger().info(f'Decoded points shape: {decoded_points.shape}')

        # ----- PUBLISH DECODED -----
        # Reuse original header (with timestamp/frame_id)
        header = msg.header
        # Create a PointCloud2 message from decoded points
        decoded_msg = point_cloud2.create_cloud_xyz32(
            header,
            decoded_points.tolist()
        )
        self.decoded_publisher.publish(decoded_msg)
        self.get_logger().info('Published decoded point cloud.')

    def listener_callback(self, msg: PointCloud2):
        # 1) unpack to Nx3 float32 array
        points = self.pointcloud2_to_xyz_array(msg)
        if points.size == 0:
            self.get_logger().warn('No points in incoming cloud.')
            return
        
        # points = points[points[:,0] > 0]
        # 2) Draco compress
        min_vals = points.min(axis=0)
        max_vals = points.max(axis=0)
        max_range = float(np.max(max_vals - min_vals))

        # max_range = [50., 50., 50.] 
        # min_vals = [0., 0., 0.]
        # min_vals = None 

        self.get_logger().info(f"max_range: {max_range}")
        self.get_logger().info(f"min_values: {min_vals}")

        compressed = encode(
            points=points,
            faces=None,
            quantization_bits= 7,
            compression_level=9,
            quantization_range=max_range,
            quantization_origin=min_vals,
            create_metadata=True,
            preserve_order=True,
            colors=None,
            tex_coord=None,
            normals=None
        )
        self.get_logger().info(f'Compressed size: {len(compressed)} bytes')

        # ----- DECODE -----
        decoded = decode(compressed)
        decoded_points = np.array(decoded.points, dtype=np.float32)
        self.get_logger().info(f'Decoded points shape: {decoded_points.shape}')

        # ----- PUBLISH DECODED -----
        # Reuse original header (with timestamp/frame_id)
        header = msg.header
        # Create a PointCloud2 message from decoded points
        decoded_msg = point_cloud2.create_cloud_xyz32(
            header,
            decoded_points.tolist()
        )
        self.decoded_publisher.publish(decoded_msg)
        self.get_logger().info('Published decoded point cloud.')

    def pointcloud2_to_xyz_array(self, cloud_msg):
        """Extract XYZ floats from a PointCloud2 into an (N,3) numpy array."""
        # Compute field offsets
        offset = {f.name: f.offset for f in cloud_msg.fields}
        point_step = cloud_msg.point_step
        data = cloud_msg.data

        pts = []
        for i in range(0, len(data), point_step):
            x = struct.unpack_from('f', data, i + offset['x'])[0]
            y = struct.unpack_from('f', data, i + offset['y'])[0]
            z = struct.unpack_from('f', data, i + offset['z'])[0]
            pts.append([x, y, z])
        return np.array(pts, dtype=np.float32)

def main(args=None):
    rclpy.init(args=args)
    node = PointCloudCompressor()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()

