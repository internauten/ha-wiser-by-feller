# Smart Button (SMB) Integration

Die Smart Buttons (SMB) von Wiser by Feller fehlen in dieser Integration. Darum sollen diese hinzugefügt werden.

## SMB's holen

Request: GET /api/smartbuttons
Response:

```json
{
  "data": [
    {
      "id": 21,
      "job": 34,
      "device": "0000abed",
      "channel": 2
    },
    {
      "id": 24,
      "job": 34,
      "device": "0000abed",
      "channel": 3
    },
    {
      "id": 80,
      "job": 34,
      "device": "0000d012",
      "channel": 2
    }
  ],
  "status": "success"
}
```

## Status update by Websocket

OOB SMB's senden keine status aktualisierungen über die Websockets. Darum wird ein Script und ein Job erstellt der den SM's zugeordnet wird.

Das Script:
```python
import websockets
import uasyncio


async def ws_task(argv):
    await websockets.Connection.push_event('/api', {'smb': {'id': argv[2], 'action': argv[0], 'type': argv[1]}})


def onButtonEvent(*argv):
    loop = uasyncio.get_event_loop()
    loop.run_until_complete(ws_task(argv))
```

Dieses Script wird als Job alllen SMB's zugeordnet.

Dieser Job sendet folgendes an den Websocket:

```json
{
  'smb': {
    'id': 80,
    'action': 'press',
    'type': 'button'
  }
}

## Implementierung in Home Assistant Custom Component wiser_by_feller

Es soll als Event (Platform.EVENT) implementiert werden. Zudem gbt es im aiowiserbyfeller eine Klasse SmartButton. Die Implementierung soll sich annhand der anderen Entitäten wie z.B. light orientieren. Light implementiert die Loads vom Typ WiserOnOffEntity.



