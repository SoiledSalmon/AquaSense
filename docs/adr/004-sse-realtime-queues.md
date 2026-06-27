# 4. Server-Sent Events (SSE) Real-Time Streaming & Per-User Queues

## Context
In Phase 3 of AquaSense, we need to push real-time telemetry updates and anomaly alerts directly from the backend to the browser client immediately upon receiving them from the ThingSpeak MQTT broker. The original dashboard in v1 HTTP polled the API every 15–30 seconds. We need a unidirectional, real-time push mechanism that is highly efficient, scales easily, and plays nicely with the Next.js 15 frontend architecture.

## Decision
1. **Server-Sent Events (SSE) over WebSockets:** We choose Server-Sent Events (SSE) using FastAPI's `StreamingResponse` set to `media_type="text/event-stream"`. WebSockets are bi-directional and heavier; because the water quality telemetry flow is strictly server-to-client, SSE is a perfect fit. It runs over standard HTTP/2 (making it proxy and firewall-friendly) and features native browser reconnection support out of the box via the `EventSource` API.
2. **Per-User Async Queues with Multitab Support:** To support multiple concurrent connections for a single user (e.g., if a user has multiple browser tabs open), we introduce an `SSEManager` service. 
   - The manager maintains a map: `_user_queues: Dict[str, Set[asyncio.Queue]]` where `user_id` is the key.
   - When a client connects to `/api/stream`, a new `asyncio.Queue` is instantiated and registered for that `user_id`.
   - When the MQTT subscriber ingests and processes a reading, it broadcasts the update to *all* active queues registered for that user.
   - When the connection terminates (tab closed, page refreshed), the queue is unregistered and cleaned up to prevent memory leaks.
3. **Heartbeat and Keep-Alive:** To prevent load balancers, reverse proxies (like Nginx), or hosting platforms (like Railway) from closing idle connections, the event generator yields a keep-alive `heartbeat` event every 30 seconds if no telemetry update is processed.
4. **Transparent Auth and cookie flow**: EventSource utilizes the browser's native cookie handling. With `withCredentials` enabled on the client side, HTTP-only JWT cookies (`access_token` and `refresh_token`) are automatically forwarded to `/api/stream`, maintaining authentication parity with REST endpoints.

## Consequences
- **Minimal Latency:** Ingested sensor data is pushed to the client immediately (~1–3s from ESP32 upload to browser render), removing the 15s polling delay.
- **Resource Efficiency:** The backend avoids constant database polling load. The connection remains idle, only taking up a tiny memory footprint for the queue and connection handle.
- **Resilience:** The client UI automatically transitions state to "Reconnecting" if the network drops and re-establishes the stream once connection is recovered.
- **Stateless Scaling Limitation:** In-memory queue mappings mean that if the backend scales horizontally (multiple server instances), a client connected to Server A won't receive updates ingested by Server B. Since AquaSense is currently hosted on a single container instance on Railway, this is accepted; if horizontal scaling becomes necessary in the future, we will transition `SSEManager` to a Redis Pub/Sub backend.
