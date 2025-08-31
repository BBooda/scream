#!/usr/bin/env python3
import os
import joblib
import numpy as np
import struct
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32
from sensor_msgs.msg import PointCloud2
from sensor_msgs_py import point_cloud2
from DracoPy import encode, decode

class AdaptivePointCloudCompressor(Node):
    def __init__(self):
        super().__init__('adaptive_pc_compressor')

        # ---- 1) Load your trained poly+model ----
        # model_path = os.path.join(
        #     os.path.expanduser('~'),
        #     '/home/eamrgde/Documents/gitrepos/pc_rate_adaptation/ros2_ws/src/pc_rate_adaptation/pc_rate_adaptation/train/draco_model.pkl'
        # )
        self.get_logger().info("draco node started!...")
        model_path = '/home/eamrgde/Documents/gitrepos/pc_rate_adaptation/ros2_ws/src/pc_rate_adaptation/pc_rate_adaptation/train/draco_model.pkl'
        self.poly, self.lr = joblib.load(model_path)

        # these define the sweep you used in training
        self._quant_bits_list  = np.array([8, 12, 16, 20, 24])
        self._comp_levels_list = np.array([0,  3,   6,   9])

        # Pre-build the grid of (q,c)
        self._grid = np.array([
            [q, c]
            for q in self._quant_bits_list
            for c in self._comp_levels_list
        ])  # shape=(20,2)

        # Pre-predict bits/sec FOR A UNIT POINT-COUNT:
        # (we’ll multiply by actual n_pts at runtime if your model used it,
        # otherwise this is the final pred_bps)
        # If your model was trained including num_points you should
        # instead leave num_points out of the grid here and build it
        # per callback as in the “Analysis” above.

        # If you trained on a 3-col feature ([q,c,n_pts]) do something like:
        fake_n = 19800
        grid3 = np.hstack([self._grid, np.full((len(self._grid),1), fake_n)])
        Xg = self.poly.transform(grid3)
        self._pred_unit_bps = self.lr.predict(Xg)
        #
        # Then in callback do: pred_bps * n_pts.  

        # # But if you trained on just (q,c) then:
        # Xg2 = self.poly.transform(self._grid)
        self._pred_bps = self.lr.predict(Xg)   # shape=(20,)

        # default desired bits/sec until the first Float32 arrives
        self.desired_bps = self._pred_bps.mean()

        # will hold the last-chosen pair
        self.quant_bits   = int(self._grid[0,0])
        self.comp_level   = int(self._grid[0,1])

        # ---- 2) Subscriber: desired bps ----
        self.create_subscription(
            Float32,
            '/desired_bps',
            self._on_desired_bps,
            10
        )

        # ---- 3) Subscriber: raw LIDAR ----
        self.create_subscription(
            PointCloud2,
            '/husky1/ouster/points',
            self._on_pointcloud,
            10
        )

        # ---- 4) Publisher: decoded for debug/visual ----
        self.decoded_pub = self.create_publisher(
            PointCloud2,
            '/husky1/lidar_points_decoded',
            10
        )

    def _on_desired_bps(self, msg: Float32):
        """Update the desired bits/sec and re-compute q/c."""
        self.desired_bps = float(msg.data)

        # find the grid-index whose predicted bps is closest
        idx = np.abs(self._pred_bps - self.desired_bps).argmin()
        q, c = self._grid[idx]
        self.quant_bits = int(q)
        self.comp_level = int(c)
        self.get_logger().info(
            f'New target={self.desired_bps:.0f}bps → '
            f'q={self.quant_bits}, lvl={self.comp_level}'
        )

    def _on_pointcloud(self, msg: PointCloud2):
        # unpack points
        pts = self._pointcloud2_to_xyz(msg)
        if pts.size == 0:
            return
        
        pts = pts[pts[:,0] > 0]
        # compute quantization range & origin
        mins = pts.min(axis=0)
        maxs = pts.max(axis=0)
        q_range = float((maxs - mins).max())
        q_origin = mins.tolist()

        # encode using the CURRENT q & c
        t0 = time.time()
        compressed = encode(
            points=pts,
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
        dur = time.time() - t0
        self.get_logger().info(
            f'Compressed {pts.shape[0]} pts → '
            f'{len(compressed)} B in {dur*1e3:.1f}ms '
            f'(q={self.quant_bits},lvl={self.comp_level})'
        )

        # OPTIONAL: decode + re-publish for visualization/debug
        decoded = decode(compressed)
        dpts = np.array(decoded.points, dtype=np.float32)
        hdr = msg.header
        out_msg = point_cloud2.create_cloud_xyz32(hdr, dpts.tolist())
        self.decoded_pub.publish(out_msg)

    def _pointcloud2_to_xyz(self, cloud_msg):
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

def main(args=None):
    rclpy.init(args=args)
    node = AdaptivePointCloudCompressor()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()

