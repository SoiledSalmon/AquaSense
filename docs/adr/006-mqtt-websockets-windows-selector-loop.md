# 6. MQTT WebSockets & Windows Event Loop Policy

## Context
1. **Network Firewalls/Blocked Ports:** The standard MQTT port (`1883`) and secure MQTT port (`8883`) are blocked by the developer's local network/ISP, preventing standard TCP MQTT client connections to `mqtt3.thingspeak.com`.
2. **Windows Event Loop Support:** On Windows, python-asyncio defaults to `ProactorEventLoop` starting with Python 3.8. However, `ProactorEventLoop` does not implement `add_reader` and `add_writer`, which the `aiomqtt` library (and the underlying `paho-mqtt` library) depends on for monitoring network sockets. This incompatibility raises `NotImplementedError` and causes MQTT connection tasks to hang or time out repeatedly.
3. **ThingSpeak Client Authentication:** ThingSpeak's MQTT broker requires the client ID (`identifier`) to match the generated username, otherwise connections are rejected.

## Decision
1. **Secure WebSockets (WSS):** Modify the MQTT client to use WebSockets transport (`transport="websockets"`) over port `443` with `websocket_path="/mqtt"` and a default SSL/TLS context. Since HTTPS (port `443`) is open and reachable on the network, this bypasses the port block while retaining secure, encrypted communications.
2. **Explicit Client ID:** Specify the `identifier` parameter in `aiomqtt.Client` with the value of `THINGSPEAK_MQTT_USER` to satisfy ThingSpeak's strict authentication constraints.
3. **Windows Selector Event Loop Policy:** Configure the application startup loop policy to `WindowsSelectorEventLoopPolicy` when running on Windows (`sys.platform == "win32"`). The `SelectorEventLoop` implements the socket monitoring methods required by `aiomqtt`.

## Consequences
- **Port Reachability:** The MQTT subscriber can connect successfully on local environments where ports `1883` and `8883` are blocked.
- **Windows Platform Compatibility:** The `NotImplementedError` raised by `aiomqtt` is resolved, allowing developers to develop and test the MQTT integration locally on Windows machines.
- **Production Performance:** The event loop policy change is conditionally applied only on Windows platforms (`win32`), meaning production Linux servers (running under Uvicorn/FastAPI with standard event loops or uvloop) remain unaffected and run with optimal performance.
