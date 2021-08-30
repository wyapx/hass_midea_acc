import asyncio
import enum

from msmart.lan import lan
from msmart.device import air_conditioning_device, device
from msmart.packet_builder import packet_builder
from msmart.command import appliance_response, base_command, set_command


class Lan(lan):
    async def request(self, message: bytes) -> bytes:
        reader, writer = await asyncio.open_connection(self.device_ip, self.device_port)
        writer.write(message)
        await writer.drain()
        return await reader.read(512)  # avg 1.8s

    async def appliance_transparent_send(self, data: bytes) -> bytearray:
        response = bytearray(await self.request(data))
        if len(response) > 0:
            if len(response) == 88:
                reply = self.decode(self.security.aes_decrypt(response[40:72]))
            else:
                reply = self.decode(self.security.aes_decrypt(response[40:88]))
            return reply
        else:
            return bytearray(0)


class AC(air_conditioning_device):

    """class fan_speed_enum(enum.IntEnum):
        Auto = 102
        High = 80
        Medium = 60
        Low = 40
        Silent = 20
        Useless = 0

        @staticmethod
        def list():
            return list(map(lambda c: c.name, air_conditioning_device.fan_speed_enum))

        @staticmethod
        def get(value):
            if value in AC.fan_speed_enum._value2member_map_:
                return AC.fan_speed_enum(value)
            #_LOGGER.debug("Unknown Fan Speed: {}".format(value))
            elif value < 0 or value > 100:
                raise ValueError("The value must between 100 and 0")
            return Value(value)"""

    class fan_speed_enum(int):
        def __init__(self, value):
            self._value = value

        def __str__(self) -> str:
            return str(self._value)

        def __int__(self) -> int:
            return int(self._value)

        @property
        def value(self):
            return self._value

        @property
        def key(self) -> str:
            return "Any"

    class operational_mode_enum(enum.IntEnum):
        auto = 1
        cool = 2
        dry = 3
        heat = 4
        fan_only = 5

        @staticmethod
        def list():
            return list(map(lambda c: c.name, air_conditioning_device.operational_mode_enum))

        @staticmethod
        def get(value):
            if value in air_conditioning_device.operational_mode_enum._value2member_map_:
                return air_conditioning_device.operational_mode_enum(value)
            #_LOGGER.debug("Unknown Operational Mode: {}".format(value))
            return air_conditioning_device.operational_mode_enum.fan_only

    class swing_mode_enum(enum.IntEnum):
        Off = 0x0
        Vertical = 0xC
        Horizontal = 0x3
        Both = 0xF

        @staticmethod
        def list():
            return list(map(lambda c: c.name, air_conditioning_device.swing_mode_enum))

        @staticmethod
        def get(value):
            if value in air_conditioning_device.swing_mode_enum._value2member_map_:
                return air_conditioning_device.swing_mode_enum(value)
            #_LOGGER.debug("Unknown Swing Mode: {}".format(value))
            return air_conditioning_device.swing_mode_enum.Off

    def __init__(self, device_ip: str, device_id: str, device_port: int):
        super(AC, self).__init__(device_ip, device_id, device_port)
        self._lan_service = Lan(device_ip, device_id, device_port)

    async def refresh(self):
        cmd = base_command(self.type)
        pkt_builder = packet_builder(self.id)
        pkt_builder.set_command(cmd)

        data = pkt_builder.finalize()
        data = await self._lan_service.appliance_transparent_send(data)
        if len(data) > 0:
            self._online = True
            response = appliance_response(data)
            self._defer_update = False
            self._support = True
            if not self._defer_update:
                if data[0xa] == 0xc0:
                    self.update(response)
                if data[0xa] == 0xa1 or data[0xa] == 0xa0:
                    '''only update indoor_temperature and outdoor_temperature'''
                    pass
                    # self.update_special(response)
                self._defer_update = False
        else:
            self._online = False

    async def apply(self):
        self._updating = True
        try:
            cmd = set_command(self.type)
            cmd.prompt_tone = self._prompt_tone
            cmd.power_state = self._power_state
            cmd.target_temperature = self._target_temperature
            cmd.operational_mode = self._operational_mode
            cmd.fan_speed = self._fan_speed
            cmd.swing_mode = self._swing_mode
            cmd.eco_mode = self._eco_mode
            cmd.turbo_mode = self._turbo_mode
            pkt_builder = packet_builder(self.id)
            #            cmd.night_light = False
            cmd.fahrenheit = self.farenheit_unit
            pkt_builder.set_command(cmd)

            data = pkt_builder.finalize()
            data = await self._lan_service.appliance_transparent_send(data)
            if len(data) > 0:
                self._online = True
                response = appliance_response(data)
                self._support = True
                if not self._defer_update:
                    if data[0xa] == 0xc0:
                        self.update(response)
                    if data[0xa] == 0xa1 or data[0xa] == 0xa0:
                        '''only update indoor_temperature and outdoor_temperature'''
                        pass
                        # self.update_special(response)
            else:
                self._online = False
        finally:
            self._updating = False
            self._defer_update = False


class Device(device):
    def setup(self):
        return AC(self._ip, str(self._id), self._port)
