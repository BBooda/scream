#!/usr/bin/env python3
import socket
import struct

PORT = 30001
BUF_SIZE = 1024

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('0.0.0.0', PORT))
    print(f"Listening for uint32 bitrates on UDP port {PORT}…")

    while True:
        data, addr = sock.recvfrom(BUF_SIZE)
        if len(data) < 4:
            print(f"Ignoring short packet ({len(data)} bytes) from {addr}")
            continue

        # 1) Unpack big-endian uint32 (same as memcpy+ntohl)
        (rate_raw,) = struct.unpack('!I', data[:4])

        # 2) Emulate the C++ division-by-1000 for "default" media_src
        #    (you can skip this if you just want the raw integer)
        # rate = rate_raw // 1000
        # rate = rate_raw / 1000
        rate = rate_raw 

        # print(f"[{addr}] raw=0x{rate_raw:08X}  rate={rate/ 1000000}")
        print(f"[{addr}] raw=0x{rate_raw:08X}  rate={rate/ 1000000} Mbps")

if __name__ == '__main__':
    main()

