# 🔘 Smart Buttons (SMB)

Smart Buttons are buttons in your Wiser installation that don't switch a load
directly — they run a **job** stored on the µGateway. The integration reads them
from the gateway and exposes each one as an **event entity**, so you can use
them as automation triggers like any other Home Assistant button.

> [!IMPORTANT]
> Smart buttons do **not** report presses on their own. You have to install a
> small gateway script that pushes the press over the WebSocket connection — see
> [Enabling press events](#enabling-press-events) below. Without it, the
> entities are created but stay empty.

## The entities

For every smart button reported by `GET /api/smartbuttons`, the integration
creates one event entity, e.g. `event.living_room_dimmer_smart_button_3`.

| Attribute | Description |
|---|---|
| `event_type` | `click` (short press), `press` (long press / held), `release` |
| `type` | Interaction kind reported by the gateway script, e.g. `button` |

Smart buttons are inputs and have no room of their own. A button that sits on a
device with loads is attached to that load's Home Assistant device, so no
duplicate device shows up for the same piece of hardware.

## Enabling press events

Out of the box, smart buttons send no WebSocket updates. As described in the
[Wiser API documentation](https://github.com/Feller-AG/wiser-api/issues/40), a
script on the µGateway can push arbitrary WebSocket messages. Install the
following script and assign it as a job to the smart buttons you want to use:

```python
import websockets
import uasyncio


async def ws_task(argv):
    await websockets.Connection.push_event('/api', {'smb': {'id': argv[2], 'action': argv[0], 'type': argv[1]}})


def onButtonEvent(*argv):
    loop = uasyncio.get_event_loop()
    loop.run_until_complete(ws_task(argv))
```

Each press then pushes a message the integration understands:

```json
{
  "smb": {
    "id": 80,
    "action": "press",
    "type": "button"
  }
}
```

Installing and assigning the script is an advanced, gateway-side step that the
integration does not automate.

## Example automation

```yaml
automation:
  - alias: "Smart button toggles lamp"
    triggers:
      - trigger: state
        entity_id: event.living_room_dimmer_smart_button_3
        attribute: event_type
        to: click
    actions:
      - action: light.toggle
        target:
          entity_id: light.lamp
```

Every press is additionally fired on the Home Assistant event bus as
`wiser_by_feller_smart_button_event`, carrying `smart_button_id`, `event`,
`type` and `config_entry_id`. Use it if you prefer a raw event trigger, or to
discover a button's id in **Developer Tools → Events**:

```yaml
automation:
  - alias: "Smart button arms alarm"
    triggers:
      - trigger: event
        event_type: wiser_by_feller_smart_button_event
        event_data:
          smart_button_id: 80
          event: click
    actions:
      - action: alarm_control_panel.alarm_arm_away
        target:
          entity_id: alarm_control_panel.home
```
