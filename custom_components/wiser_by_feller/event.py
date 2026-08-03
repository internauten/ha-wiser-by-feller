"""Platform for event integration."""

from __future__ import annotations

import logging

from aiowiserbyfeller import Device, Load, SmartButton
from homeassistant.components.event import EventDeviceClass, EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import SMART_BUTTON_EVENT_TYPES
from .coordinator import WiserCoordinator
from .entity import WiserEntity

PARALLEL_UPDATES = 0
_LOGGER = logging.getLogger(__name__)


def resolve_host_load(coordinator: WiserCoordinator, device: Device) -> Load | None:
    """Return the first load of a device.

    Smart buttons are inputs and carry neither a load nor a room. Devices with
    outputs are registered in Home Assistant per load channel, so the button is
    attached to the device's first load to avoid registering a second, near
    identical device for the same piece of hardware.
    """
    if coordinator.loads is None:
        return None

    for output in device.outputs:
        load = coordinator.loads.get(output.get("load"))
        if load is not None:
            return load

    return None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Wiser event entities."""
    coordinator: WiserCoordinator = entry.runtime_data

    assert coordinator.devices is not None
    assert coordinator.rooms is not None
    entities: list[WiserSmartButtonEventEntity] = []
    for smart_button in (coordinator.smart_buttons or {}).values():
        device = coordinator.devices.get(smart_button.device)
        if device is None:
            _LOGGER.warning(
                "Smart button %s references unknown device %s, skipping",
                smart_button.id,
                smart_button.device,
            )
            continue

        load = resolve_host_load(coordinator, device)
        room = (
            coordinator.rooms.get(load.room)
            if load is not None and load.room is not None
            else None
        )
        entities.append(
            WiserSmartButtonEventEntity(coordinator, smart_button, load, device, room)
        )

    if entities:
        async_add_entities(entities)


class WiserSmartButtonEventEntity(WiserEntity, EventEntity):
    """Entity class for smart buttons (SMB).

    Smart buttons don't control a load, they only report presses. The µGateway
    does not push these natively, so a gateway script forwards them over the
    WebSocket connection (see docs/SMB.md).
    """

    _device: Device
    _attr_device_class = EventDeviceClass.BUTTON
    _attr_event_types = SMART_BUTTON_EVENT_TYPES
    _attr_translation_key = "smart_button"

    def __init__(
        self,
        coordinator: WiserCoordinator,
        smart_button: SmartButton,
        load: Load | None,
        device: Device,
        room: dict | None,
    ) -> None:
        """Set up the smart button event entity."""
        super().__init__(coordinator, load, device, room)
        del self._attr_name
        self._smart_button = smart_button
        self._attr_unique_id = f"{device.id}_smart_button_{smart_button.id}"
        # The smart button id is unique across the installation, so it names the
        # entity unambiguously even where several devices share a device name.
        self._attr_translation_placeholders = {"id": str(smart_button.id)}

    async def async_added_to_hass(self) -> None:
        """Subscribe to smart button events."""
        await super().async_added_to_hass()
        assert self._smart_button.id is not None
        self.async_on_remove(
            self.coordinator.subscribe_smart_button(
                self._smart_button.id, self._handle_smart_button_event
            )
        )

    @callback
    def _handle_smart_button_event(self, event: dict) -> None:
        """Handle a smart button event pushed over the WebSocket connection."""
        event_type = event["event"]
        if event_type not in SMART_BUTTON_EVENT_TYPES:
            _LOGGER.debug(
                "Ignoring unknown smart button event type '%s' for button %s",
                event_type,
                self._smart_button.id,
            )
            return

        self._trigger_event(event_type, {"type": event.get("type")})
        self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator.

        Smart button state is push-only; polled updates carry nothing to apply.
        """
