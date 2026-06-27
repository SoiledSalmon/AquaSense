# AquaSense — IoT Water Quality Monitoring & ML Diagnostics

AquaSense is an end-to-end IoT platform for real-time water quality tracking, statistical anomaly detection, and predictive safety analysis. It integrates ESP32 microcontrollers, ThingSpeak MQTT brokers, a FastAPI backend orchestrating a 3-layer machine learning pipeline, and a Next.js 15 dashboard streaming live metrics over Server-Sent Events (SSE).

---

## 🚀 Key Features

*   **Real-Time Data Streaming:** High-frequency ingestion of pH, Total Dissolved Solids (TDS), and Turbidity pushed instantly to frontend clients over Server-Sent Events (SSE).
*   **Predictive Diagnostics:** XGBoost classifier evaluates telemetry in real time, predicting safety status (`Safe`, `Borderline`, `Unsafe`) and generating mathematically exact SHAP contribution metrics.
*   **Statistical Anomalies:** Isolation Forest outlier detection on EWMA-smoothed parameters identifies sensor drift, device errors, or filtration failures.
*   **Contaminant Alert Engine:** Evaluates metrics against dynamic rules, issuing warning notifications and user-specific actionable safety recommendations.
*   **Unified Auth & Role Control:** Secure Supabase Auth proxied through FastAPI with HttpOnly session cookies. Role-Based Access Control (RBAC) allows administrators to manage users and system metrics.

---

## 🛠 Tech Stack

*   **Backend:** FastAPI, `aiomqtt` (MQTT Client), `structlog` (Structured Logging), `slowapi` (Rate Limiting), Pydantic v2 (Validation), `jose` (JWT parsing).
*   **Machine Learning:** XGBoost, Scikit-learn (Isolation Forest), Pandas, NumPy, Joblib, Custom Pure-Python Exact SHAP Explainer.
*   **Frontend:** Next.js 16/15 (App Router), Tailwind CSS v4, Lucide Icons, Recharts (Telemetry Analytics).
*   **Database:** Supabase PostgreSQL 15, TimescaleDB (Hypertables, Continuous Aggregates).
*   **IoT Firmware:** Arduino/C++ for ESP32, WiFi client, ThingSpeak HTTP Post.

---

## 📂 Project Structure

```
AquaSense/
├── .agents/                    # Workspace configuration & engineering workflows
├── Firmware/
│   └── AquaSense/
│       └── AquaSense.ino      # ESP32 C++ firmware (Wi-Fi, sensor sampling, ThingSpeak client)
├── backend/
│   ├── app/
│   │   ├── api/               # FastAPI routers & request/response validation schemas
│   │   ├── core/              # Config, exceptions, dependencies, logging, auth helpers
│   │   ├── ml/                # XGBoost + SHAP + Isolation Forest pipeline
│   │   ├── repositories/      # Supabase/PostgreSQL parameterized database access queries
│   │   ├── services/          # WQI scoring, alerts engine, SSE queues, ML orchestrator
│   │   └── main.py            # FastAPI entry point & lifespan manager
│   ├── migrations/            # Consolidated SQL schemas
│   │   ├── relational/        # Users, alerts, and Relational tables
│   │   └── timescaledb/       # Telemetry Hypertables & Continuous Aggregates
│   ├── tests/                 # Full unit & integration pytest suite
│   ├── requirements.txt       # Python dependencies
│   └── .env.example           # Backend environment template
├── frontend/
│   ├── app/                   # Next.js Routes, Layouts, and Page compositions
│   ├── components/            # Auth forms, live telemetry, and admin dashboards
│   ├── lib/                   # Supabase client context & API proxy wrappers
│   ├── package.json           # Node dependencies
│   └── .env.example           # Frontend environment template
├── docs/
│   ├── adr/                   # Architecture Decision Records (001-005)
│   ├── diagrams/              # Mermaid Architecture & Ingestion Flow diagrams
│   ├── api.md                 # Detailed API Endpoint Reference
│   └── deployment_guide.md    # Production deployment and operations playbook
└── README.md                  # Handover developer guide
```

---

## ⚙️ Local Development Setup

### 📋 Prerequisites
*   Python `3.12` to `3.14`
*   Node.js `18.x` or `20.x`
*   C++ Compiler / Arduino IDE (for ESP32 hardware compilation only)

---

### 1. Database & Authentication Setup
AquaSense relies on Supabase (Postgres 15) and the TimescaleDB extension.

1.  Create a project on the [Supabase Dashboard](https://supabase.com). Ensure you select **PostgreSQL 15** (TimescaleDB extension is not supported by Supabase on PostgreSQL 16+).
2.  Open the Supabase SQL Editor and execute the SQL migrations in order:
    *   **Relational Schema:** Run the scripts in [backend/migrations/relational/](file:///D:/Coding%20Projects/College%20Era/AquaSense/backend/migrations/relational/) sequentially.
    *   **TimescaleDB Schema:** Run the scripts in [backend/migrations/timescaledb/](file:///D:/Coding%20Projects/College%20Era/AquaSense/backend/migrations/timescaledb/) sequentially.
3.  Note down the project **URL**, **Anon API key**, **Service Role API key**, and **JWT Secret**.

---

### 2. Backend Local Run
1.  Navigate to the backend folder:
    ```bash
    cd backend
    ```
2.  Create and activate a virtual environment:
    ```bash
    python -m venv .venv
    # Windows:
    .venv\Scripts\activate
    # macOS/Linux:
    source .venv/bin/activate
    ```
3.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
4.  Configure the environment variables:
    *   Copy `.env.example` to `.env`
    *   Fill in credentials captured during the Supabase setup.
5.  Start the FastAPI development server:
    ```bash
    uvicorn app.main:app --reload
    ```
    *The background MQTT subscriber will start automatically at startup. If the ThingSpeak broker is unreachable, it will trigger exponential backoff reconnect loops.*
6.  Run the pytest test suite:
    ```bash
    pytest
    ```

---

### 3. Frontend Local Run
1.  Navigate to the frontend folder:
    ```bash
    cd frontend
    ```
2.  Install dependencies:
    ```bash
    npm install
    ```
3.  Configure the environment variables:
    *   Copy `.env.example` to `.env.local`
    *   Ensure `NEXT_PUBLIC_API_URL` points to the local backend (usually `http://localhost:8000`).
4.  Launch the Next.js development server:
    ```bash
    npm run dev
    ```
5.  Access the client dashboard at `http://localhost:3000`.

---

### 4. IoT Firmware Setup
1.  Install the **Arduino IDE** and configure the esp32 board manager.
2.  Open [Firmware/AquaSense/AquaSense.ino](file:///D:/Coding%20Projects/College%20Era/AquaSense/Firmware/AquaSense/AquaSense.ino).
3.  Update the Wi-Fi credentials (`ssid`, `password`) and the ThingSpeak Channel ID & Write API Key.
4.  Wire your analog pH, TDS, and Turbidity probes to the ESP32 GPIO pins matching the code configuration.
5.  Compile and upload the firmware.

---

## 📘 Documentation & Reference Links

*   **Architecture & Flowcharts:** Refer to [docs/diagrams/architecture.md](file:///D:/Coding%20Projects/College%20Era/AquaSense/docs/diagrams/architecture.md) for sequence/layered Mermaid diagrams.
*   **API reference:** Endpoints, request/response models, query validation parameters are documented in [docs/api.md](file:///D:/Coding%20Projects/College%20Era/AquaSense/docs/api.md).
*   **Production Deployment:** Step-by-step instructions for deploying to Vercel, Railway, and Supabase are detailed in [docs/deployment_guide.md](file:///D:/Coding%20Projects/College%20Era/AquaSense/docs/deployment_guide.md).
*   **Technical Decisions:** Key engineering choices are documented in [docs/adr/](file:///D:/Coding%20Projects/College%20Era/AquaSense/docs/adr/).