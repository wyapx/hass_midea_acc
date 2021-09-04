import logging
from typing import Optional, List

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import TEMP_CELSIUS, ATTR_TEMPERATURE
from homeassistant.core import HomeAssistant
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import *
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.restore_state import RestoreEntity

from .aiomart.aiomart import AC, Device
from .aiomart.discover import scan

SUPPORT_FLAGS = SUPPORT_TARGET_TEMPERATURE | SUPPORT_FAN_MODE | SUPPORT_SWING_MODE | SUPPORT_PRESET_MODE
SUPPORTED_FEATURES_MAP = {
    ATTR_TEMPERATURE: SUPPORT_TARGET_TEMPERATURE,
    ATTR_TARGET_TEMP_HIGH: 30,
    ATTR_TARGET_TEMP_LOW: 17,
    ATTR_FAN_MODE: SUPPORT_FAN_MODE,
    ATTR_SWING_MODE: SUPPORT_SWING_MODE,
    ATTR_PRESET_MODE: SUPPORT_PRESET_MODE,
}


_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass: HomeAssistant, config_entry: ConfigEntry, add_entities, discovery_info=None):
    devices_list = await scan()
    entities = []
    _LOGGER.warning("%s devices_list found" % len(devices_list))
    for device in devices_list:
        if device["type"] == "ac":
            ac_device = Device(device["ip"], device["device_id"], device["port"]).setup()
            await ac_device.refresh()
            entities.append(
                MideaACDevice(hass, ac_device, 0.5)
            )
    if len(entities) > 0:
        add_entities(entities)
        _LOGGER.warning("%s devices_list loaded" % len(entities))
        return True
    _LOGGER.warning("no devices_list loaded")
    return False


class MideaACDevice(ClimateEntity, RestoreEntity):
    def __init__(self, hass: HomeAssistant, device: AC, temp_step: float):
        self.hass = hass
        self.device = device
        self._attr_target_temperature_step = temp_step
        self._attr_target_temperature_high = 30
        self._attr_target_temperature_low = 17
        self._attr_target_temperature = device.target_temperature
        self._attr_temperature_unit = TEMP_CELSIUS

        features = 0
        for f in SUPPORTED_FEATURES_MAP.keys():
            features |= SUPPORTED_FEATURES_MAP[f]
        for f in SUPPORTED_FEATURES_MAP.keys():
            features |= SUPPORTED_FEATURES_MAP[f]
        self._supported_features = features

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
        self.device.fan_speed = air_conditioning_device.fan_speed_enum(fan_mode).value
        await self.device.apply()

    async def async_set_hvac_mode(self, hvac_mode: str) -> None:
        self.device.operational_mode = AC.operational_mode_enum(hvac_mode).value
        await self.device.apply()

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        self.device.swing_mode = AC.swing_mode_enum(swing_mode).value
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

    @property
    def hvac_mode(self) -> str:
        return self.device.operational_mode.name

    @property
    def hvac_modes(self) -> list[str]:
        return [HVAC_MODE_AUTO, HVAC_MODE_DRY, HVAC_MODE_HEAT, HVAC_MODE_COOL, HVAC_MODE_FAN_ONLY]

    @property
    def supported_features(self) -> int:
        return self._supported_features

    @property
    def fan_mode(self) -> Optional[str]:
        return self.device.fan_speed.name

    @property
    def fan_modes(self) -> list[str]:
        return [FAN_ON, FAN_AUTO, FAN_HIGH, FAN_MEDIUM, FAN_MIDDLE, FAN_LOW]
