"""
Data models for the Real-Time AI Smart Traffic & Accident Detection Fog Computing System.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import time


class Vehicle(BaseModel):
    id: str
    type: str  # 'car', 'suv', 'truck', 'bus', 'motorcycle', 'ambulance'
    x: float   # 0.0 to 1.0 (relative canvas coords)
    y: float
    vx: float
    vy: float
    speed_kmh: float
    lane: int
    direction: str  # 'N', 'S', 'E', 'W'
    status: str = 'normal'  # 'normal', 'braking', 'stopped', 'collided', 'emergency'
    confidence: float = 0.94
    bbox: List[float] = Field(default_factory=list)  # [x, y, w, h]


class SignalState(BaseModel):
    current_phase: str = 'NS_GREEN'  # 'NS_GREEN', 'NS_YELLOW', 'EW_GREEN', 'EW_YELLOW', 'EMERGENCY_CORRIDOR'
    time_remaining: int = 15
    ns_green_duration: int = 25
    ew_green_duration: int = 20
    is_adaptive: bool = True
    emergency_override: bool = False
    emergency_direction: Optional[str] = None


class AccidentEvent(BaseModel):
    id: str
    node_id: str
    location_name: str
    timestamp: str
    severity: str  # 'CRITICAL', 'HIGH', 'MODERATE'
    gps: List[float]  # [lat, lng]
    vehicles_involved: List[Dict[str, Any]]
    impact_speed_kmh: float
    collision_x: float
    collision_y: float
    confidence: float
    status: str = 'DETECTED'  # 'DETECTED', 'DISPATCHED', 'RESOLVED'
    recommended_response: List[str]
    fog_latency_ms: float
    cloud_estimated_latency_ms: float
    cleared_at: Optional[str] = None


class FogNodeTelemetry(BaseModel):
    node_id: str
    name: str
    lat: float
    lng: float
    status: str  # 'ONLINE', 'ALERT', 'CONGESTED'
    vehicle_count: int
    congestion_level: str  # 'LOW', 'MODERATE', 'HEAVY', 'GRIDLOCK'
    congestion_pct: float
    avg_speed_kmh: float
    inference_latency_ms: float
    cloud_latency_ms: float
    fps: float
    bandwidth_raw_mbps: float
    bandwidth_fog_kbps: float
    bandwidth_saved_pct: float
    cpu_load_pct: float
    memory_load_pct: float
    signal: SignalState
    active_incident: Optional[AccidentEvent] = None
    historical_throughput: List[int] = Field(default_factory=list)
