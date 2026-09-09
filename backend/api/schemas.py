from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


# ============================================================================
# Common
# ============================================================================

class CoordinateResponse(BaseModel):
    lat: float
    lon: float


class DatasetStatus(BaseModel):
    available: bool
    time_start: str | None = None
    time_end: str | None = None


# ============================================================================
# Health / status
# ============================================================================

GateStatus = Literal[
    "published",
    "stale",
    "blocked",
]


class RunStatusResponse(BaseModel):
    analysisWeek: str
    modelVersion: str
    gateStatus: GateStatus
    sourceWindow: str
    lastUpdated: str


# ============================================================================
# Field / map
# ============================================================================

class FieldPoint(BaseModel):
    lat: float
    lon: float
    value: float | None
    uncertainty: float | None = None


class FieldResponse(BaseModel):
    variable: str
    date: str
    depth: float | None
    stride: int
    points: list[FieldPoint]


# ============================================================================
# Profile
# ============================================================================

class ProfileVariable(BaseModel):
    value: float | None
    uncertainty: float | None = None


class ProfileDepthPoint(BaseModel):
    depth: float

    temperature: float | None = None
    temperature_uncertainty: float | None = None

    salinity: float | None = None
    salinity_uncertainty: float | None = None


class ProfileResponse(BaseModel):
    location: CoordinateResponse
    requestedDate: str
    dataDate: str | None

    depths: list[ProfileDepthPoint]

    tchp: float | None = None
    d26: float | None = None
    mld: float | None = None
    thermoclineDepth: float | None = None


# ============================================================================
# Scalar business variables
# ============================================================================

class TchpResponse(BaseModel):
    location: CoordinateResponse
    date: str
    value: float | None
    category: str | None = None
    d26: float | None = None


class D26Response(BaseModel):
    location: CoordinateResponse
    date: str
    value: float | None
    tchp: float | None = None


class MldResponse(BaseModel):
    location: CoordinateResponse
    date: str
    value: float | None


class ThermoclineResponse(BaseModel):
    location: CoordinateResponse
    date: str
    value: float | None


# ============================================================================
# Detailed depth response
# ============================================================================

class DepthDetailResponse(BaseModel):
    location: CoordinateResponse
    date: str
    depth: float

    temperature: float | None = None
    temperatureUncertainty: float | None = None

    salinity: float | None = None
    salinityUncertainty: float | None = None


# ============================================================================
# Uncertainty
# ============================================================================

class UncertaintyResponse(BaseModel):
    location: CoordinateResponse
    date: str
    depth: float

    temperature: float | None = None
    salinity: float | None = None


# ============================================================================
# Adaptive sampling
# ============================================================================

class SamplingRecommendation(BaseModel):
    lat: float
    lon: float

    priority: Literal[
        "low",
        "medium",
        "high",
    ]

    score: float

    reasons: list[str]


class SamplingRecommendationResponse(BaseModel):
    date: str
    recommendations: list[SamplingRecommendation]