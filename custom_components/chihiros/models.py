"""The chihiros integration models."""

from __future__ import annotations

from dataclasses import dataclass

from .chihiros_led_control.device import BaseDevice
from homeassistant.components.bluetooth.passive_update_coordinator import (
    PassiveBluetoothDataUpdateCoordinator
)


@dataclass
class ChihirosData:
    """Data for the chihiros integration."""

    title: str
    device: BaseDevice
    coordinator: PassiveBluetoothDataUpdateCoordinator
