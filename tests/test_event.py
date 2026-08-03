"""Tests for event platform entities."""

from unittest.mock import MagicMock, patch

from aiowiserbyfeller import Device, Load, SmartButton
from homeassistant.components.event import EventDeviceClass

from custom_components.wiser_by_feller.const import SMART_BUTTON_EVENT_TYPES
from custom_components.wiser_by_feller.coordinator import WiserCoordinator
from custom_components.wiser_by_feller.event import (
    WiserSmartButtonEventEntity,
    resolve_host_load,
)

# ── helpers ───────────────────────────────────────────────────────────────────


def _make_device(device_id="0000abed", outputs=None):
    device = MagicMock(spec=Device)
    device.id = device_id
    device.c = {
        "comm_ref": "3401A",
        "comm_name": "Druckschalter 1K",
        "fw_version": "0x00501a30",
    }
    device.a = device.c
    device.c_name = "Druckschalter 1K"
    device.a_name = "Druckschalter 1K"
    device.combined_serial_number = "011110_B_000064"
    device.outputs = outputs if outputs is not None else []
    return device


def _make_load(load_id=1, device_id="0000abed", channel=0, room=10, name="Lampe"):
    load = MagicMock(spec=Load)
    load.id = load_id
    load.device = device_id
    load.channel = channel
    load.room = room
    load.name = name
    return load


def _make_smart_button(button_id=80, device_id="0000abed", channel=2, job=34):
    button = MagicMock(spec=SmartButton)
    button.id = button_id
    button.device = device_id
    button.raw_data = {
        "id": button_id,
        "job": job,
        "device": device_id,
        "channel": channel,
    }
    return button


def _make_coordinator(loads=None, rooms=None):
    coord = MagicMock(spec=WiserCoordinator)
    gw = MagicMock()
    gw.combined_serial_number = "20012161"
    coord.gateway = gw
    coord.loads = loads if loads is not None else {}
    coord.rooms = rooms if rooms is not None else {}
    coord.subscribe_smart_button = MagicMock(return_value=lambda: None)
    return coord


def _make_entity(coordinator=None, smart_button=None, load=None, device=None):
    coordinator = coordinator or _make_coordinator()
    device = device or _make_device()
    return WiserSmartButtonEventEntity(
        coordinator, smart_button or _make_smart_button(), load, device, None
    )


# ── resolve_host_load ─────────────────────────────────────────────────────────


def test_resolve_host_load_returns_first_load():
    """The first output load of the device is used as the button's host load."""
    load = _make_load(load_id=7)
    coord = _make_coordinator(loads={7: load})
    device = _make_device(outputs=[{"load": 7}])
    assert resolve_host_load(coord, device) is load


def test_resolve_host_load_none_without_outputs():
    """Devices without outputs (e.g. scene switches) have no host load."""
    coord = _make_coordinator()
    assert resolve_host_load(coord, _make_device()) is None


def test_resolve_host_load_skips_unknown_loads():
    """Outputs referencing loads unknown to the coordinator are skipped."""
    load = _make_load(load_id=8)
    coord = _make_coordinator(loads={8: load})
    device = _make_device(outputs=[{"load": 99}, {"load": 8}])
    assert resolve_host_load(coord, device) is load


def test_resolve_host_load_none_when_loads_not_loaded():
    """No host load is resolved before the coordinator has loaded the loads."""
    coord = _make_coordinator()
    coord.loads = None
    assert resolve_host_load(coord, _make_device(outputs=[{"load": 1}])) is None


# ── WiserSmartButtonEventEntity ───────────────────────────────────────────────


def test_entity_unique_id_contains_device_and_button_id():
    """The unique ID combines the device ID and the smart button ID."""
    entity = _make_entity(smart_button=_make_smart_button(button_id=80))
    assert entity.unique_id == "0000abed_smart_button_80"


def test_entity_device_class_and_event_types():
    """Smart buttons are exposed as button event entities with all press types."""
    entity = _make_entity()
    assert entity.device_class == EventDeviceClass.BUTTON
    assert entity.event_types == SMART_BUTTON_EVENT_TYPES


def test_entity_name_uses_smart_button_id():
    """The entity name placeholder carries the installation-unique button ID."""
    entity = _make_entity(smart_button=_make_smart_button(button_id=80))
    assert entity.translation_placeholders == {"id": "80"}


def test_entity_names_are_unique_across_identical_devices():
    """Buttons on same-named devices are distinguishable by their ID."""
    first = _make_entity(smart_button=_make_smart_button(button_id=21, channel=2))
    second = _make_entity(smart_button=_make_smart_button(button_id=75, channel=2))
    assert first.translation_placeholders != second.translation_placeholders


def test_entity_shares_device_with_host_load():
    """A button on a load device reuses that load's device registry entry."""
    load = _make_load(load_id=7, channel=1)
    entity = _make_entity(load=load)
    assert entity.raw_unique_id == "0000abed_1"


def test_entity_uses_device_id_without_host_load():
    """A button on a device without loads is attached to the device itself."""
    entity = _make_entity()
    assert entity.raw_unique_id == "0000abed"


async def test_added_to_hass_subscribes_to_coordinator():
    """The entity subscribes to its smart button ID when added to Home Assistant."""
    coord = _make_coordinator()
    entity = _make_entity(coordinator=coord, smart_button=_make_smart_button(21))
    entity.async_on_remove = MagicMock()
    entity.hass = MagicMock()
    with patch(
        "homeassistant.helpers.update_coordinator.CoordinatorEntity.async_added_to_hass"
    ):
        await entity.async_added_to_hass()

    coord.subscribe_smart_button.assert_called_once()
    assert coord.subscribe_smart_button.call_args[0][0] == 21


def test_event_triggers_entity_event():
    """A press event received over the WebSocket is triggered on the entity."""
    entity = _make_entity()
    entity.async_write_ha_state = MagicMock()
    entity._handle_smart_button_event(
        {"smart_button_id": 80, "event": "press", "type": "button"}
    )

    assert entity.state_attributes["event_type"] == "press"
    assert entity.state_attributes["type"] == "button"
    entity.async_write_ha_state.assert_called_once()


def test_unknown_event_type_ignored():
    """Event types the entity does not declare are ignored rather than raising."""
    entity = _make_entity()
    entity.async_write_ha_state = MagicMock()
    entity._handle_smart_button_event({"smart_button_id": 80, "event": "wiggle"})

    assert entity.state_attributes["event_type"] is None
    entity.async_write_ha_state.assert_not_called()


def test_coordinator_update_does_not_clear_event():
    """Polled coordinator updates leave the last received event untouched."""
    entity = _make_entity()
    entity.async_write_ha_state = MagicMock()
    entity._handle_smart_button_event({"smart_button_id": 80, "event": "click"})
    entity._handle_coordinator_update()

    assert entity.state_attributes["event_type"] == "click"


# ── setup ─────────────────────────────────────────────────────────────────────


async def _setup(hass, mock_config_entry, mock_coordinator):
    mock_config_entry.add_to_hass(hass)
    with (
        patch("custom_components.wiser_by_feller.Auth"),
        patch("custom_components.wiser_by_feller.WiserByFellerAPI"),
        patch(
            "custom_components.wiser_by_feller.WiserCoordinator",
            return_value=mock_coordinator,
        ),
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()


async def test_setup_creates_one_entity_per_smart_button(
    hass, mock_config_entry, mock_coordinator
):
    """Each smart button reported by the µGateway becomes one event entity."""
    mock_coordinator.devices = {"0000abed": _make_device()}
    mock_coordinator.smart_buttons = {
        21: _make_smart_button(button_id=21, channel=2),
        24: _make_smart_button(button_id=24, channel=3),
    }

    await _setup(hass, mock_config_entry, mock_coordinator)

    assert len(hass.states.async_entity_ids("event")) == 2


async def test_setup_skips_buttons_on_unknown_devices(
    hass, mock_config_entry, mock_coordinator
):
    """Smart buttons pointing at devices the µGateway didn't report are skipped."""
    mock_coordinator.devices = {"0000abed": _make_device()}
    mock_coordinator.smart_buttons = {
        21: _make_smart_button(button_id=21),
        80: _make_smart_button(button_id=80, device_id="0000d012"),
    }

    await _setup(hass, mock_config_entry, mock_coordinator)

    assert len(hass.states.async_entity_ids("event")) == 1


async def test_setup_without_smart_buttons(hass, mock_config_entry, mock_coordinator):
    """No event entities are created when the system has no smart buttons."""
    await _setup(hass, mock_config_entry, mock_coordinator)

    assert hass.states.async_entity_ids("event") == []
