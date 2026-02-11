"""Internal algorithm data structures for layering logic."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel

from .schemas import PerfumeVector, ScoreBreakdown


class ComponentScores(BaseModel):
    harmony: float
    bridge: float
    penalty: float
    target: float


class LayeringComputationResult(BaseModel):
    candidate: PerfumeVector
    total_score: float
    feasible: bool
    feasibility_reason: Optional[str]
    clash_detected: bool
    spray_order: List[str]
    score_breakdown: ScoreBreakdown
    layered_vector: List[float]
