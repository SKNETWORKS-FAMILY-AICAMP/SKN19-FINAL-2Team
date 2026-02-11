import logging
import os
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from langsmith import RunTree

try:  # pragma: no cover - fallback for script execution
    from .agent.database import (
        LayeringDataError,
        PerfumeRepository,
        check_db_health,
        save_recommendation_feedback,
        save_my_perfume,
        save_recommendation_results,
    )
    from .agent.graph import (
        analyze_user_input,
        analyze_user_query,
        is_application_request,
        is_info_request,
        suggest_perfume_options,
    )
    from .agent.schemas import (
        PerfumeBasic,
        LayeringError,
        LayeringErrorResponse,
        LayeringRequest,
        LayeringResponse,
        RecommendationFeedbackRequest,
        RecommendationFeedbackResponse,
        SaveResult,
        UserQueryRequest,
        UserQueryResponse,
    )
    from .agent.tools import (
        _matches_input_name,
        _should_exclude_candidate,
        build_input_name_keys,
        rank_recommendations,
    )
except ImportError:  # pragma: no cover
    from agent.database import (
        LayeringDataError,
        PerfumeRepository,
        check_db_health,
        save_recommendation_feedback,
        save_my_perfume,
        save_recommendation_results,
    )
    from agent.graph import (
        analyze_user_input,
        analyze_user_query,
        is_application_request,
        is_info_request,
        suggest_perfume_options,
    )
    from agent.schemas import (
        PerfumeBasic,
        LayeringError,
        LayeringErrorResponse,
        LayeringRequest,
        LayeringResponse,
        RecommendationFeedbackRequest,
        RecommendationFeedbackResponse,
        SaveResult,
        UserQueryRequest,
        UserQueryResponse,
    )
    from agent.tools import (
        _matches_input_name,
        _should_exclude_candidate,
        build_input_name_keys,
        rank_recommendations,
    )


load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
app = FastAPI(title="Layering Service")
logger = logging.getLogger("layering")
DEBUG_ERROR_DETAILS = os.getenv("LAYERING_DEBUG_ERRORS", "").lower() in {
    "true",
    "1",
    "yes",
}
LANGSMITH_TRACING = os.getenv("LANGSMITH_TRACING", "").lower() in {
    "true",
    "1",
    "yes",
}
if LANGSMITH_TRACING:
    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")

# CORS origins from environment variable
cors_origins_env = os.getenv("LAYERING_CORS_ORIGINS", "")
if cors_origins_env:
    origins = [origin.strip() for origin in cors_origins_env.split(",") if origin.strip() and origin.strip() != "*"]
else:
    # Default for local development
    origins = ["http://localhost:3000", "http://127.0.0.1:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

repository: Optional[PerfumeRepository] = None


def get_repository() -> PerfumeRepository:
    global repository
    if repository is not None:
        return repository
    repository = PerfumeRepository()
    return repository


def _start_langsmith_run(name: str, inputs: dict, metadata: dict | None = None) -> RunTree | None:
    if not LANGSMITH_TRACING:
        return None
    try:
        run = RunTree(
            name=name,
            run_type="chain",
            inputs=inputs,
            extra={"metadata": metadata or {}},
        )
        run.post()
        return run
    except Exception:
        return None


def _filter_duplicate_recommendations(
    base_perfume: PerfumeBasic,
    recommendations: list,
    repository: PerfumeRepository,
    input_name_keys: set[str] | None = None,
) -> tuple[list, int]:
    filtered = []
    filtered_out = 0
    try:
        base_vector = repository.get_perfume(base_perfume.perfume_id)
    except KeyError:
        return recommendations, 0
    for candidate in recommendations:
        try:
            candidate_vector = repository.get_perfume(candidate.perfume_id)
        except KeyError:
            continue
        if input_name_keys and _matches_input_name(candidate_vector, input_name_keys):
            filtered_out += 1
            continue
        if _should_exclude_candidate(base_vector, candidate_vector):
            filtered_out += 1
            continue
        filtered.append(candidate)
    return filtered, filtered_out


def build_error_response(
    *,
    code: str,
    message: str,
    step: str,
    retriable: bool,
    details: Optional[str] = None,
) -> LayeringErrorResponse:
    return LayeringErrorResponse(
        error=LayeringError(
            code=code,
            message=message,
            step=step,
            retriable=retriable,
            details=details if DEBUG_ERROR_DETAILS else None,
        )
    )


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Layering service is running!"}


@app.get("/health")
def health() -> dict[str, str]:
    db_status = "ok" if check_db_health() else "degraded"
    if repository is None:
        repo_status = "uninitialized"
    else:
        repo_status = "ok" if repository.count > 0 else "degraded"
    status = "ok" if db_status == "ok" and repo_status == "ok" else "degraded"
    return {
        "status": status,
        "service": "layering",
        "db": db_status,
        "repository": repo_status,
    }


@app.post("/layering/recommend", response_model=LayeringResponse)
def layering_recommend(payload: LayeringRequest) -> LayeringResponse:
    run = _start_langsmith_run(
        "layering.recommend",
        inputs={
            "base_perfume_id": payload.base_perfume_id,
            "keywords": payload.keywords,
            "member_id": payload.member_id,
        },
    )
    try:
        logger.info(
            "Layering recommend request received (member_id=%s, save_recommendations=%s, save_my_perfume=%s)",
            payload.member_id,
            payload.save_recommendations,
            payload.save_my_perfume,
        )
        if not payload.member_id:
            logger.info("Layering recommend request has no member_id")
        repo = get_repository()
        base_perfume = repo.get_perfume(payload.base_perfume_id)
        recommendations, total_available = rank_recommendations(
            payload.base_perfume_id,
            payload.keywords,
            repo,
        )
        recommendations, filtered_out = _filter_duplicate_recommendations(
            PerfumeBasic(
                perfume_id=base_perfume.perfume_id,
                perfume_name=base_perfume.perfume_name,
                perfume_brand=base_perfume.perfume_brand,
                image_url=base_perfume.image_url,
                concentration=base_perfume.concentration,
            ),
            recommendations,
            repo,
            input_name_keys=None,
        )
        if filtered_out:
            total_available = max(0, total_available - filtered_out)
        save_results = []
        if payload.member_id and payload.save_recommendations:
            # 추천 결과 저장 요청이 있을 때만 recom_db에 기록
            save_results.append(
                save_recommendation_results(payload.member_id, recommendations)
            )
        if payload.member_id and payload.save_my_perfume:
            try:
                save_results.append(save_my_perfume(payload.member_id, base_perfume))
            except KeyError:
                save_results.append(
                    SaveResult(
                        target="my_perfume",
                        saved=False,
                        saved_count=0,
                        message="base perfume not found",
                    )
                )
        if payload.member_id:
            logger.info("Layering recommend save_results=%s", save_results)
    except LayeringDataError as exc:
        logger.exception("Layering data error during recommendation")
        error_payload = build_error_response(
            code=exc.code,
            message=exc.message,
            step=exc.step,
            retriable=exc.retriable,
            details=exc.details,
        )
        if run is not None:
            run.end(error=str(error_payload.model_dump(exclude_none=True)))
        raise HTTPException(
            status_code=503,
            detail=error_payload.model_dump(exclude_none=True),
        ) from exc
    except KeyError as exc:
        error_payload = build_error_response(
            code="PERFUME_NOT_FOUND",
            message="요청한 향수를 찾지 못했습니다.",
            step="perfume_lookup",
            retriable=False,
            details=str(exc),
        )
        if run is not None:
            run.end(error=str(error_payload.model_dump(exclude_none=True)))
        raise HTTPException(
            status_code=404,
            detail=error_payload.model_dump(exclude_none=True),
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error during recommendation")
        error_payload = build_error_response(
            code="RANKING_FAILED",
            message="추천 계산에 실패했습니다.",
            step="ranking",
            retriable=False,
            details=str(exc),
        )
        if run is not None:
            run.end(error=str(error_payload.model_dump(exclude_none=True)))
        raise HTTPException(
            status_code=500,
            detail=error_payload.model_dump(exclude_none=True),
        ) from exc

    note = None
    if total_available < 3:
        note = (
            f"Only {total_available} layering option(s) available after feasibility checks."
        )
    if filtered_out:
        duplicate_note = "같은 이름의 향수는 추천에서 제외했어요."
        note = f"{note} {duplicate_note}" if note else duplicate_note

    if run is not None:
        run.end(
            outputs={
                "recommendation_ids": [item.perfume_id for item in recommendations],
                "total_available": total_available,
                "filtered_out": filtered_out,
            }
        )

    return LayeringResponse(
        base_perfume=PerfumeBasic(
            perfume_id=base_perfume.perfume_id,
            perfume_name=base_perfume.perfume_name,
            perfume_brand=base_perfume.perfume_brand,
            image_url=base_perfume.image_url,
            concentration=base_perfume.concentration,
        ),
        base_perfume_id=payload.base_perfume_id,
        keywords=payload.keywords,
        total_available=total_available,
        recommendations=recommendations,
        note=note,
        save_results=save_results,
    )


@app.post("/layering/analyze", response_model=UserQueryResponse)
def layering_analyze(payload: UserQueryRequest) -> UserQueryResponse:
    run = _start_langsmith_run(
        "layering.analyze",
        inputs={
            "user_text": payload.user_text,
            "member_id": payload.member_id,
            "context_recommended_perfume_id": payload.context_recommended_perfume_id,
        },
    )
    try:
        logger.info(
            "Layering analyze request received (member_id=%s, save_recommendations=%s, save_my_perfume=%s)",
            payload.member_id,
            payload.save_recommendations,
            payload.save_my_perfume,
        )
        if not payload.member_id:
            logger.info("Layering analyze request has no member_id")
        repo = get_repository()
        preferences = analyze_user_input(payload.user_text)
        keywords = preferences.keywords
        info_request = is_info_request(payload.user_text)
        if is_application_request(payload.user_text):
            note = (
                "레이어링은 맥박이 뛰는 부위에 1~2회씩 얇게 뿌리고,"
                " 지속력이 강한 향은 먼저, 가벼운 향은 나중에 덧뿌리면 좋아요."
                " 손목·귀 뒤·목선처럼 체온이 있는 곳을 추천합니다."
            )
            return UserQueryResponse(
                raw_text=payload.user_text,
                keywords=keywords,
                base_perfume_id=None,
                base_perfume=None,
                detected_perfumes=[],
                detected_pair=None,
                recommendation=None,
                recommended_perfume_info=None,
                brand_name=None,
                brand_best_perfume=None,
                brand_best_score=None,
                brand_best_reason=None,
                clarification_prompt=None,
                clarification_options=[],
                note=note,
                save_results=[],
            )
        analysis = analyze_user_query(
            payload.user_text,
            repo,
            preferences,
            context_recommended_perfume_id=payload.context_recommended_perfume_id,
        )
        input_name_keys = build_input_name_keys(
            payload.user_text,
            analysis.detected_perfumes,
        )
        recommendation = None
        note = None
        base_perfume_id = None
        clarification_prompt = None
        clarification_options: list[str] = []
        brand_name = analysis.brand_name
        brand_best_perfume = analysis.brand_best_perfume
        brand_best_score = analysis.brand_best_score
        brand_best_reason = analysis.brand_best_reason
        similar_perfumes = analysis.similar_perfumes
        save_results = []
        skip_recommendation = False

        if analysis.recommended_perfume_info:
            note = "요청하신 향수 정보를 안내합니다."
            skip_recommendation = True
        elif similar_perfumes:
            note = "비슷한 향수 후보를 정리해 드렸어요."
            skip_recommendation = True
        elif brand_best_perfume:
            note = "브랜드 내 레이어링 범용성이 가장 높은 향수입니다."
            skip_recommendation = True
        elif info_request and not payload.context_recommended_perfume_id:
            clarification_prompt = "추천된 향수 정보는 최근 추천 결과가 필요해요. 먼저 레이어링 추천을 받아주세요."
            clarification_options = []
            skip_recommendation = True

        if skip_recommendation:
            pass
        elif analysis.pairing_analysis:
            recommendation = analysis.pairing_analysis.result
            if analysis.detected_pair:
                base_perfume_id = analysis.detected_pair.base_perfume_id
        elif analysis.detected_perfumes:
            base_perfume_id = analysis.detected_perfumes[0].perfume_id
            recommendations, _ = rank_recommendations(
                base_perfume_id,
                keywords,
                repo,
                input_name_keys=input_name_keys,
            )
            if recommendations:
                recommendation = recommendations[0]
            else:
                note = "No feasible layering options found for the detected base perfume."
        else:
            note = "No perfume names detected from the query."
            clarification_prompt = "레이어링할 향수 이름을 알려주세요. 예: CK One, Wood Sage & Sea Salt"
            clarification_options = suggest_perfume_options(payload.user_text, repo)

        duplicate_filtered = False
        if recommendation:
            try:
                base_vector = repo.get_perfume(base_perfume_id) if base_perfume_id else None
                candidate_vector = repo.get_perfume(recommendation.perfume_id)
            except KeyError:
                base_vector = None
                candidate_vector = None
            if candidate_vector:
                if input_name_keys and _matches_input_name(candidate_vector, input_name_keys):
                    recommendation = None
                    duplicate_filtered = True
                elif base_vector and _should_exclude_candidate(base_vector, candidate_vector):
                    recommendation = None
                    duplicate_filtered = True
            if duplicate_filtered:
                duplicate_note = "같은 이름의 향수는 추천에서 제외했어요."
                note = f"{note} {duplicate_note}" if note else duplicate_note

        if payload.member_id and payload.save_recommendations and recommendation:
            # 추천 결과 저장 요청이 있을 때만 recom_db에 기록
            save_results.append(
                save_recommendation_results(payload.member_id, [recommendation])
            )
        if payload.member_id and payload.save_my_perfume and base_perfume_id:
            try:
                base_perfume = repo.get_perfume(base_perfume_id)
                save_results.append(save_my_perfume(payload.member_id, base_perfume))
            except KeyError:
                save_results.append(
                    SaveResult(
                        target="my_perfume",
                        saved=False,
                        saved_count=0,
                        message="base perfume not found",
                    )
                )
        if payload.member_id:
            logger.info("Layering analyze save_results=%s", save_results)

        if not keywords and note is None and recommendation is not None and not skip_recommendation:
            note = "요청 의도 키워드를 찾지 못해 기본 조합으로 추천했어요."

        base_perfume = None
        if base_perfume_id:
            try:
                base = repo.get_perfume(base_perfume_id)
                base_perfume = PerfumeBasic(
                    perfume_id=base.perfume_id,
                    perfume_name=base.perfume_name,
                    perfume_brand=base.perfume_brand,
                    image_url=base.image_url,
                    concentration=base.concentration,
                )
            except KeyError:
                base_perfume = None
        if run is not None:
            run.end(
                outputs={
                    "base_perfume_id": base_perfume_id,
                    "recommendation_id": recommendation.perfume_id if recommendation else None,
                    "duplicate_filtered": duplicate_filtered,
                }
            )
    except LayeringDataError as exc:
        logger.exception("Layering data error during analysis")
        error_payload = build_error_response(
            code=exc.code,
            message=exc.message,
            step=exc.step,
            retriable=exc.retriable,
            details=exc.details,
        )
        if run is not None:
            run.end(error=str(error_payload.model_dump(exclude_none=True)))
        raise HTTPException(
            status_code=503,
            detail=error_payload.model_dump(exclude_none=True),
        ) from exc
    except KeyError as exc:
        error_payload = build_error_response(
            code="PERFUME_NOT_FOUND",
            message="요청한 향수를 찾지 못했습니다.",
            step="perfume_lookup",
            retriable=False,
            details=str(exc),
        )
        if run is not None:
            run.end(error=str(error_payload.model_dump(exclude_none=True)))
        raise HTTPException(
            status_code=404,
            detail=error_payload.model_dump(exclude_none=True),
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error during analysis")
        error_payload = build_error_response(
            code="ANALYSIS_FAILED",
            message="자연어 분석에 실패했습니다.",
            step="analysis",
            retriable=False,
            details=str(exc),
        )
        if run is not None:
            run.end(error=str(error_payload.model_dump(exclude_none=True)))
        raise HTTPException(
            status_code=500,
            detail=error_payload.model_dump(exclude_none=True),
        ) from exc

    return UserQueryResponse(
        raw_text=payload.user_text,
        keywords=keywords,
        base_perfume_id=base_perfume_id,
        base_perfume=base_perfume,
        detected_perfumes=analysis.detected_perfumes,
        detected_pair=analysis.detected_pair,
        recommendation=recommendation,
        recommended_perfume_info=analysis.recommended_perfume_info,
        brand_name=brand_name,
        brand_best_perfume=brand_best_perfume,
        brand_best_score=brand_best_score,
        brand_best_reason=brand_best_reason,
        similar_perfumes=similar_perfumes,
        clarification_prompt=clarification_prompt,
        clarification_options=clarification_options,
        note=note,
        save_results=save_results,
    )


@app.post(
    "/layering/recommendation/feedback",
    response_model=RecommendationFeedbackResponse,
)
def save_layering_feedback(
    payload: RecommendationFeedbackRequest,
) -> RecommendationFeedbackResponse:
    logger.info(
        "Layering feedback received (member_id=%s, perfume_id=%s, preference=%s)",
        payload.member_id,
        payload.perfume_id,
        payload.preference,
    )
    save_result = save_recommendation_feedback(
        payload.member_id,
        payload.perfume_id,
        payload.perfume_name,
        payload.preference,
    )
    return RecommendationFeedbackResponse(save_result=save_result)
