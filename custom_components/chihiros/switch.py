"""Support for Chihiros LED connection switch."""
from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers import device_registry as dr
from homeassistant.components.bluetooth.passive_update_coordinator import (
    PassiveBluetoothDataUpdateCoordinator
)

from .const import DOMAIN, MANUFACTURER
from .models import ChihirosData

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Chihiros connection switch."""
    chihiros_data: ChihirosData = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ChihirosConnectionSwitch(chihiros_data.coordinator, chihiros_data.device)])

class ChihirosConnectionSwitch(SwitchEntity):
    """Representation of a Chihiros connection switch entity."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: PassiveBluetoothDataUpdateCoordinator, device) -> None:
        """Initialize the switch entity."""
        self._coordinator = coordinator
        self._device = device
        self._attr_unique_id = f"{coordinator.address}_connection"
        self._attr_name = "Connection"
        self._attr_is_on = True
        self._connection_retries = 0
        self._max_retries = 3
        
        self._attr_device_info = DeviceInfo(
            connections={(dr.CONNECTION_BLUETOOTH, coordinator.address)},
            manufacturer=MANUFACTURER,
            model=device.model_name,
            name=device.name,
        )

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if self._connection_retries < self._max_retries:
            return True
        return self._device._client is not None

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        try:
            return self._device.is_connected
        except Exception:
            return False

    async def async_turn_on(self, **kwargs) -> None:
        """Turn on the connection."""
        try:
            await self._device._ensure_connected()
            self._attr_is_on = True
            self._connection_retries = 0
        except Exception as ex:
            _LOGGER.debug("Connection attempt failed: %s", ex)
            self._connection_retries += 1
        finally:
            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off the connection."""
        try:
            await self._device.disconnect()
            self._attr_is_on = False
        except Exception as ex:
            _LOGGER.debug("Disconnect attempt failed: %s", ex)
        finally:
            self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Handle entity about to be added to hass."""
        await super().async_added_to_hass()
        try:
            await self.async_turn_on()
        except Exception as ex:
            _LOGGER.debug("Initial connection attempt failed: %s", ex)