#!/usr/bin/env python3
import os
import time
import csv

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2
from sensor_msgs_py import point_cloud2
import numpy as np
import struct

from DracoPy import encode, decode  # your Draco bindings

class PointCloudCompressor(Node):
    def __init__(self):
        super().__init__('pointcloud_compressor')

        # --- PARAMETERS ---
        # You can also declare/get these via self.declare_parameter + get_parameter
        self.quant_bits   = [8, 12, 16, 20, 24]
        self.comp_levels  = [0, 3, 6, 9]
        self.scan_rate_hz = 10.0  # for bits/sec calculation

        # CSV setup
        self.csv_path = os.path.join(
            os.path.expanduser('~'),
            'draco_bench.csv'
        )
        is_new = not os.path.exists(self.csv_path)
        self.csv_file = open(self.csv_path, 'a', newline='')
        self.csv_writer = csv.writer(self.csv_file)
        if is_new:
            self.csv_writer.writerow([
                'timestamp',
                'scan_id',
                'num_points',
                'quant_bits',
                'comp_level',
                'raw_size_bytes',
                'compressed_size_bytes',
                'encode_time_s',
                'bits_per_scan',
                'bits_per_second'
            ])

        # ROS subscriptions / publishers
        self.subscription = self.create_subscription(
            PointCloud2,
            '/husky1/lidar_points',
            self.listener_callback,
            10
        )
        self.decoded_publisher = self.create_publisher(
            PointCloud2,
            '/husky1/lidar_points_decoded',
            10
        )

        self.scan_counter = 0

    def listener_callback(self, msg: PointCloud2):
        self.scan_counter += 1

        # 1) unpack to Nx3 float32 array
        points = self.pointcloud2_to_xyz_array(msg)
        n_pts = points.shape[0]
        if n_pts == 0:
            self.get_logger().warn('No points in incoming cloud.')
            return

        raw_bytes = points.nbytes
        mins = points.min(axis=0)
        maxs = points.max(axis=0)
        max_range = float(np.max(maxs - mins))
        origin = mins.tolist()

        # 2) loop over all compression settings
        for q_bits in self.quant_bits:
            for c_lvl in self.comp_levels:
                # time & compress
                t0 = time.time()
                comp = encode(
                    points=points,
                    faces=None,
                    quantization_bits=q_bits,
                    compression_level=c_lvl,
                    quantization_range=max_range,
                    quantization_origin=origin,
                    create_metadata=True,
                    preserve_order=True,
                    colors=None,
                    tex_coord=None,
                    normals=None
                )
                duration = time.time() - t0
                comp_bytes = len(comp)

                bits_scan = comp_bytes * 8
                bits_sec  = bits_scan * self.scan_rate_hz

                # log to console
                self.get_logger().info(
                    f"[scan {self.scan_counter:04d}] "
                    f"q={q_bits} lvl={c_lvl} → "
                    f"{comp_bytes} B, {duration:.3f} s, "
                    f"{bits_sec:.1f} b/s"
                )

                # append to CSV
                self.csv_writer.writerow([
                    time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()),
                    self.scan_counter,
                    n_pts,
                    q_bits,
                    c_lvl,
                    raw_bytes,
                    comp_bytes,
                    f"{duration:.6f}",
                    bits_scan,
                    bits_sec
                ])
                # ensure it’s written immediately
                self.csv_file.flush()

        # ===== decode & republish (optional) =====
        decoded = decode(comp)
        decoded_pts = np.array(decoded.points, dtype=np.float32)
        header = msg.header
        decoded_msg = point_cloud2.create_cloud_xyz32(
            header,
            decoded_pts.tolist()
        )
        self.decoded_publisher.publish(decoded_msg)

    def pointcloud2_to_xyz_array(self, cloud_msg):
        """Extract XYZ floats into an (N,3) numpy array."""
        offsets = {f.name: f.offset for f in cloud_msg.fields}
        step    = cloud_msg.point_step
        data    = cloud_msg.data

        pts = []
        for i in range(0, len(data), step):
            x = struct.unpack_from('f', data, i + offsets['x'])[0]
            y = struct.unpack_from('f', data, i + offsets['y'])[0]
            z = struct.unpack_from('f', data, i + offsets['z'])[0]
            pts.append([x, y, z])
        return np.array(pts, dtype=np.float32)

    def destroy_node(self):
        # close CSV on shutdown
        self.csv_file.close()
        return super().destroy_node()

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

