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
from homeassistant.const import CONF_DEVICE
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.device_registry import format_mac

from .chihiros_led_control.device import BaseDevice, CODE2MODEL, get_model_class_from_name
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

ADDITIONAL_DISCOVERY_TIMEOUT = 60


class ChihirosConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Chihiros."""

    VERSION = 1
    MINOR_VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovery_info: BluetoothServiceInfoBleak | None = None
        self._discovered_device: BaseDevice | None = None
        self._discovered_devices: dict[str, BluetoothServiceInfoBleak] = {}

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> FlowResult:
        """Handle the bluetooth discovery step."""
        await self.async_set_unique_id(format_mac(discovery_info.address))
        self._abort_if_unique_id_configured()
        
        try:
            model_class = get_model_class_from_name(discovery_info.name)
            device = model_class(discovery_info.device)
            self._discovery_info = discovery_info
            self._discovered_device = device
            _LOGGER.debug(
                "async_step_bluetooth - discovered device %s", discovery_info.name
            )
            return await self.async_step_bluetooth_confirm()
        except Exception:  # pylint: disable=broad-except
            return self.async_abort(reason="not_supported")

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

        placeholders = {"name": title}
        self.context["title_placeholders"] = placeholders
        return self.async_show_form(
            step_id="bluetooth_confirm", description_placeholders=placeholders
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the user step to pick discovered device."""
        if user_input is not None:
            address = user_input[CONF_DEVICE]
            await self.async_set_unique_id(
                format_mac(address), raise_on_progress=False
            )
            try:
                return self.async_create_entry(
                    title=self._discovered_devices[address].name,
                    data={},
                )
            except Exception:  # pylint: disable=broad-except
                return self.async_abort(reason="cannot_connect")

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
                if "6e400001-b5a3-f393-e0a9-e50e24dcca9e" in discovery.service_data:
                    is_valid = True
                if is_valid:
                    self._discovered_devices[address] = discovery

        if not self._discovered_devices:
            return self.async_abort(reason="no_devices_found")

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DEVICE): vol.In(
                        {
                            address: f"{discovery.name} ({address})"
                            for address, discovery in self._discovered_devices.items()
                        }
                    )
                }
            ),
        )
