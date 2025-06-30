#!/usr/bin/env python3
import socket
import struct
import numpy as np
from DracoPy import decode

PORT = 30112
BUFFER_SIZE = 65536  # large enough for one UDP/RTP packet

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('0.0.0.0', PORT))
    print(f"Listening for RTP on port {PORT}…")

    last_timestamp = None
    current_payload = bytearray()

    while True:
        data, addr = sock.recvfrom(BUFFER_SIZE)
        if len(data) < 12:
            continue  # too small to be RTP

        # --- parse RTP header ---
        b1, b2, seq, timestamp, ssrc = struct.unpack('!BBHII', data[:12])
        version     = b1 >> 6
        marker_bit  = (b2 & 0x80) != 0
        payload_type= b2 & 0x7F

        if version != 2:
            continue  # not RTPv2

        payload = data[12:]

        # --- frame boundary by timestamp change (fallback) ---
        if last_timestamp is not None and timestamp != last_timestamp and not marker_bit:
            _decode_and_print(current_payload)
            current_payload.clear()

        # --- append this packet’s payload ---
        current_payload.extend(payload)

        # --- frame boundary by marker bit ---
        if marker_bit:
            _decode_and_print(current_payload)
            current_payload.clear()

        last_timestamp = timestamp


def _decode_and_print(compressed_bytes: bytearray):
    if not compressed_bytes:
        return
    compressed = bytes(compressed_bytes)
    try:
        decoded = decode(compressed)
        pts = np.array(decoded.points, dtype=np.float32)
        print(f"▶ Decoded frame: {pts.shape} points")
    except Exception as e:
        print(f"!! Draco decode failed: {e}")


if __name__ == '__main__':
    main()

