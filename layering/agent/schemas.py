"""Pydantic schemas for the layering service domain objects."""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

from .constants import ACCORDS


class PerfumeAccord(BaseModel):
    accord: str = Field(description="Accord name aligned with ACCORDS order")
    ratio: float = Field(ge=0, description="Numeric contribution of the accord")

    @field_validator("accord")
    @classmethod
    def validate_accord(cls, value: str) -> str:  # noqa: D401
        if value not in ACCORDS:
            raise ValueError(f"Accord '{value}' not recognised")
        return value


class PerfumeBasic(BaseModel):
    perfume_id: str
    perfume_name: str
    perfume_brand: str
    image_url: Optional[str] = None
    concentration: Optional[str] = None


class PerfumeRecord(BaseModel):
    """Raw perfume information prior to vectorization."""

    perfume: PerfumeBasic
    accords: List[PerfumeAccord]
    base_notes: List[str] = Field(default_factory=list)


class PerfumeVector(BaseModel):
    perfume_id: str
    perfume_name: str
    perfume_brand: str
    image_url: Optional[str] = None
    concentration: Optional[str] = None
    vector: List[float]
    total_intensity: float
    persistence_score: float
    dominant_accords: List[str]
    base_notes: List[str] = Field(default_factory=list)

    @field_validator("vector")
    @classmethod
    def validate_vector_length(cls, value: List[float]) -> List[float]:
        if len(value) != len(ACCORDS):
            raise ValueError("Vector length mismatch with ACCORDS")
        return value

    @field_validator("base_notes")
    @classmethod
    def validate_base_notes(cls, value: List[str]) -> List[str]:
        return [note for note in value if note]


class LayeringRequest(BaseModel):
    base_perfume_id: str = Field(..., description="Base perfume identifier")
    keywords: List[str] = Field(default_factory=list)
    member_id: Optional[int] = Field(
        default=None, description="Member identifier for saving results"
    )
    save_recommendations: bool = Field(
        default=True, description="Persist recommendations when member_id is set"
    )
    save_my_perfume: bool = Field(
        default=False, description="Save base perfume to my collection"
    )


class UserQueryRequest(BaseModel):
    user_text: str = Field(..., description="Free-form user question")
    member_id: Optional[int] = Field(
        default=None, description="Member identifier for saving results"
    )
    context_recommended_perfume_id: Optional[str] = Field(
        default=None,
        description="Recommended perfume id from previous response",
    )
    save_recommendations: bool = Field(
        default=True, description="Persist recommendations when member_id is set"
    )
    save_my_perfume: bool = Field(
        default=False, description="Save detected base perfume to my collection"
    )


class ScoreBreakdown(BaseModel):
    base: float = Field(default=1.0)
    harmony: float
    bridge: float
    penalty: float
    target: float


class LayeringCandidate(BaseModel):
    perfume_id: str
    perfume_name: str
    perfume_brand: str
    image_url: Optional[str] = None
    concentration: Optional[str] = None
    total_score: float
    feasible: bool = True
    feasibility_reason: Optional[str]
    spray_order: List[str]
    score_breakdown: ScoreBreakdown
    clash_detected: bool
    analysis: str
    layered_vector: List[float] = Field(default_factory=list)


class SaveResult(BaseModel):
    target: str = Field(description="Save target identifier")
    saved: bool
    saved_count: int = 0
    message: Optional[str] = None


class RecommendationFeedbackRequest(BaseModel):
    member_id: int = Field(..., description="Member identifier")
    perfume_id: str = Field(..., description="Recommended perfume identifier")
    perfume_name: str = Field(..., description="Recommended perfume name")
    preference: Literal["GOOD", "BAD"] = Field(
        ..., description="Satisfaction value for the recommendation"
    )


class RecommendationFeedbackResponse(BaseModel):
    save_result: SaveResult


class LayeringResponse(BaseModel):
    base_perfume: Optional[PerfumeBasic] = None
    base_perfume_id: str
    keywords: List[str]
    total_available: int
    recommendations: List[LayeringCandidate]
    note: Optional[str] = None
    save_results: List[SaveResult] = Field(default_factory=list)


class DetectedPerfume(BaseModel):
    perfume_id: str
    perfume_name: str
    perfume_brand: str
    match_score: float
    matched_text: str


class DetectedPair(BaseModel):
    base_perfume_id: Optional[str]
    candidate_perfume_id: Optional[str]


class PairingAnalysis(BaseModel):
    base_perfume_id: str
    candidate_perfume_id: str
    result: LayeringCandidate


class UserQueryAnalysis(BaseModel):
    raw_text: str
    detected_perfumes: List[DetectedPerfume]
    detected_pair: Optional[DetectedPair] = None
    pairing_analysis: Optional[PairingAnalysis] = None
    recommended_perfume_info: Optional["PerfumeInfo"] = None
    brand_name: Optional[str] = None
    brand_best_perfume: Optional[PerfumeBasic] = None
    brand_best_score: Optional[float] = None
    brand_best_reason: Optional[str] = None
    similar_perfumes: List[PerfumeBasic] = Field(default_factory=list)


class UserQueryResponse(BaseModel):
    raw_text: str
    keywords: List[str]
    base_perfume_id: Optional[str] = None
    base_perfume: Optional[PerfumeBasic] = None
    detected_perfumes: List[DetectedPerfume]
    detected_pair: Optional[DetectedPair] = None
    recommendation: Optional[LayeringCandidate] = None
    recommended_perfume_info: Optional["PerfumeInfo"] = None
    brand_name: Optional[str] = None
    brand_best_perfume: Optional[PerfumeBasic] = None
    brand_best_score: Optional[float] = None
    brand_best_reason: Optional[str] = None
    similar_perfumes: List[PerfumeBasic] = Field(default_factory=list)
    clarification_prompt: Optional[str] = None
    clarification_options: List[str] = Field(default_factory=list)
    note: Optional[str] = None
    save_results: List[SaveResult] = Field(default_factory=list)


class LayeringError(BaseModel):
    code: str
    message: str
    step: str
    retriable: bool = False
    details: Optional[str] = None


class LayeringErrorResponse(BaseModel):
    error: LayeringError


class PerfumeInfo(BaseModel):
    perfume_id: str
    perfume_name: str
    perfume_brand: str
    image_url: Optional[str] = None
    concentration: Optional[str] = None
    gender: Optional[str] = None
    accords: List[str] = Field(default_factory=list)
    seasons: List[str] = Field(default_factory=list)
    occasions: List[str] = Field(default_factory=list)
    top_notes: List[str] = Field(default_factory=list)
    middle_notes: List[str] = Field(default_factory=list)
    base_notes: List[str] = Field(default_factory=list)
