# AquaSense System Architecture

This document describes the architectural design, system layers, data flows, and technical decisions of the AquaSense IoT Water Quality Monitoring platform.

---

## 1. 5-Layer IoT Architecture

AquaSense is structured around a standard 5-layer IoT model to decouple concerns and ensure scalability from sensor nodes up to the web dashboard.

```mermaid
graph TD
    %% Perception
    subgraph Perception [1. Perception Layer]
        Sensors[Physical Sensors: pH, TDS, Turbidity] --> ESP32[ESP32 Microcontroller]
    end

    %% Connectivity
    subgraph Connectivity [2. Connectivity Layer]
        ESP32 -->|HTTP POST| TS[ThingSpeak Channel]
    end

    %% Ingestion
    subgraph Ingestion [3. Ingestion Layer]
        TS -->|WebSockets MQTT| Client[aiomqtt Client]
        Client -->|Parse & Validate| IngestService[FastAPI Ingestion]
    end

    %% Storage & ML
    subgraph StorageML [4. Storage & Processing Layer]
        IngestService -->|Write Raw Telemetry| DB[(PostgreSQL Database)]
        IngestService -->|Run ML Inference| MLPipeline[3-Layer ML Pipeline]
        MLPipeline -->|Write Predictions & Alerts| DB
    end

    %% Application
    subgraph Application [5. Application Layer]
        IngestService -->|Broadcast SSE| SSE[SSE Manager]
        SSE -->|Real-time streams| Dashboard[Next.js Client Dashboard]
        DB -->|Materialized aggregates| API[FastAPI HTTP Endpoints]
        API -->|Fetch historical data| Dashboard
    end
```

### 1.1 Ingestion Layer Design (MQTT WebSocket Subscriber)
Telemetry values read by the ESP32 firmware are posted to ThingSpeak via HTTP POST. Rather than long-polling ThingSpeak's REST API from the application backend (which introduces polling overhead and latency), the FastAPI backend maintains a persistent WebSocket connection to the ThingSpeak MQTT Broker (`mqtt3.thingspeak.com`).
*   **Latency:** Propagation latency drops from ~60 seconds to ~1–3 seconds.
*   **Connection Resilience:** The backend uses an always-on hosting context that keeps the TCP/WebSocket subscriber loop active. Reconnection mechanisms with exponential backoff and REST API catch-up queries are implemented to handle transient network drops.

### 1.2 Storage Layer Design (TimescaleDB / Partitioned Relational fallback)
Sensor readings are partitioned and indexed chronologically. To improve query performance for charts (24h/7d/30d views), the database pre-computes hourly and daily metrics using PostgreSQL Materialized Views.
*   **Query Performance:** Chronological queries read directly from views instead of scanning raw telemetry rows.
*   **pg_cron Aggregation:** Views are concurrently refreshed on a set schedule (`pg_cron`) in production.

---

## 2. Ingestion Sequence

The diagram below traces telemetry from the physical hardware through ingestion, storage, ML pipeline evaluation, and live Server-Sent Events (SSE) broadcast to browser clients.

```mermaid
sequenceDiagram
    autonumber
    participant ESP as ESP32 Device
    participant TS as ThingSpeak Broker
    participant SUB as MQTT Subscriber (FastAPI)
    participant ML as ML Pipeline
    participant DB as PostgreSQL
    participant SSE as SSE Manager (FastAPI)
    participant UI as Next.js Client Dashboard

    ESP->>TS: HTTP POST (ph, tds, turb)
    TS-->>SUB: MQTT Publish Message
    SUB->>SUB: Parse & Validate inputs
    SUB->>DB: Insert raw readings
    SUB->>ML: Pass telemetry row for ML analysis
    activate ML
    ML->>ML: Run Imputation & WQI Scoring
    ML->>ML: Run EWMA features calculation
    ML->>ML: Run XGBoost classification & SHAP explainer
    ML->>ML: Run Isolation Forest anomaly detection
    ML->>DB: Insert detailed ML prediction results
    ML->>DB: Create & Persist Alert (if thresholds violated)
    ML-->>SUB: Return processed metrics + alert status
    deactivate ML
    SUB->>SSE: Broadcast reading & alert payload
    SSE->>UI: SSE push (reading_update / alert_new)
```

---

## 3. Machine Learning Processing Pipeline

Every incoming reading undergoes three processing stages:

```mermaid
flowchart TD
    %% Ingest
    Start([Raw Sensor Ingestion]) --> Preprocess[Stage 1: Input Validation & Imputation]
    
    %% Preprocessing
    Preprocess --> Impute{Has missing fields?}
    Impute -- Yes --> EWMA_Fill[Impute via historical average]
    Impute -- No --> Range_Check[Verify sensor range limits]
    
    %% Feature & WQI
    EWMA_Fill --> Range_Check
    Range_Check --> WQI_Score[Calculate WQI Score]
    Range_Check --> EWMA_Smooth[Stage 2: EWMA Feature Smoothing]
    
    %% Inferences
    EWMA_Smooth --> ML_Engine[Stage 3: Inference Engine]
    
    subgraph Inference_Engine [Inference Engine]
        style Inference_Engine fill:#0f172a,stroke:#334155,color:#fff
        XGB[XGBoost Classifier]
        SHAP[Exact pure-Python SHAP Explainer]
        IForest[Isolation Forest Outlier Detector]
    end
    
    ML_Engine --> XGB
    ML_Engine --> IForest
    
    XGB --> Label[Predict safety status: Safe, Borderline, Unsafe]
    Label --> SHAP
    SHAP --> Contribution[Extract feature contribution weights]
    
    IForest --> Score[Generate anomaly decision score]
    Score --> Anomaly{Is Outlier?}
    
    %% Results
    Contribution --> Alert_Rules[Evaluate Alerting Rule Engine]
    Anomaly -- Yes --> Alert_Rules
    
    Alert_Rules --> Alert_Create{Contaminant limit violated?}
    Alert_Create -- Yes --> DB_Alert[Persist Alert & Broadcast to SSE]
    Alert_Create -- No --> DB_ML[Persist ML results & Update Reading]
    DB_Alert --> Done([Telemetry Processing Complete])
    DB_ML --> Done
```

1.  **Validation & Imputation:** Checks incoming fields against physical bounds (e.g., pH between 0 and 14). Missing or out-of-bounds metrics are filled using a historical running average.
2.  **Smoothing & WQI Calculation:** Computes a Water Quality Index (WQI) score and applies Exponentially Weighted Moving Average (EWMA) smoothing to reduce noise and sensor drift.
3.  **Inference:**
    *   **XGBoost Classifier:** Predicts the safety status (`Safe`, `Borderline`, `Unsafe`).
    *   **SHAP Explainer:** A custom, pure-Python tree explainer computes mathematically exact feature contributions to explain why a status was predicted.
    *   **Isolation Forest:** Detects multidimensional anomalies to flag potential sensor failure or sudden contamination.
