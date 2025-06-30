#!/usr/bin/env python3
"""
rtp_sender.py

Reads a Python object (or byte array) supplied in the script, pickles it,
builds an RTP packet (12-byte header + payload), and sends it over UDP.
"""

import socket
import struct
import pickle
import time
import argparse
import random

RTP_VERSION = 2
PAYLOAD_TYPE = 96  # Dynamic payload type (often used for application-specific data)


def build_rtp_header(seq_num, timestamp, ssrc, marker=0, payload_type=PAYLOAD_TYPE):
    """
    Construct a 12-byte RTP header.
    - Version: 2 bits (2)
    - Padding: 1 bit (0)
    - Extension: 1 bit (0)
    - CSRC count: 4 bits (0)
    - Marker: 1 bit (0 or 1)
    - Payload Type: 7 bits (dynamic: 96–127)
    - Sequence Number: 16 bits
    - Timestamp: 32 bits
    - SSRC: 32 bits
    Returns: bytes of length 12
    """
    # First byte: V (2 bits), P (1), X (1), CC (4)
    b0 = (RTP_VERSION << 6) | 0  # P=0, X=0, CC=0
    # Second byte: M (1), PT (7)
    b1 = ((marker & 0x1) << 7) | (payload_type & 0x7F)
    header = struct.pack("!BBHII", b0, b1, seq_num & 0xFFFF, timestamp & 0xFFFFFFFF, ssrc & 0xFFFFFFFF)
    return header


def send_pickled_object(obj, dest_ip, dest_port, ssrc=None, start_seq=0):
    """
    Pickles `obj`, encapsulates it in RTP (header + payload), and sends via UDP to dest_ip:dest_port.
    - ssrc: if None, random 32-bit.
    - start_seq: initial sequence number (default 0).
    """
    if ssrc is None:
        ssrc = random.getrandbits(32)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    seq_num = start_seq
    # You might want to send multiple packets (e.g., for streaming); here, we send just one.
    # If you have a larger object, consider fragmenting into MTU-sized chunks and incrementing seq_num per chunk.

    # 1) Pickle the object
    data_bytes = pickle.dumps(obj)

    # 2) Generate a timestamp (e.g., using time.time())
    #    For demo, use current time in milliseconds as timestamp.
    timestamp = int(time.time() * 1000) & 0xFFFFFFFF

    # 3) Build RTP header
    header = build_rtp_header(seq_num=seq_num, timestamp=timestamp, ssrc=ssrc)

    # 4) Concatenate header + payload
    packet = header + data_bytes

    # 5) Send over UDP
    sock.sendto(packet, (dest_ip, dest_port))
    print(f"Sent RTP packet to {dest_ip}:{dest_port}")
    print(f"  SSRC: 0x{ssrc:08X}")
    print(f"  Sequence Number: {seq_num}")
    print(f"  Timestamp: {timestamp}")
    print(f"  Payload size: {len(data_bytes)} bytes")
    sock.close()


def main():
    parser = argparse.ArgumentParser(description="Send a pickled object over RTP (UDP).")
    parser.add_argument("dest_ip", help="Destination IP address")
    parser.add_argument("dest_port", type=int, help="Destination port")
    parser.add_argument("--seq", type=int, default=0, help="Starting RTP sequence number (default: 0)")
    parser.add_argument("--ssrc", type=lambda x: int(x, 0), default=None,
                        help="SSRC as a 32-bit integer (e.g. 0x1234ABCD). If not provided, a random SSRC is used.")
    args = parser.parse_args()

    # Example object to send: you can replace this with any Python object.
    example_obj = {
        "message": "Hello, RTP!",
        "timestamp_sent": time.ctime(),
        "numbers": [1, 2, 3, 4, 5]
    }

    for i in range(0, 100):
        send_pickled_object(
            obj=example_obj,
            dest_ip=args.dest_ip,
            dest_port=args.dest_port,
            ssrc=args.ssrc,
            start_seq=i
        )

        time.sleep(0.5)


if __name__ == "__main__":
    main()

