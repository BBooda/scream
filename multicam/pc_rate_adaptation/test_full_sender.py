#!/usr/bin/env python3
import os
import joblib
import numpy as np
import struct
import time
import socket
import random
import math

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32
from sensor_msgs.msg import PointCloud2
from sensor_msgs_py import point_cloud2
from DracoPy import encode, decode

class AdaptivePointCloudRtpSender(Node):
    def __init__(self):
        super().__init__('adaptive_pointcloud_rtp_sender')

        # ------------------ Model / adaptation setup ------------------
        self.get_logger().info("Starting adaptive Draco + RTP sender…")

        # 1) Load your trained poly + linear model
        # Update this path if needed
        model_path = '/home/eamrgde/Documents/gitrepos/ros_scream_int/scream/multicam/pc_rate_adaptation/train/draco_model_v1.pkl'
        try:
            self.poly, self.lr = joblib.load(model_path)
            self.get_logger().info(f"Loaded model from: {model_path}")
        except Exception as e:
            self.get_logger().error(f"Failed to load model: {e}")
            raise

        # 2) Grid as used in training (same as your first script)
        self._quant_bits_list  = np.array([8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24])
        self._comp_levels_list = np.array([0,1,2,3,4,5,6,7,8,9])

        self._grid = np.array([[q, c]
                               for q in self._quant_bits_list
                               for c in self._comp_levels_list])  # (20,2)

        # 3) Pre-predict bps for the grid (mirrors your first script)
        fake_n = 32185
        grid3 = np.hstack([self._grid, np.full((len(self._grid), 1), fake_n)])
        Xg = self.poly.transform(grid3)
        self._pred_bps = self.lr.predict(Xg)  # shape=(20,)

        # Default target (until /desired_bps arrives)
        self.desired_bps = float(np.mean(self._pred_bps))

        # Current chosen params
        self.quant_bits = int(self._grid[0, 0])
        self.comp_level = int(self._grid[0, 1])

        # ------------------ RTP / UDP setup ------------------
        self.dst_addr = ('127.0.0.1', 30000)   # change if needed
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        self.sequence_number = 0
        self.timestamp = 0
        self.ssrc = random.getrandbits(32)
        self.max_payload = 1200  # bytes per RTP packet

        # ------------------ ROS I/O ------------------
        # Desired bitrate subscriber
        self.create_subscription(Float32, '/desired_bps', self._on_desired_bps, 10)

        # PointCloud2 subscriber (from your second script)
        self.create_subscription(PointCloud2, '/husky1/ouster/points', self._on_pointcloud, 10)

        # Optional decoded point cloud publisher for visualization/debug
        self.decoded_pub = self.create_publisher(PointCloud2, '/husky1/lidar_points_decoded', 10)

        self.get_logger().info("Ready. Waiting for /husky1/lidar_points and /desired_bps…")

        # in __init__
        self.rtp_clock   = 90000
        self.frame_rate  = 10.0
        self.frame_period = 1.0 / self.frame_rate    # 0.1 s
        self.timestamp_step = int(self.rtp_clock / self.frame_rate)  # 9000
        self.pacing_safety = 0.9   # spread packets across ~90% of the frame

    # ------------------ ROS callbacks ------------------
    def _on_desired_bps(self, msg: Float32):
        self.desired_bps = float(msg.data)

        # Pick the (q,c) whose predicted bps is closest to desired
        idx = np.abs(self._pred_bps - self.desired_bps).argmin()
        q, c = self._grid[idx]
        self.quant_bits = int(q)
        self.comp_level = int(c)

        self.get_logger().info(
            f"New desired_bps={self.desired_bps:.0f} → q={self.quant_bits}, level={self.comp_level}"
        )

    def _on_pointcloud(self, msg: PointCloud2):
        # Unpack to Nx3 float32
        points = self._pointcloud2_to_xyz(msg)
        if points.size == 0:
            self.get_logger().warn('No points in incoming cloud.')
            return

        # (Optional) filter: keep x>0 like in your first script
        # points = points[points[:, 0] > 0] if points.size else points
        if points.size == 0:
            self.get_logger().warn('All points filtered out (x<=0).')
            return

        # Quantization config (range & origin)
        mins = points.min(axis=0)
        maxs = points.max(axis=0)
        q_range = float((maxs - mins).max())
        q_origin = mins.tolist()

        # Draco encode using current q & c
        t0 = time.time()
        compressed = encode(
            points=points,
            faces=None,
            quantization_bits=self.quant_bits,
            compression_level=self.comp_level,
            quantization_range=q_range,
            quantization_origin=q_origin,
            create_metadata=True,
            preserve_order=True,
            colors=None,
            tex_coord=None,
            normals=None
        )
        enc_ms = (time.time() - t0) * 1e3

        self.get_logger().info(
            # f"Compressed {points.shape[0]} pts → {len(compressed)} B in {enc_ms:.1f} ms "
            f"Compressed {points.shape[0]} pts → {len(compressed)*8*10*10**(-6)} Mbps in {enc_ms:.1f} ms "
            f"(q={self.quant_bits}, lvl={self.comp_level})"
        )

        # # Optional: decode & publish for visual/debug
        # try:
        #     decoded = decode(compressed)
        #     dpts = np.array(decoded.points, dtype=np.float32)
        #     out = point_cloud2.create_cloud_xyz32(msg.header, dpts.tolist())
        #     self.decoded_pub.publish(out)
        # except Exception as e:
        #     self.get_logger().warn(f"Decode/republish failed: {e}")

        # RTP send
        self._send_rtp(compressed)

    # ------------------ RTP helpers ------------------
    def _send_rtp(self, payload: bytes):
        bytes_per_sec = max(1.0, self.desired_bps / 8.0)  # bps → B/s
        offset = 0
        while offset < len(payload):
            chunk = payload[offset : offset + self.max_payload]
            offset += len(chunk)
            is_last = (offset >= len(payload))

            b1 = 0x80
            b2 = (0x80 if is_last else 0x00) | 96
            hdr = struct.pack('!BBHII', b1, b2,
                              self.sequence_number & 0xFFFF,
                              self.timestamp & 0xFFFFFFFF,
                              self.ssrc)
            t0 = time.perf_counter()
            self.sock.sendto(hdr + chunk, self.dst_addr)
            self.sequence_number = (self.sequence_number + 1) & 0xFFFF

            # pacing based on bitrate target
            send_budget = len(chunk) / bytes_per_sec  # seconds
            elapsed = time.perf_counter() - t0
            if send_budget > elapsed:
                time.sleep(send_budget - elapsed)

        self.timestamp = (self.timestamp + self.timestamp_step) & 0xFFFFFFFF

    # ------------------ Utility ------------------
    def _pointcloud2_to_xyz(self, cloud_msg: PointCloud2) -> np.ndarray:
        offsets = {f.name: f.offset for f in cloud_msg.fields}
        step = cloud_msg.point_step
        data = cloud_msg.data
        n_pts = len(data) // step
        if n_pts == 0:
            return np.empty((0, 3), dtype=np.float32)

        pts = np.zeros((n_pts, 3), dtype=np.float32)
        for i in range(n_pts):
            base = i * step
            x = struct.unpack_from('f', data, base + offsets['x'])[0]
            y = struct.unpack_from('f', data, base + offsets['y'])[0]
            z = struct.unpack_from('f', data, base + offsets['z'])[0]

            if np.isnan(x) or np.isnan(y) or np.isnan(z):
                continue
            pts[i] = (x, y, z)
        return pts

def main(args=None):
    rclpy.init(args=args)
    node = AdaptivePointCloudRtpSender()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()

