# AquaSense REST & SSE API Reference

This document serves as the definitive API reference for the AquaSense IoT Water Quality Monitoring system, generated directly from the live OpenAPI 3.1.0 schema definition.

---

## Base Path & Security

*   **Production API URL:** `https://aquasense-api.railway.app/api`
*   **Local Development API URL:** `http://localhost:8000/api`
*   **Authentication Flow:** All secure endpoints are guarded by JWT tokens. These are stored and passed automatically in **httpOnly** cookies (`access_token` and `refresh_token`), preventing client-side scripts from reading tokens.
*   **CORS Policy:** Allowed origins are loaded from `FRONTEND_URL` environment setting (defaults to `http://localhost:3000` with local development fallback routes).

---

## 1. Authentication Router (`/api/auth`)

Endpoints for user registration, session management, profile configuration, and credentials verification.

### **POST** `/api/auth/signup`
Creates a new user profile in the database and registers credentials in Supabase Auth.
*   **Request Body:** `application/json`
    ```json
    {
      "email": "user@example.com",
      "password": "strong-password-min-8-chars",
      "full_name": "John Doe"
    }
    ```
*   **Responses:**
    *   `201 Created`: Account successfully registered.
    *   `400 Bad Request`: Email already in use or password too weak.

### **POST** `/api/auth/login`
Exchanges user credentials for access/refresh tokens. Sets `access_token` (15-min expiry) and `refresh_token` (7-day expiry) HTTP-only cookies in response.
*   **Request Body:** `application/json`
    ```json
    {
      "email": "user@example.com",
      "password": "your-password"
    }
    ```
*   **Responses:**
    *   `200 OK`: Successful login.
    *   `401 Unauthorized`: Invalid credentials.

### **POST** `/api/auth/logout`
Clears HTTP-only session cookies (`access_token` and `refresh_token`).
*   **Responses:**
    *   `200 OK`: Session cleared.

### **GET** `/api/auth/me`
Retrieves authentication profile details of the current logged-in session.
*   **Security:** Requires valid session cookies.
*   **Responses:**
    *   `200 OK`:
        ```json
        {
          "id": "user-uuid",
          "email": "user@example.com",
          "full_name": "John Doe",
          "role": "user",
          "channel_id": "thingspeak-channel-id",
          "phone_number": "+1234567890",
          "created_at": "2026-06-26T12:00:00Z"
        }
        ```
    *   `401 Unauthorized`: Missing or invalid session.

### **PATCH** `/api/auth/profile`
Updates current user's profile metadata and external channel settings.
*   **Security:** Requires valid session cookies.
*   **Request Body:** `application/json`
    ```json
    {
      "full_name": "John Smith",
      "phone_number": "+9876543210",
      "channel_id": "thingspeak-channel-id-str",
      "ts_api_key": "thingspeak-read-api-key"
    }
    ```
*   **Responses:**
    *   `200 OK`: Profile updated successfully.

---

## 2. Readings & Telemetry Router (`/api/readings`)

Access to raw telemetry stream, latest water quality indices, and historical continuous aggregations.

### **GET** `/api/readings/latest`
Gets the single most recent sensor telemetry data.
*   **Security:** Requires valid session cookies.
*   **Responses:**
    *   `200 OK`:
        ```json
        {
          "reading": {
            "id": "reading-uuid",
            "timestamp": "2026-06-27T06:50:00Z",
            "ph": 7.42,
            "tds": 180.5,
            "turbidity": 1.25,
            "wqi_score": 92.4,
            "label": "safe"
          }
        }
        ```

### **GET** `/api/readings`
Gets pre-aggregated, continuous time-series history for the user's sensor.
*   **Security:** Requires valid session cookies.
*   **Query Parameters:**
    *   `range`: String (supported values: `24h`, `7d`, `30d`). Defauts to `24h`.
*   **Responses:**
    *   `200 OK`:
        ```json
        {
          "range": "24h",
          "data": [
            {
              "bucket": "2026-06-27T01:00:00Z",
              "ph_avg": 7.2,
              "tds_avg": 175.0,
              "turb_avg": 1.1,
              "wqi_avg": 94.0
            }
          ]
        }
        ```

### **GET** `/api/stream` (SSE Stream)
Establishes a persistent Server-Sent Events (SSE) unidirectional flow to stream telemetry and alerts to the client browser in real time.
*   **Security:** Requires valid session cookies (`withCredentials = true` in EventSource setup).
*   **Response Content-Type:** `text/event-stream`
*   **Event Types:**
    *   `reading_update`: Dispatched when a new telemetry reading is ingested and processed by ML.
        *   *Data payload:* Telemetry reading row + ML diagnostics (SHAP, anomaly predictions).
    *   `alert_new`: Dispatched when a newly generated alert rule is violated.
        *   *Data payload:* Alert description, category, and recommendation.
    *   `heartbeat`: Blank keep-alive event sent every 30 seconds to prevent proxy connection timeout.

---

## 3. Alerts & Warnings Router (`/api/alerts`)

Endpoints to fetch, acknowledge, and resolve alerts generated by the rule engine.

### **GET** `/api/alerts`
Fetches a list of warnings for the user, ordered by timestamp (newest first).
*   **Security:** Requires valid session cookies.
*   **Query Parameters:**
    *   `status`: String (choices: `unread`, `unacknowledged`, `resolved`, `active`, `all`). Defaults to `unacknowledged`.
    *   `limit`: Integer (min 1, max 100). Defaults to 50.
*   **Responses:**
    *   `200 OK`: Returns alerts array matching query filters.

### **POST** `/api/alerts/{alert_id}/acknowledge`
Acknowledge an active alert notification.
*   **Security:** Requires valid session cookies. Checks ownership of the alert.
*   **Responses:**
    *   `200 OK`: Acknowledged successfully. Mark as read.

### **POST** `/api/alerts/{alert_id}/resolve`
Resolve an alert notification manually (alerts are normally resolved automatically when telemetry values return to normal).
*   **Security:** Requires valid session cookies. Checks ownership of the alert.
*   **Responses:**
    *   `200 OK`: Resolved successfully.

### **POST** `/api/alerts/{alert_id}/read`
Mark a warning notification as read without acknowledging its severity warning.
*   **Security:** Requires valid session cookies.
*   **Responses:**
    *   `200 OK`: Marked read successfully.

---

## 4. Admin Router (`/api/admin`)

Endpoints restricted to users with `admin` role in their app_metadata claims.

### **GET** `/api/admin/users`
Lists registered users.
*   **Security:** Requires `admin` privilege.
*   **Query Parameters:**
    *   `role`: choices `all`, `admin`, `user`. Defaults to `all`.
    *   `search`: search terms matching name or email.
*   **Responses:**
    *   `200 OK`: Array of users profiles.

### **PATCH** `/api/admin/users/{user_id}/role`
Updates a user's role to `admin` or `user` across both App Metadata (auth) and database profiles.
*   **Security:** Requires `admin` privilege.
*   **Request Body:**
    ```json
    {
      "role": "admin"
    }
    ```
*   **Responses:**
    *   `200 OK`: Role updated.

### **GET** `/api/admin/system-stats`
Retrieves system liveness statistics and daemon execution checks.
*   **Security:** Requires `admin` privilege.
*   **Responses:**
    *   `200 OK`:
        ```json
        {
          "users_count": 42,
          "readings_count": 48392,
          "active_streams": 3,
          "background_status": {
            "mqtt_subscriber": "connected",
            "model_xgb": "loaded",
            "model_iforest": "loaded"
          }
        }
        ```

### **POST** `/api/admin/ml/retrain`
Forces retraining of XGBoost and Isolation Forest models on the latest telemetry dataset.
*   **Security:** Requires `admin` privilege.
*   **Responses:**
    *   `200 OK`:
        ```json
        {
          "success": true,
          "message": "Models retrained successfully",
          "xgb_model_path": ".../xgboost_model.json",
          "iforest_model_path": ".../isolation_forest.joblib"
        }
        ```
