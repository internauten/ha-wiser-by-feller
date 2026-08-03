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
creates one event entity named after the button's id, e.g.
`event.living_room_dimmer_smart_button_80`. The id is unique across the whole
installation, so buttons stay distinguishable even when several devices share
the same name — which is common for scene switches.

| Attribute | Description |
|---|---|
| `event_type` | `press` — plus `click` and `release`, declared but unused (see below) |
| `type` | Interaction kind reported by the gateway script, currently always `button` |

> [!IMPORTANT]
> Wiser currently reports a single action and a single type: `press` and
> `button`. Every press — short or long — arrives as `press`, so you cannot
> distinguish a tap from a hold. The entity also declares `click` and `release`
> for forward compatibility, but no Wiser system emits them today. Match on
> `press` in your automations.

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

### Steps to create the script on the µGateway

1. Open the µGateway in your browser.
2. Go to **Scripts** and create a new file.
3. Name it `ws_smb.py`.
4. Paste the Python script above into it and save.
5. Link it to every smart button you want to use.

## Example automation

```yaml
automation:
  - alias: "Smart button toggles lamp"
    triggers:
      - trigger: state
        entity_id: event.living_room_dimmer_smart_button_80
        attribute: event_type
        to: press
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
          event: press
    actions:
      - action: alarm_control_panel.alarm_arm_away
        target:
          entity_id: alarm_control_panel.home
```

## Appendix: duplicate WebSocket messages

While testing smart buttons we found that the integration processed **every**
WebSocket message twice — smart button presses as well as load state updates.
The cause is unrelated to smart buttons; they only made it visible, because a
button press is a discrete event that is easy to count.

### Diagnosis

A second WebSocket client connected to the µGateway independently of Home
Assistant received each press exactly once, while the Home Assistant log showed
two entries a millisecond apart:

```
18:55:10 >>> SMB {"smb": {"action": "press", "type": "button", "id": "80"}}   ← gateway sent once

18:55:10.977 DEBUG ... Websocket smart button event received: {...'id': '80'}  ← HA processed twice
18:55:10.978 DEBUG ... Websocket smart button event received: {...'id': '80'}
```

So the gateway was not at fault. `netstat` inside the Home Assistant container
confirmed **two** established connections to the µGateway.

### Root cause

The config entry had been set up twice within one Home Assistant run. Each setup
calls `ws_init()`, which calls `Websocket.init()` in aiowiserbyfeller, which
spawns an independent `asyncio` task that reconnects on its own.

The first task is never stopped, because `Websocket.async_close()` cannot close
anything: `connect()` never assigns the connection it opens to `self._ws`, so
the attribute stays `None` and the close is a no-op:

```python
# aiowiserbyfeller/websocket/websocket.py
async def async_close(self) -> None:
    if self._ws is not None:   # always None — connect() never sets it
        await self._ws.close()
```

Two live tasks, one gateway message, two callback invocations.

### The fix

Since the flaw is in the library, the coordinator guards against triggering it.
Two flags in [coordinator.py](../custom_components/wiser_by_feller/coordinator.py):

- **`_ws_started`** makes `ws_init()` idempotent — a repeat call logs and
  returns instead of spawning a second task. `ws_close()` clears the flag so a
  deliberate reconnect still works.
- **`_ws_subscribed`** guards the message handler registration.
  `Websocket.subscribe()` appends unconditionally, so re-subscribing on every
  reconnect would reintroduce the duplication through the back door.

The reconnect path in `_async_update_data()` now goes through `ws_init()` rather
than calling `Websocket.init()` directly, so it passes the same guard.

Verified live: one connection instead of two, and each press processed exactly
once.

> [!NOTE]
> The underlying library bug still exists. This integration works around it, but
> `Websocket.async_close()` remains a no-op for any other consumer.
