# 7. Async Event Loop Blocking Fix

## Context
The backend logs showed a persistent disconnect loop in the ThingSpeak MQTT subscriber:
```
mqtt_connected
mqtt_connection_error error="Disconnected during message iteration" retry_in=1.0
```
This loop recurred every 2-5 seconds. The root cause was event-loop blocking inside the single-threaded asyncio event loop:
1. The Supabase sync client (`create_client`) was being called inside `async def` functions, causing synchronous socket network calls to freeze the event loop.
2. In the ML pipeline service, CPU-bound tasks like XGBoost model inference, Isolation Forest anomaly detection, and pure-Python exact SHAP calculations were executed synchronously, locking the thread and preventing aiomqtt from responding to broker pings.

## Decision
1. **Transition to Async Supabase Client:** Initialize `supabase` and `supabase_admin` using `create_async_client` instead of `create_client` in `main.py`. This ensures that all database CRUD queries and authentication operations are cooperative and non-blocking.
2. **Await DB Queries and Auth Calls:** Update all repositories and service layers to prefix `.execute()` and `.auth` method calls with `await`.
3. **Offload ML Inference to Thread Pool:** Wrap the CPU-bound ML pipeline functions (`run_xgb_inference`, `detect_anomaly`, and `compute_exact_shap`) with `asyncio.to_thread`. This moves computational overhead onto Python's default thread pool executor, leaving the main event loop thread free for network I/O.
4. **Update Tests:** Adapt existing test mocks and fixtures to handle the asynchronous Supabase client and auth APIs correctly.

## Consequences
- **Loop Health:** The cooperative event loop is no longer blocked. `aiomqtt` connection reads and keepalive/ping-pong exchanges complete in a timely manner, eliminating the subscriber disconnect loop.
- **Resource Offloading:** CPU-heavy ML calculations run on separate thread pool threads. Since the database operations are async, they do not compete for these thread pool worker threads, avoiding thread pool exhaustion.
- **Unified Style:** The database client is fully async throughout the backend APIs and services, promoting codebase consistency.
