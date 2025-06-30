#!/usr/bin/env python3
import socket
import struct

PORT = 30112
BUFFER_SIZE = 65536  # max UDP packet size

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('0.0.0.0', PORT))
    print(f"Listening for RTP on port {PORT}…")

    last_timestamp = None

    while True:
        data, addr = sock.recvfrom(BUFFER_SIZE)
        if len(data) < 12:
            # not enough for RTP header
            continue

        # Unpack the fixed RTP header (12 bytes)
        b1, b2, seq, timestamp, ssrc = struct.unpack('!BBHII', data[:12])
        version = b1 >> 6
        marker  = (b2 & 0x80) != 0
        payload_type = b2 & 0x7F

        # sanity check
        if version != 2:
            continue

        # check for frame boundary
        if marker:
            print(f"[{addr}] ▶ Marker bit set; end of frame ts={timestamp}")
        else:
            if last_timestamp is not None and timestamp != last_timestamp:
                print(f"[{addr}] ▶ Timestamp changed: frame ts={last_timestamp} complete")
        last_timestamp = timestamp

        # (optional) inspect payload:
        # payload = data[12:]
        # do something with payload…

if __name__ == '__main__':
    main()

