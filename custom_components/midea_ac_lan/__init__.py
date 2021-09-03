import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .aiomart.aiomart import Device, AC
from .aiomart.discover import scan
from .climate import MideaACDevice

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    devices = await scan()
    entities = []
    _LOGGER.warning("%s devices found" % len(devices))
    for ip, data in devices.items():
        if data["type"] == "ac":
            device = await Device(ip, data["sn"], data["port"]).setup()
            await device.refresh()
            entities.append(
                MideaACDevice(hass, device, 0.5)
            )
    if len(entities) > 0:
        hass.data[config_entry.entry_id] = {
            "climate_devices": entities
        }
        _LOGGER.info("%s devices loaded" % len(entities))
        return True
    _LOGGER.warning("no devices loaded")
    return False
