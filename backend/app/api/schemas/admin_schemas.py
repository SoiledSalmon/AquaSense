"""Pydantic V2 models for Administrator Dashboard API request/response.

Enforces strict input validation and clean API contracts.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ── Request Models ────────────────────────────────────


class UserUpdateRoleRequest(BaseModel):
    """PATCH /api/admin/users/{user_id}/role body."""

    role: str = Field(
        ..., pattern="^(user|admin)$", description="Role must be 'user' or 'admin'"
    )


# ── Response Models ───────────────────────────────────


class AdminUserResponse(BaseModel):
    """User profile representation for administrators."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    full_name: Optional[str] = None
    role: str
    channel_id: Optional[str] = None
    ts_api_key: Optional[str] = None
    phone: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class PaginatedUsersResponse(BaseModel):
    """Paginated list of users."""

    users: List[AdminUserResponse]
    total_count: int
    page: int
    limit: int


class AdminReadingResponse(BaseModel):
    """Telemetry reading with optional user metadata."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    timestamp: datetime
    user_id: str
    user_email: Optional[str] = None
    ph: Optional[float] = None
    tds: Optional[float] = None
    turbidity: Optional[float] = None
    wqi_score: Optional[float] = None
    label: Optional[str] = None


class PaginatedReadingsResponse(BaseModel):
    """Paginated list of global telemetry readings."""

    readings: List[AdminReadingResponse]
    total_count: int
    page: int
    limit: int


class AdminAlertResponse(BaseModel):
    """Water quality alert with user context."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    timestamp: datetime
    user_id: str
    user_email: Optional[str] = None
    message: str
    severity: str
    category: str
    is_read: bool
    is_acknowledged: bool
    is_resolved: bool
    recommendation: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None


class PaginatedAlertsResponse(BaseModel):
    """Paginated list of global alerts."""

    alerts: List[AdminAlertResponse]
    total_count: int
    page: int
    limit: int


class AdminMLPredictionResponse(BaseModel):
    """Machine learning pipeline result."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    reading_id: Optional[str] = None
    user_id: str
    user_email: Optional[str] = None
    timestamp: datetime
    ph_smoothed: Optional[float] = None
    tds_smoothed: Optional[float] = None
    turb_smoothed: Optional[float] = None
    anomaly_score: Optional[float] = None
    is_anomaly: bool = False
    shap_ph: Optional[float] = None
    shap_tds: Optional[float] = None
    shap_turbidity: Optional[float] = None
    risk_level: Optional[str] = None
    recommendation: Optional[str] = None
    created_at: datetime


class PaginatedMLPredictionsResponse(BaseModel):
    """Paginated list of ML results."""

    predictions: List[AdminMLPredictionResponse]
    total_count: int
    page: int
    limit: int


class AlertFrequencyStats(BaseModel):
    """Stats tracking alerts over recent timeframes."""

    last_24h: int
    last_7d: int


class MLDistributionStats(BaseModel):
    """Aggregated prediction levels and anomaly occurrences."""

    anomaly_count: int
    normal_count: int
    low_risk: int
    medium_risk: int
    high_risk: int


class SystemStatusStats(BaseModel):
    """Connection and service heartbeat health states."""

    database: str
    mqtt_subscriber: str


class TrendDataPoint(BaseModel):
    """Daily time bucket data for trends."""

    date: str
    avg_wqi: Optional[float] = None
    readings_count: int


class AdminStatsResponse(BaseModel):
    """High-level system metrics and trends compiled for administrators."""

    active_users_count: int
    total_readings_count: int
    unsafe_events_count: int
    average_wqi: float
    alert_frequency: AlertFrequencyStats
    ml_prediction_distribution: MLDistributionStats
    system_status: SystemStatusStats
    trends: List[TrendDataPoint]
