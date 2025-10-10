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
    data = points.astype(np.float32).tobytes()
    return PointCloud2(
        header=header,
        height=1,
        width=points.shape[0],
        is_dense=True,
        is_bigendian=False,
        fields=fields,
        point_step=12,
        row_step=12 * points.shape[0],
        data=data,
    )


class RtpDracoToRos2(Node):
    def __init__(self):
        super().__init__('rtp_draco_to_ros2')

        # RTP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # a slightly bigger recv buffer helps when packets bunch up
        try:
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4 * 1024 * 1024)
        except Exception:
            pass
        self.sock.bind(('0.0.0.0', 30112))
        self.get_logger().info('Listening for RTP+Draco on port 30112')

        # Publisher
        self.pub = self.create_publisher(PointCloud2, '/decoded_pointcloud', 10)

        # RTP reassembly state
        self.last_timestamp = None
        self.last_seq = None
        self.frame_corrupt = False
        self.current_payload = bytearray()

        # Spin the socket in a timer callback
        self.create_timer(0.001, self._poll_socket)

    @staticmethod
    def _seq_inc(prev, cur) -> bool:
        """Return True if cur is the next 16-bit RTP sequence after prev."""
        return ((prev + 1) & 0xFFFF) == cur

    def _poll_socket(self):
        while True:
            try:
                data, addr = self.sock.recvfrom(65536)
            except BlockingIOError:
                break

            if len(data) < 12:
                return  # too small for RTP header

            # Parse RTP header
            b1, b2, seq, timestamp, ssrc = struct.unpack('!BBHII', data[:12])
            version = b1 >> 6
            if version != 2:
                return

            marker_bit = (b2 & 0x80) != 0  # M bit = high bit of second byte
            payload = data[12:]

            # New timestamp while previous frame in-progress but without M:
            if (self.last_timestamp is not None and
                timestamp != self.last_timestamp and
                not marker_bit and
                self.current_payload):
                # Fallback: flush what we had (best-effort)
                self.get_logger().warn('Timestamp changed without marker; flushing frame (network reordering/clock jump).')
                self._try_decode_and_publish()
                self._reset_reassembly()

            # If we are still on the same frame, check for sequence gaps
            if self.last_timestamp == timestamp and self.last_seq is not None:
                if not self._seq_inc(self.last_seq, seq):
                    # gap or reordering – mark corrupt and keep collecting until M
                    self.frame_corrupt = True

            # Append this payload
            self.current_payload.extend(payload)

            # End-of-frame signaled by marker bit
            if marker_bit:
                self._try_decode_and_publish()
                self._reset_reassembly()
            else:
                # Continue reassembly
                self.last_timestamp = timestamp
                self.last_seq = seq

    def _reset_reassembly(self):
        self.current_payload.clear()
        self.last_timestamp = None
        self.last_seq = None
        self.frame_corrupt = False

    def _try_decode_and_publish(self):
        if not self.current_payload:
            return
        if self.frame_corrupt:
            self.get_logger().warn('Dropping frame due to packet loss/reorder inside frame (sequence gap).')
            return
        try:
            decoded = decode(bytes(self.current_payload))
            pts = np.array(decoded.points, dtype=np.float32).reshape(-1, 3)
            msg = create_pointcloud2(pts, frame_id='lidar', stamp=self.get_clock().now().to_msg())
            self.pub.publish(msg)
            self.get_logger().info(f'Published PointCloud2 with {pts.shape[0]} points')
        except Exception as e:
            self.get_logger().error(f'Draco decode failed: {e}')

def main(args=None):
    rclpy.init(args=args)
    node = RtpDracoToRos2()
    node.sock.setblocking(False)
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
