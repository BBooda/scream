#!/usr/bin/env python3
import socket
import struct
import numpy as np

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2, PointField
from std_msgs.msg import Header

from DracoPy import decode

# Helper to build PointCloud2 from Nx3 float32 array
def create_pointcloud2(points: np.ndarray, frame_id: str = 'map', stamp=None) -> PointCloud2:
    header = Header()
    header.frame_id = frame_id
    if stamp is not None:
        header.stamp = stamp

    fields = [
        PointField(name='x', offset=0,  datatype=PointField.FLOAT32, count=1),
        PointField(name='y', offset=4,  datatype=PointField.FLOAT32, count=1),
        PointField(name='z', offset=8,  datatype=PointField.FLOAT32, count=1),
    ]
    # pack xyz into a bytes object
    data = points.astype(np.float32).tobytes()
    return PointCloud2(
        header=header,
        height=1,
        width=points.shape[0],
        is_dense=True,
        is_bigendian=False,
        fields=fields,
        point_step=12,           # 3 * 4 bytes
        row_step=12 * points.shape[0],
        data=data,
    )


class RtpDracoToRos2(Node):
    def __init__(self):
        super().__init__('rtp_draco_to_ros2')

        # RTP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('0.0.0.0', 30112))
        self.get_logger().info('Listening for RTP+Draco on port 30112')

        # Publisher
        self.pub = self.create_publisher(PointCloud2, '/decoded_pointcloud', 10)

        # RTP reassembly state
        self.last_timestamp = None
        self.current_payload = bytearray()

        # Spin the socket in a timer callback
        self.create_timer(0.001, self._poll_socket)

    def _poll_socket(self):
        try:
            data, addr = self.sock.recvfrom(65536)
        except BlockingIOError:
            return

        if len(data) < 12:
            return  # too small

        # parse RTP header
        b1, b2, seq, timestamp, ssrc = struct.unpack('!BBHII', data[:12])
        version    = b1 >> 6
        if version != 2:
            return
        marker_bit = (b2 & 0x80) != 0

        payload = data[12:]

        # if timestamp changed without marker, flush previous frame
        if self.last_timestamp is not None and timestamp != self.last_timestamp and not marker_bit:
            self._decode_and_publish(self.current_payload)
            self.current_payload.clear()

        self.current_payload.extend(payload)

        if marker_bit:
            self._decode_and_publish(self.current_payload)
            self.current_payload.clear()

        self.last_timestamp = timestamp

    def _decode_and_publish(self, compressed_bytes: bytearray):
        if not compressed_bytes:
            return
        try:
            decoded = decode(bytes(compressed_bytes))
            pts = np.array(decoded.points, dtype=np.float32).reshape(-1, 3)
            msg = create_pointcloud2(pts, frame_id='lidar', stamp=self.get_clock().now().to_msg())
            self.pub.publish(msg)
            self.get_logger().info(f'Published PointCloud2 with {pts.shape[0]} points')
        except Exception as e:
            self.get_logger().error(f'Draco decode failed: {e}')

def main(args=None):
    rclpy.init(args=args)
    node = RtpDracoToRos2()
    # Set socket non-blocking so timer can poll it
    node.sock.setblocking(False)
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
