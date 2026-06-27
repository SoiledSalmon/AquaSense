# AquaSense System Architecture & Diagrams

This document contains Mermaid diagrams visualizing the architecture, data ingestion pipelines, and ML processing flows for the AquaSense platform.

---

## 1. System Overview & Layered Architecture

AquaSense follows a strict layered architecture pattern as governed by the project constitution. No layer may cross over its immediate neighbors.

```mermaid
graph TD
    %% Frontend Layers
    subgraph Frontend [Next.js 15 Client - Vercel]
        style Frontend fill:#0f172a,stroke:#334155,color:#f8fafc
        UI[UI Components /components]
        Routes[Routes /app/routes]
        DataAPI[Data layer /lib/api]
    end

    %% Backend Layers
    subgraph Backend [FastAPI Backend - Railway]
        style Backend fill:#090d16,stroke:#1e293b,color:#f8fafc
        API[API Router /app/api]
        Services[Business Services /app/services]
        Ingestion[Ingestion Services /app/ingestion]
        ML[ML Pipeline /app/ml]
        Repos[Repositories /app/repositories]
    end

    %% External Infrastructure
    subgraph Infrastructure [Data & Auth Store]
        style Infrastructure fill:#022c22,stroke:#064e3b,color:#f8fafc
        SupaAuth[Supabase Auth]
        Timescale[(PostgreSQL + TimescaleDB)]
        TSBroker[ThingSpeak MQTT Broker]
    end

    %% Interactions
    Routes --> UI
    UI --> DataAPI
    DataAPI -- HTTPS / SSE --> API
    
    API --> Services
    Ingestion -- Async Handoff --> Services
    Services --> ML
    Services --> Repos
    Repos -- SQL Queries --> Timescale
    API -- JWT verification --> SupaAuth
    TSBroker -- MQTT Sub --> Ingestion
```

---

## 2. Real-Time Telemetry Ingestion Flow

Telemetry flows from the ESP32 to ThingSpeak, which propagates it via MQTT. The backend processes the message in real time and broadcasts it to client browsers over Server-Sent Events (SSE).

```mermaid
sequenceDiagram
    autonumber
    participant ESP as ESP32 Device
    participant TS as ThingSpeak Broker
    participant SUB as MQTT Subscriber (FastAPI)
    participant ML as ML Pipeline (FastAPI)
    participant DB as TimescaleDB
    participant SSE as SSE Manager (FastAPI)
    participant UI as Next.js Client Dashboard

    ESP->>TS: HTTP POST (ph, tds, turb)
    TS-->>SUB: MQTT Publish Message
    SUB->>SUB: Parse & Validate inputs
    SUB->>DB: Insert raw readings (telemetry)
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

## 3. Machine Learning Diagnosis Pipeline

AquaSense runs a structured 3-layer machine learning diagnostic pipeline on every incoming sensor reading.

```mermaid
flowchart TD
    %% Ingest
    Start([Raw Sensor Ingestion]) --> Preprocess[Layer 1: Input Validation & Imputation]
    
    %% Preprocessing
    Preprocess --> Impute{Has missing fields?}
    Impute -- Yes --> EWMA_Fill[Impute via historical average]
    Impute -- No --> Range_Check[Verify sensor range limits]
    
    %% Feature & WQI
    EWMA_Fill --> Range_Check
    Range_Check --> WQI_Score[Calculate WQI Score]
    Range_Check --> EWMA_Smooth[Layer 2: EWMA Feature Smoothing]
    
    %% Inferences
    EWMA_Smooth --> ML_Engine[Layer 3: Advanced Inference Engine]
    
    subgraph Inference_Layer [Inference Engine]
        style Inference_Layer fill:#0f172a,stroke:#334155,color:#fff
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
