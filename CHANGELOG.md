# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-07-10

### Added
- Standardized open-source repository structure.
- Dynamic path resolution for `ml` modules and tests, allowing packages to run cleanly from root or backend.
- Generic licensing under the MIT License for AquaSense Contributors.
- Consolidated `docs/` containing standardized architecture, setup, and api references.
- Contributor Covenant Code of Conduct and Security Policy.
- Integrated background MQTT subscriber logic for ThingSpeak connectivity, delivering sub-second real-time telemetry updates.
- Real-time Server-Sent Events (SSE) data pipeline from backend to dashboard.
- Three-layer ML diagnosis pipeline (imputation + EWMA + XGBoost + Isolation Forest + exact SHAP values).
