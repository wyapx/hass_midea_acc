from typing import Optional, List

from homeassistant.const import TEMP_CELSIUS, ATTR_TEMPERATURE
from homeassistant.core import HomeAssistant, Config
from homeassistant.components.climate import ClimateDevice
from homeassistant.components.climate.const import *
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.restore_state import RestoreEntity

from .aiomart.aiomart import Device, AC
from .aiomart.discover import scan

SUPPORT_FLAGS = SUPPORT_TARGET_TEMPERATURE | SUPPORT_FAN_MODE | SUPPORT_SWING_MODE | SUPPORT_PRESET_MODE


async def async_setup_platform(hass: HomeAssistant, config: Config, async_add_entities, discovery_info=None):
    devices = await scan()
    entities = []
    for ip, data in devices.items():
        if data["type"] == "ac":
            device = await Device(ip, data["sn"], data["port"]).setup()
            await device.refresh()
            entities.append(
                MideaACDevice(hass, device, 0.5)
            )
    async_add_entities(entities)


class MideaACDevice(ClimateDevice, RestoreEntity):
    def __init__(self, hass: HomeAssistant, device: AC, temp_step: float):
        self.hass = hass
        self.device = device
        self._attr_target_temperature_step = temp_step
        self._attr_target_temperature_high = 30
        self._attr_target_temperature_low = 17
        self._attr_target_temperature = device.target_temperature
        self._attr_temperature_unit = TEMP_CELSIUS

    async def device_info(self) -> Optional[DeviceInfo]:
        return DeviceInfo(
            name=self.device.name,
            manufacturer="Midea",
            model="Midea AC Device",
            entry_type="HVAC"
        )

    async def async_device_update(self, warning: bool = True) -> None:
        await self.device.refresh()

    async def async_turn_on(self) -> None:
        self.device.power_state = True
        await self.device.apply()

    async def async_turn_off(self) -> None:
        self.device.power_state = False
        await self.device.apply()

    async def async_set_temperature(self, **kwargs) -> None:
        if kwargs.get(ATTR_TEMPERATURE) is not None:
            self.device.target_temperature = kwargs[ATTR_TEMPERATURE]
            await self.device.apply()

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        from msmart.device import air_conditioning_device
        self.device.fan_speed = air_conditioning_device.fan_speed_enum[fan_mode]
        await self.device.apply()

    async def async_set_hvac_mode(self, hvac_mode: str) -> None:
        self.device.operational_mode = AC.operational_mode_enum[hvac_mode]
        await self.device.apply()

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        self.device.swing_mode = AC.swing_mode_enum[swing_mode]
        await self.device.apply()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        if preset_mode == PRESET_ECO:
            self.device.eco_mode = True
            self.device.turbo_mode = False
        elif preset_mode == PRESET_BOOST:
            self.device.eco_mode = False
            self.device.turbo_mode = True
        else:
            self.device.eco_mode = False
            self.device.turbo_mode = False
        await self.device.apply()

    @property
    def preset_mode(self) -> Optional[str]:
        if self.device.eco_mode:
            return PRESET_ECO
        elif self.device.turbo_mode:
            return PRESET_BOOST

    @property
    def preset_modes(self) -> List[str]:
        return [PRESET_NONE, PRESET_ECO, PRESET_BOOST]

    @property
    def swing_mode(self) -> Optional[str]:
        return self.device.swing_mode.name

    @property
    def swing_modes(self) -> List[str]:
        return [SWING_OFF, SWING_BOTH, SWING_VERTICAL, SWING_HORIZONTAL]
