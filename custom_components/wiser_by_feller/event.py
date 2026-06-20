"""Platform for event integration."""

from __future__ import annotations

import logging

from aiowiserbyfeller import Device, SmartButton
from homeassistant.components.event import EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import WiserCoordinator
from .entity import WiserEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Wiser Smart Button entities."""
    coordinator: WiserCoordinator = entry.runtime_data

    entities = []
    for smb in coordinator.smbs.values():
        device = coordinator.devices[smb.device]
        entities.append(WiserSmbEntity(coordinator, smb, device))

    if entities:
        async_add_entities(entities)


class WiserSmbEntity(WiserEntity, EventEntity):
    """Entity class for Smart Button."""

    def __init__(
        self, coordinator: WiserCoordinator, smb: SmartButton, device: Device
    ) -> None:
        """Set up Wiser Smart Button entity."""
        super().__init__(coordinator, None, device, None)
