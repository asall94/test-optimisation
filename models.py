"""
Data models for infrastructure monitoring agent.
Defines input/output schemas with strict validation.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Literal
from datetime import datetime


class ServiceStatus(BaseModel):
    """Service health status."""
    database: str
    api_gateway: str
    cache: str


class InputData(BaseModel):
    """Single monitoring snapshot from infrastructure."""
    timestamp: str
    cpu_usage: float
    memory_usage: float
    latency_ms: float
    disk_usage: float
    network_in_kbps: float
    network_out_kbps: float
    io_wait: float
    thread_count: int
    active_connections: int
    error_rate: float
    uptime_seconds: int
    temperature_celsius: float
    power_consumption_watts: float
    service_status: ServiceStatus


class Insights(BaseModel):
    """Aggregated metrics insights."""
    average_latency_ms: float
    max_cpu_usage: float
    max_memory_usage: float
    error_rate: float
    uptime_seconds: int


class Anomaly(BaseModel):
    """Detected infrastructure anomaly."""
    metric: str
    value: float
    threshold: float
    severity: Literal["low", "medium", "high"]
    description: str


class Recommendation(BaseModel):
    """Action recommendation for optimization."""
    id: str
    action: str
    target: str
    parameters: Dict
    benefit_estimate: str


class ServiceStatusSummary(BaseModel):
    """Summary of service health across all snapshots."""
    online: List[str]
    degraded: List[str]
    offline: List[str]


class OutputData(BaseModel):
    """Final analysis output schema."""
    timestamp: str
    insights: Insights
    anomalies: List[Anomaly]
    recommendations: List[Recommendation]
    service_status_summary: ServiceStatusSummary
