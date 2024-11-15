"""Support for Chihiros LED mode selection."""
from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import ChihirosDataUpdateCoordinator
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

class ChihirosModeSelect(SelectEntity):
    """Representation of a Chihiros mode select entity."""

    _attr_options = ["Manual", "Auto"]

    def __init__(self, coordinator: ChihirosDataUpdateCoordinator, device) -> None:
        """Initialize the select entity."""
        self._coordinator = coordinator
        self._device = device
        self._attr_unique_id = f"{coordinator.address}_mode"
        self._attr_name = f"{device.name} Mode"
        self._attr_current_option = "Manual"
        
        # Add device info to link this entity to the device
        self._attr_device_info = {
            "identifiers": {("bluetooth", coordinator.address)},
            "name": device.name,
            "manufacturer": "Chihiros",
            "model": device._model_name,
        }

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        if option == "Auto":
            await self._device.enable_auto_mode()
        self._attr_current_option = option
        self.async_write_ha_state()