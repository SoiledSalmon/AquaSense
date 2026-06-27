# 2. MQTT Reconnect & Catch-Up Strategy

## Context
ThingSpeak MQTT broker (`mqtt3.thingspeak.com`) holds a persistent connection for real-time ingestion. However, network blips, server updates, or Railway service restarts can disconnect the client. During the disconnect window, the ESP32 device will continue sending data to ThingSpeak (via HTTP POST) which the backend will miss. We need a way to ensure connection resilience and zero data loss.

## Decision
1. **Exponential Backoff Reconnection:** We use an `aiomqtt.Client` block in a retry loop. On connection failure (`aiomqtt.MqttError`), we catch the exception and wait for a delay before retrying. The delay starts at 1 second and doubles after each failure up to a maximum of 60 seconds.
2. **REST API Catch-Up:** Upon any successful connection or reconnection, the backend will identify all active users (users with `channel_id`). For each user, it will query the database for the timestamp of their latest reading. If a timestamp is found, it will call the ThingSpeak REST API `GET /channels/{channel_id}/feeds.json?start={last_stored_timestamp}` to retrieve all readings published during the disconnect window.
3. **De-duplication:** To prevent duplicates, we skip any fetched feed item whose timestamp is less than or equal to the latest stored timestamp in the database.
4. **Dynamic Subscriptions:** A background loop polls the database every 60 seconds. If a new user signs up or configures a `channel_id`, the loop automatically triggers catch-up for that channel and subscribes to it without requiring a connection restart.

## Consequences
- **Robustness:** Network outages or server restarts will not cause data loss. The system automatically catches up with historical REST data once connection is restored.
- **Latency:** Real-time ingestion remains extremely low-latency (~1–3s) via MQTT, while recovery is handled asynchronously without blocking the server.
- **Performance:** REST API calls are only made on connection initialization/reconnection and when new users configure their channels, minimizing REST API rate-limiting issues on ThingSpeak.
- **Resource Usage:** Storing a local map of `subscribed_channels` and `channel_to_user_map` in memory prevents duplicate subscriptions.
