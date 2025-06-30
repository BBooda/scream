# server.py
import asyncio
from aiortc.rtp import RtpPacket
from aiortc.rtcp import RtcpReceiverReport
import socket

RTP_PORT = 5004
RTCP_PORT = 5005

async def rtp_receiver():
    rtp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rtp_sock.bind(("0.0.0.0", RTP_PORT))

    print(f"RTP server listening on port {RTP_PORT}")
    while True:
        data, addr = rtp_sock.recvfrom(2048)
        pkt = RtpPacket.parse(data)
        print(f"Received RTP: SSRC={pkt.ssrc}, Seq={pkt.sequence_number}, Timestamp={pkt.timestamp}")
        # simulate RTCP response
        await send_rtcp_report(addr[0])

async def send_rtcp_report(dest_ip):
    rtcp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rtcp = RtcpReceiverReport(ssrc=1234, reports=[])
    rtcp_sock.sendto(bytes(rtcp), (dest_ip, RTCP_PORT))
    print("Sent RTCP receiver report")

asyncio.run(rtp_receiver())

