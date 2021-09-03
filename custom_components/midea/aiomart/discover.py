import asyncio
import pprint
import socket

from msmart.security import security
from asyncio import transports
from typing import Tuple

BROADCAST_MSG = bytearray([
    0x5a, 0x5a, 0x01, 0x11, 0x48, 0x00, 0x92, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x7f, 0x75, 0xbd, 0x6b, 0x3e, 0x4f, 0x8b, 0x76,
    0x2e, 0x84, 0x9c, 0x6e, 0x57, 0x8d, 0x65, 0x90,
    0x03, 0x6e, 0x9d, 0x43, 0x42, 0xa5, 0x0f, 0x1f,
    0x56, 0x9e, 0xb8, 0xec, 0x91, 0x8e, 0x92, 0xe5
])

DEVICE_INFO_MSG = bytearray([
    0x5a, 0x5a, 0x15, 0x00, 0x00, 0x38, 0x00, 0x04,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x27, 0x33, 0x05,
    0x13, 0x06, 0x14, 0x14, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x03, 0xe8, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0xca, 0x8d, 0x9b, 0xf9, 0xa0, 0x30, 0x1a, 0xe3,
    0xb7, 0xe4, 0x2d, 0x53, 0x49, 0x47, 0x62, 0xbe
])


def device_id2int(device_id: bytes) -> int:
    return int.from_bytes(reversed(device_id), "big")


def bytes2port(data: bytes) -> int:
    i = 0
    for b in range(4):
        if b < len(data):
            b1 = data[b] & 0xFF
        else:
            b1 = 0
        i |= b1 << b * 8
    return i


class DiscoverProtocol(asyncio.DatagramProtocol):
    def __init__(self, future: asyncio.Future, loop=None, *, timeout=1):
        if not loop:
            loop = asyncio.get_event_loop()
        self.found_devices = []
        self.timeout = timeout
        self._security = security()
        self._future = future
        self._loop = loop

    def broadcast(self):
        #print("sending broadcast packet")
        self.transport.sendto(BROADCAST_MSG, ("255.255.255.255", 6445))
        self.transport.sendto(BROADCAST_MSG, ("255.255.255.255", 20086))

    def connection_made(self, transport: transports.DatagramTransport) -> None:
        self.transport = transport
        self.broadcast()
        self._loop.create_task(self.wait(self.timeout))

    def datagram_received(self, data: bytes, addr: Tuple[str, int]) -> None:
        if addr[0] in self.found_devices:
            return
        ret = {}
        if len(data) >= 104 and (data[:2] == b'\x5a\x5a' or data[8:10] == b'\x5a\x5a'):
            if data[:2] == b"\x5a\x5a":
                ret["version"] = "v2"
            elif data[:2] == b"\x83\x70":
                ret["version"] = "v3"
            if data[8:10] == b"\x5a\x5a":
                data = data[8:-16]
            ret["device_id"] = device_id2int(data[20:26])
            reply = self._security.aes_decrypt(data[40:-16])
            dec_ip = '.'.join([str(i) for i in reply[3::-1]])
            if dec_ip == addr[0]:
                ret["ip"] = dec_ip
            else:
                return print(dec_ip, addr[0], "mismatch")
            ret["port"] = bytes2port(reply[4:8])
            ret["sn"] = reply[8:40].decode("utf-8")
            ret["ssid"] = reply[41:41+reply[40]].decode("utf-8")
            ret["type"] = ret["ssid"].split("_")[1]
            self.found_devices.append(ret)

    async def wait(self, sec: int):
        await asyncio.sleep(sec)
        self._future.set_result(self.found_devices)


async def scan() -> dict:
    loop = asyncio.get_event_loop()
    future = loop.create_future()
    await loop.create_datagram_endpoint(
        lambda: DiscoverProtocol(future, loop),
        allow_broadcast=True,
        family=socket.AF_INET
    )
    return await future


if __name__ == '__main__':
    pprint.pprint(asyncio.run(scan()))
