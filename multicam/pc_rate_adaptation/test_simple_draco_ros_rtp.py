import rclpy
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2
import numpy as np
import struct
import socket
import time
import random
from DracoPy import encode, decode

class PointCloudRtpSender(Node):
    def __init__(self):
        super().__init__('pointcloud_rtp_sender')

        # --- UDP/RTP setup ---
        self.dst_addr = ('127.0.0.1', 30000)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # RTP state
        self.sequence_number = 0
        self.timestamp = 0
        self.ssrc = random.getrandbits(32)
        self.max_payload = 1200  # bytes per RTP packet

        # ROS subscription
        self.subscription = self.create_subscription(
            PointCloud2,
            '/husky1/lidar_points',
            self.listener_callback,
            10)

    def listener_callback(self, msg: PointCloud2):
        # 1) unpack to Nx3 float32 array
        points = self.pointcloud2_to_xyz_array(msg)
        if points.size == 0:
            self.get_logger().warn('No points in incoming cloud.')
            return

        # 2) Draco compress
        min_vals = points.min(axis=0)
        max_vals = points.max(axis=0)
        max_range = float(np.max(max_vals - min_vals))
        compressed = encode(
            points=points,
            faces=None,
            quantization_bits=8,
            compression_level=1,
            quantization_range=max_range,
            quantization_origin=min_vals,
            create_metadata=True,
            preserve_order=True,
            colors=None,
            tex_coord=None,
            normals=None
        )
        self.get_logger().info(f'Compressed size: {len(compressed)} bytes')

        # 3) (optional) verify round-trip decode
        decoded = decode(compressed)
        decoded_points = np.array(decoded.points, dtype=np.float32)
        self.get_logger().info(f'Decoded back to {decoded_points.shape[0]} points')

        # 4) RTP-packetize+send
        self.send_rtp(compressed)

    def send_rtp(self, payload: bytes):
        """Split payload into chunks, prepend RTP headers, and send."""
        offset = 0
        while offset < len(payload):
            chunk = payload[offset:offset + self.max_payload]
            # RTP header: V=2,P=0,X=0,CC=0 => 0x80 ; M=0, PT=96 => 96
            rtp_header = struct.pack(
                '!BBHII',
                0x80,
                96,
                self.sequence_number & 0xFFFF,
                self.timestamp & 0xFFFFFFFF,
                self.ssrc
            )
            packet = rtp_header + chunk
            self.sock.sendto(packet, self.dst_addr)

            # advance RTP state
            self.sequence_number += 1
            offset += len(chunk)

        # you can choose a better timestamp scheme,
        # e.g. timestamp += frame_duration_in_samples
        self.timestamp += 3000  # arbitrary step per-frame

    def pointcloud2_to_xyz_array(self, cloud_msg):
        # very basic unpacker for xyz fields only
        fmt = 'fff'  # three float32
        offsets = {f.name: f.offset for f in cloud_msg.fields}
        step = cloud_msg.point_step
        buf = cloud_msg.data
        n_pts = len(buf) // step

        pts = np.zeros((n_pts, 3), dtype=np.float32)
        for i in range(n_pts):
            base = i * step
            x = struct.unpack_from('f', buf, base + offsets['x'])[0]
            y = struct.unpack_from('f', buf, base + offsets['y'])[0]
            z = struct.unpack_from('f', buf, base + offsets['z'])[0]
            pts[i] = (x, y, z)
        return pts

def main(args=None):
    rclpy.init(args=args)
    node = PointCloudRtpSender()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()

