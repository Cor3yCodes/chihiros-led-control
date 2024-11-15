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

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the user step to pick discovered device."""
        if user_input is not None:
            return self.async_create_entry(
                title=self._discovered_devices[user_input[CONF_ADDRESS]].name,
                data={},
                unique_id=user_input[CONF_ADDRESS].lower(),
            )

        current_addresses = self._async_current_ids()
        for discovery in async_discovered_service_info(self.hass):
            address = discovery.address
            if address in current_addresses or address in self._discovered_devices:
                continue
                
            # Filter for Chihiros devices
            if discovery.name:
                device_name = discovery.name[:-12]  # Remove MAC
                is_valid = False
                for model_code in CODE2MODEL.keys():
                    if device_name.startswith(model_code):
                        is_valid = True
                        break
                # Check for service UUID in service_data
                if "6e400001-b5a3-f393-e0a9-e50e24dcca9e" in discovery.service_data:
                    is_valid = True
                if is_valid:
                    self._discovered_devices[address] = discovery

        if not self._discovered_devices:
            return self.async_abort(reason="no_devices_found")

        data_schema = vol.Schema(
            {
                vol.Required(CONF_ADDRESS): vol.In(
                    {
                        address: f"{discovery.name} ({address})"
                        for address, discovery in self._discovered_devices.items()
                    }
                )
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
        )
