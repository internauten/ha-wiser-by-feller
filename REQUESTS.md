Hier ist die kompakte Tabelle mit Endpoint, Methode, Auslöser und Codepfad.

| Endpoint am µGateway | Methode | Auslöser in Home Assistant | Codepfad im Repo |
|---|---|---|---|
| /api/account/claim | POST | Einrichtung/Reauth (Token anfordern) | config_flow.py |
| /api/info | GET | Einrichtung, DHCP/Zeroconf-Validierung, Reauth | config_flow.py |
| /api/site | GET | Einrichtung (Anzeigename/Site lesen) | config_flow.py |
| /api/info/debug | GET | Regelmäßiges Polling (Gateway-Info) | coordinator.py |
| /api/loads | GET | Initiale Geräteliste/Loads laden | coordinator.py |
| /api/loads/state | GET | Regelmäßiges Status-Polling | coordinator.py |
| /api/smartbuttons | GET | Initial + Status-Polling Smart Buttons | coordinator.py |
| /api/rooms | GET | Initiales Laden von Räumen | coordinator.py |
| /api/devices/* | GET | Initiales Laden detaillierter Geräteinfos | coordinator.py |
| /api/jobs | GET | Initiales Laden von Jobs | coordinator.py |
| /api/scenes | GET | Initiales Laden von Szenen | coordinator.py |
| /api/system/flags | GET | Initial + Polling von System-Flags | coordinator.py |
| /api/system/health | GET | Regelmäßiges Polling (Health) | coordinator.py |
| /api/sensors | GET | Polling Sensoren (Gen B) | coordinator.py |
| /api/hvacgroups | GET | Initiales Laden HVAC-Gruppen (Gen B) | coordinator.py |
| /api/hvacgroups/state | GET | Polling HVAC-Status (Gen B) | coordinator.py |
| /api/loads/{id}/ctrl | PUT | Licht/Schalter ein/aus, Impuls-Button, Motor-Stop | light.py, button.py, cover.py |
| /api/loads/{id}/target_state | PUT | Dimmen, Farbtemperatur/RGBW, Cover-Position/Tilt, HVAC-nahe Load-Steuerung | light.py, cover.py |
| /api/loads/{id}/state | GET | Cover-Tracking bei Bewegung | cover.py |
| /api/loads/{id}/ping | PUT | Identify/Ping von Loads | button.py |
| /api/devices/{id}/ping | GET | Identify/Ping von Geräten/Thermostat | button.py, coordinator.py |
| /api/devices/{id}/config | GET | Service status_light: Konfig holen | coordinator.py |
| /api/devices/config/{config_id}/inputs/{channel} | PATCH | Service status_light: LED/Input-Konfig setzen | coordinator.py |
| /api/devices/config/{config_id} | PUT | Service status_light: Konfig anwenden | coordinator.py |
| /api/hvacgroups/{id}/target_state | PUT | Klima: Ein/Aus, Zieltemperatur setzen | climate.py |
| /api/system/flags/{id} | PATCH | System-Flag Switch ein/aus/toggle | switch.py |
| /api/jobs/{id}/trigger | GET | Szene aktivieren | scene.py |
| ws://{host}/api | WebSocket | Push-Events für load, sensor, hvacgroup, smb, westgroup | coordinator.py |
| DHCP + Zeroconf Discovery im LAN | Discovery | Automatische Gateway-Erkennung | manifest.json, config_flow.py |

Hinweis:
Die konkreten REST-Pfade werden über die Abhängigkeit aiowiserbyfeller aufgebaut; in dieser Integration sieht man die Aufrufe über Methoden wie async_get_..., async_set_... und Entity-Aktionen. Externe Internet-Ziele sind im Integrationscode nicht erkennbar, alles geht lokal gegen das Wiser-Gateway im eigenen Netz.