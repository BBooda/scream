import rclpy
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2
import numpy as np
import struct
from DracoPy import encode, decode

class PointCloudCompressor(Node):
    def __init__(self):
        super().__init__('pointcloud_compressor')
        self.subscription = self.create_subscription(
            PointCloud2,
            '/husky1/lidar_points',  # Replace with your topic
            self.listener_callback,
            10)

    def listener_callback(self, msg: PointCloud2):
        # Convert PointCloud2 to numpy array of XYZ
        points = self.pointcloud2_to_xyz_array(msg)
        if points.size == 0:
            self.get_logger().warn('No points received.')
            return

        # Define quantization range as the largest axis span
        min_vals = points.min(axis=0)
        max_vals = points.max(axis=0)
        max_range = float(np.max(max_vals - min_vals))

        # Compress
        compressed = encode(points=points,
                            faces=None,
                            quantization_bits=8,
                            compression_level=1,
                            quantization_range=max_range,
                            quantization_origin=min_vals,
                            create_metadata=True,
                            preserve_order=True,
                            colors=None,
                            tex_coord=None,
                            normals=None)
        
        self.get_logger().info(f'Compressed size: {len(compressed)} bytes')

        # Optionally decode and verify
        decoded = decode(compressed)
        decoded_points = np.array(decoded.points, dtype=np.float32)
        self.get_logger().info(f'Decoded points shape: {decoded_points.shape}')

    def pointcloud2_to_xyz_array(self, cloud_msg):
        dtype_list = [('x', np.float32), ('y', np.float32), ('z', np.float32)]
        points = []

        offset = {f.name: f.offset for f in cloud_msg.fields}
        point_step = cloud_msg.point_step
        row_step = cloud_msg.row_step

        for i in range(0, len(cloud_msg.data), point_step):
            x = struct.unpack_from('f', cloud_msg.data, i + offset['x'])[0]
            y = struct.unpack_from('f', cloud_msg.data, i + offset['y'])[0]
            z = struct.unpack_from('f', cloud_msg.data, i + offset['z'])[0]
            points.append([x, y, z])

        return np.array(points, dtype=np.float32)

def main(args=None):
    rclpy.init(args=args)
    compressor = PointCloudCompressor()
    rclpy.spin(compressor)
    compressor.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()

