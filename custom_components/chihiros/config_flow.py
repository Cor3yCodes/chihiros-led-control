"""Config flow for chihiros integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol  # type: ignore
from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_ADDRESS
from homeassistant.data_entry_flow import FlowResult

from .chihiros_led_control.device import BaseDevice, CODE2MODEL, get_model_class_from_name
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

ADDITIONAL_DISCOVERY_TIMEOUT = 60

def is_valid_device(discovery: BluetoothServiceInfoBleak) -> bool:
    """Check if discovered device is a supported Chihiros device."""
    if not discovery.name:
        return False
    device_name = discovery.name[:-12]  # Remove last 12 chars (MAC address)
    
    # Check if device name starts with any of our model codes
    for model_code in CODE2MODEL.keys():
        if device_name.startswith(model_code):
            return True
            
    # If no match but has the service UUID, use fallback
    if discovery.service_data_uuid == "6e400001-b5a3-f393-e0a9-e50e24dcca9e":
        return True
        
    return False

class ChihirosConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for chihiros."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovery_info: BluetoothServiceInfoBleak | None = None
        self._discovered_device: BaseDevice | None = None
        self._discovered_devices: dict[str, BluetoothServiceInfoBleak] = {}

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> FlowResult:
        """Handle the bluetooth discovery step."""
        if not is_valid_device(discovery_info):
            return self.async_abort(reason="not_supported")
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        model_class = get_model_class_from_name(discovery_info.name)
        device = model_class(discovery_info.device)
        self._discovery_info = discovery_info
        self._discovered_device = device
        _LOGGER.debug(
            "async_step_bluetooth - discovered device %s", discovery_info.name
        )
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm discovery."""
        assert self._discovered_device is not None
        device = self._discovered_device
        assert self._discovery_info is not None
        discovery_info = self._discovery_info
        title = device.name or discovery_info.name
        if user_input is not None:
            return self.async_create_entry(title=title, data={})

        self._set_confirm_only()
        placeholders = {"name": title}
        self.context["title_placeholders"] = placeholders
        return self.async_show_form(
            step_id="bluetooth_confirm", description_placeholders=placeholders
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the user step to pick discovered device."""
        errors: dict[str, str] = {}

        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            discovery_info = self._discovered_devices[address]
            await self.async_set_unique_id(
                discovery_info.address, raise_on_progress=False
            )
            self._abort_if_unique_id_configured()
            model_class = get_model_class_from_name(discovery_info.name)
            device = model_class(discovery_info.device)

            self._discovery_info = discovery_info
            self._discovered_device = device
            title = device.name or discovery_info.name
            return self.async_create_entry(
                title=title, data={CONF_ADDRESS: discovery_info.address}
            )

        if discovery := self._discovery_info:
            self._discovered_devices[discovery.address] = discovery
        else:
            current_addresses = self._async_current_ids()
            for discovery in async_discovered_service_info(self.hass):
                if (
                    discovery.address in current_addresses
                    or discovery.address in self._discovered_devices
                ):
                    continue
                self._discovered_devices[discovery.address] = discovery

        if not self._discovered_devices:
            return self.async_abort(reason="no_devices_found")

        data_schema = vol.Schema(
            {
                vol.Required(CONF_ADDRESS): vol.In(
                    {
                        service_info.address: (
                            f"{service_info.name} ({service_info.address})"
                        )
                        for service_info in self._discovered_devices.values()
                    }
                ),
            }
        )
        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )
