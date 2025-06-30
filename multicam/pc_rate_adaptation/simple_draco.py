#!/usr/bin/python3
import numpy as np
from DracoPy import encode, decode_buffer_to_point_cloud, decode

compression_level = 1          # Compression level in range [0,10]
quantization_range = max_range        # Use default quantization range (largest axis span)
quantization_origin = None     # Compute from the points (minimum along each axis)
create_metadata = True
preserve_order = True
quantization_bits = 8

# Encode+decode
data = encode(points=pts[:,:3],
              faces=None,
              quantization_bits=quantization_bits,
              compression_level=compression_level,
              quantization_range=quantization_range,
              quantization_origin=quantization_origin,
              create_metadata=create_metadata,
              preserve_order=preserve_order,
              colors=None,             # Here we pass the semantic labels as "colors"
              tex_coord=None,
              normals=None)
decoded_data = decode(data)
pred = np.array(decoded_data.points, dtype=np.float32)
