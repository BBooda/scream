#!/usr/bin/env python3
import socket
import struct

PORT = 30001
BUFFER_SIZE = 1024  # Should be >= 4

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('0.0.0.0', PORT))
    print(f"Listening for float values on UDP port {PORT}…")

    while True:
        data, addr = sock.recvfrom(BUFFER_SIZE)
        if len(data) < 4:
            print(f"Ignoring packet from {addr}, too short ({len(data)} bytes)")
            continue

        # Unpack the first 4 bytes as a big-endian float
        try:
            (value,) = struct.unpack('!f', data[:4])
            # check integer: 
            # (value,) = struct.unpack('!I', data[:4])
            print(f"[{addr}] Received float: {value}")
        except struct.error as e:
            print(f"[{addr}] Failed to unpack float: {e}")

if __name__ == '__main__':
    main()

