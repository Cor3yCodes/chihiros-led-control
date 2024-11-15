"""Support for Chihiros LED mode selection."""
from __future__ import annotations

import logging
import asyncio

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers import device_registry as dr
from homeassistant.components.bluetooth.passive_update_coordinator import (
    PassiveBluetoothDataUpdateCoordinator
)
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN, MANUFACTURER
from .models import ChihirosData

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Chihiros mode select."""
    chihiros_data: ChihirosData = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ChihirosModeSelect(chihiros_data.coordinator, chihiros_data.device)])

class ChihirosModeSelect(SelectEntity, RestoreEntity):
    """Representation of a Chihiros mode select entity."""

    _attr_options = ["Manual", "Auto"]
    _attr_has_entity_name = True
    _attr_should_poll = True

    def __init__(self, coordinator: PassiveBluetoothDataUpdateCoordinator, device) -> None:
        """Initialize the select entity."""
        self._coordinator = coordinator
        self._device = device
        self._attr_unique_id = f"{coordinator.address}_mode"
        self._attr_name = "Mode"
        self._attr_current_option = "Manual"
        self._retry_count = 0
        self._max_retries = 3
        
        self._attr_device_info = DeviceInfo(
            connections={(dr.CONNECTION_BLUETOOTH, coordinator.address)},
            manufacturer=MANUFACTURER,
            model=device.model_name,
            name=device.name,
        )

    async def async_added_to_hass(self) -> None:
        """Handle entity about to be added to hass."""
        await super().async_added_to_hass()
        await self._update_mode()

    async def _update_mode(self) -> None:
        """Update mode from device."""
        try:
            is_auto = await self._device.is_auto_mode()
            self._attr_current_option = "Auto" if is_auto else "Manual"
            self.async_write_ha_state()
            self._retry_count = 0
        except Exception as ex:
            self._retry_count += 1
            if self._retry_count < self._max_retries:
                _LOGGER.debug("Retrying mode update: %s", ex)
                await asyncio.sleep(1)
                await self._update_mode()
            else:
                _LOGGER.error("Failed to verify mode: %s", ex)

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        try:
            if option == "Auto":
                await self._device.enable_auto_mode()
            else:
                await self._device.disable_auto_mode()
            
            # Give device time to change modes and verify
            for _ in range(3):
                await asyncio.sleep(1)
                is_auto = await self._device.is_auto_mode()
                expected = option == "Auto"
                if is_auto == expected:
                    self._attr_current_option = option
                    self.async_write_ha_state()
                    return
            
            _LOGGER.error("Mode change verification failed")
        except Exception as ex:
            _LOGGER.error("Failed to change mode: %s", ex)

    async def async_update(self) -> None:
        """Update the entity."""
        await self._update_mode()