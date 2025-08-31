#!/usr/bin/env python3
import socket
import struct

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32

PORT = 30001
BUF_SIZE = 1024

class BitrateNode(Node):
    def __init__(self):
        super().__init__('bitrate_listener')
        self.publisher_ = self.create_publisher(Float32, 'desired_bps', 10)

        # Setup UDP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('0.0.0.0', PORT))
        self.sock.setblocking(False)  # non-blocking so ROS2 spin works
        self.get_logger().info(f"Listening for uint32 bitrates on UDP port {PORT}…")

        # Timer to poll the socket
        self.timer = self.create_timer(0.01, self.poll_socket)

    def poll_socket(self):
        try:
            data, addr = self.sock.recvfrom(BUF_SIZE)
        except BlockingIOError:
            return  # nothing to read

        if len(data) < 4:
            self.get_logger().warn(f"Ignoring short packet ({len(data)} bytes) from {addr}")
            return

        # 1) Unpack big-endian uint32
        (rate_raw,) = struct.unpack('!I', data[:4])

        # 2) Keep same calculation (raw = bitrate in bps)
        rate = rate_raw

        # Publish as UInt32
        msg = Float32()
        msg.data = float(rate) 
        self.publisher_.publish(msg)

        self.get_logger().info(f"[{addr}] raw=0x{rate_raw:08X} rate={rate/1_000_000:.2f} Mbps")

def main(args=None):
    rclpy.init(args=args)
    node = BitrateNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()

