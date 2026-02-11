# backend/agent/graph.py
import json
import asyncio
import random
import uuid
from typing import List, Dict, Any, Optional, Set

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI  # type: ignore[reportMissingImports]
from langchain_core.messages import (  # type: ignore[reportMissingImports]
    SystemMessage,
    AIMessage,
    HumanMessage,
)
from langgraph.graph import StateGraph, START, END  # type: ignore[reportMissingImports]
from langgraph.checkpoint.memory import MemorySaver  # type: ignore[reportMissingImports]

# [Import] 로컬 모듈
from .schemas import (
    AgentState,
    UserPreferences,
    InterviewResult,
    RoutingDecision,
    ValidationResult,
    SearchStrategyPlan,
    StrategyResult,
    PerfumeDetail,
    PerfumeNotes,
)

# [Import] Expression Loader for dynamic dictionary injection
from .expression_loader import ExpressionLoader
from .brand_exclusion_parser import parse_brand_exclusions, should_clear_brand_fields

from .tools import (
    advanced_perfume_search_tool,
    lookup_note_by_string_tool,
    lookup_note_by_vector_tool,
    smart_perfume_search,
)

from .prompts import (
    PRE_VALIDATOR_PROMPT,
    SUPERVISOR_PROMPT,
    INTERVIEWER_PROMPT,
    RESEARCHER_SYSTEM_PROMPT,
    WRITER_FAILURE_PROMPT,
    WRITER_RECOMMENDATION_PROMPT_SINGLE,
    WRITER_RECOMMENDATION_PROMPT_EXPERT_SINGLE,
)
from .database import save_recommendation_log, fetch_meta_data
from .denylist import has_forbidden_words, UserFriendlyStrategyLabels

from .followup_classifier import classify_followup
from .personalization import get_personalization_summary
from .use_case_utils import infer_use_case

# [정보 검색 전용 서브 그래프 임포트]
from .graph_info import info_graph

load_dotenv()

import logging

logger = logging.getLogger(__name__)

# NOTE: Imported for monkeypatching in tests.
_MONKEYPATCH_TOOLS = (lookup_note_by_string_tool, lookup_note_by_vector_tool)

# ==========================================
# 0. Helper Functions (moved to utils.py)
# ==========================================
from .utils import (
    parse_recommended_count,
    normalize_recommended_count,
    extract_save_refs,
    sanitize_filters,
)

# ==========================================
# 1. 모델 설정
# ==========================================
FAST_LLM = ChatOpenAI(model="gpt-4.1-mini", temperature=0, streaming=True)
SMART_LLM = ChatOpenAI(model="gpt-4.1", temperature=0, streaming=True)
SUPER_SMART_LLM = ChatOpenAI(model="gpt-5.2", temperature=0, streaming=True)
# Non-streaming version for parallel_reco to prevent token interleaving
SUPER_SMART_LLM_NO_STREAM = ChatOpenAI(model="gpt-5.2", temperature=0, streaming=False)


# ==========================================
# 2. 유틸리티
# ==========================================
def log_filters(h_filters: dict, s_filters: dict):
    pass


def generate_pre_notice(
    requested: int,
    is_explicit: bool
) -> str:
    """
    스트리밍 전에 출력 가능한 안내 메시지를 생성합니다.
    (케이스 1: 과다 요청)

    Args:
        requested: 요청된 개수
        is_explicit: 사용자가 명시적으로 개수를 요청했는지

    Returns:
        안내 메시지 (필요 없으면 빈 문자열)
    """
    MAX_COUNT = 5

    # 케이스 1: 과다 요청 (명시적일 때만)
    if is_explicit and requested > MAX_COUNT:
        return (f"\n💡 안내: 한 번에 최대 {MAX_COUNT}개까지만 추천이 가능합니다. "
                f"{MAX_COUNT}개의 향수를 엄선하여 추천드렸습니다.\n\n")

    return ""


def generate_post_notice(
    requested: int,
    actual: int,
    is_explicit: bool
) -> str:
    """
    스트리밍 후에 출력 가능한 안내 메시지를 생성합니다.
    (케이스 2: 부분 실패)

    Args:
        requested: 요청된 개수
        actual: 실제 생성된 개수
        is_explicit: 사용자가 명시적으로 개수를 요청했는지

    Returns:
        안내 메시지 (필요 없으면 빈 문자열)
    """
    # 케이스 2: 부분 실패 (명시적 요청일 때만!)
    if is_explicit and actual < requested:
        return (f"\n💡 안내: 요청하신 {requested}개 중 {actual}개의 향수를 찾았습니다. "
                f"조건에 맞는 향수가 제한적이었습니다.")

    return ""


async def smart_search_with_retry_async(
    h_filters: dict,
    s_filters: dict,
    exclude_ids: Optional[List[int]] = None,
    query_text: str = "",
    rank_mode: str = "DEFAULT",
):
    _ = advanced_perfume_search_tool  # Keep reference for monkeypatches/tests
    return await smart_perfume_search(
        h_filters=h_filters,
        s_filters=s_filters,
        exclude_ids=exclude_ids,
        query_text=query_text,
        rank_mode=rank_mode,
    )


async def call_info_graph_wrapper(state: AgentState):
    """Sub-Graph Wrapper"""
    current_query = state.get("user_query", "")

    if not current_query and state.get("messages"):
        last_msg = state["messages"][-1]
        if isinstance(last_msg, HumanMessage):
            current_query = last_msg.content

    subgraph_input = {
        "user_query": current_query,
        "messages": state.get("messages", []),
        "user_mode": state.get("user_mode", "BEGINNER"),
    }

    try:
        result = await info_graph.ainvoke(subgraph_input)
        
        # [Wave 2-4] Map info_status to chat_outcome_status
        info_status = result.get("info_status", "OK")
        
        return {
            "messages": result.get("messages", []),
            "chat_outcome_status": info_status,  # OK/NO_RESULTS/ERROR 직접 매핑
            "chat_outcome_reason_code": f"info_{info_status.lower()}",
            "chat_outcome_reason_detail": f"Info graph completed with status: {info_status}",
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        
        # [Wave 2-4] Set ERROR status on exception
        return {
            "messages": [AIMessage(content="정보 검색 중 오류가 발생했습니다.")],
            "chat_outcome_status": "ERROR",
            "chat_outcome_reason_code": "info_exception",
            "chat_outcome_reason_detail": f"Info graph exception: {str(e)[:100]}",
        }


# ==========================================
# 3. Node Functions
# ==========================================


def pre_validator_node(state: AgentState):
    """
    [Pre-Validator] 요청 실현 가능성 사전 검증.
    DB에 없는 속성 요청을 조기 차단합니다.
    """
    print("\n" + "=" * 60, flush=True)
    print("🔍 [Pre-Validator] 요청 가능 여부 검증 중...", flush=True)

    messages = [SystemMessage(content=PRE_VALIDATOR_PROMPT)] + state["messages"]

    try:
        result = SMART_LLM.with_structured_output(ValidationResult).invoke(messages)

        if result.is_unsupported:
            print(f"   ❌ 지원 불가: {result.unsupported_category} - {result.reason}", flush=True)
            return {
                "validation_result": "unsupported",
                "unsupported_category": result.unsupported_category,
                "unsupported_reason": result.reason
            }
        else:
            print(f"   ✅ 지원 가능 - {result.reason}", flush=True)
            return {"validation_result": "supported"}

    except Exception as e:
        print(f"   ⚠️ 검증 실패(Error): {e} -> 기본값 지원 가능으로 처리", flush=True)
        return {"validation_result": "supported"}


def supervisor_node(state: AgentState):
    """[Main Router]"""
    print("\n" + "=" * 60, flush=True)
    print("👀 [Supervisor] 사용자 의도 분류 중...", flush=True)

    if state.get("active_mode") == "interviewer":
        print("   👉 인터뷰 진행 중 -> Interviewer로 이동", flush=True)
        return {"next_step": "interviewer"}

    messages = [SystemMessage(content=SUPERVISOR_PROMPT)] + state["messages"]

    try:
        decision = SMART_LLM.with_structured_output(RoutingDecision).invoke(messages)
        next_step = decision.next_step
        print(f"   👉 분류 결과: {next_step}", flush=True)
        return {"next_step": next_step}

    except Exception as e:
        print(f"   ⚠️ 분류 실패(Error): {e} -> 기본값 Writer로 이동", flush=True)
        return {"next_step": "writer"}


def interviewer_node(state: AgentState):
    """[Interviewer]"""
    current_prefs = state.get("user_preferences") or {}
    if isinstance(current_prefs, UserPreferences):
        current_prefs = current_prefs.model_dump(exclude_none=True)
    question_count = state.get("question_count", 0)
    
    # 질문 횟수 증가
    question_count += 1
    
    # 거부 키워드 감지
    rejection_keywords = ["몰라", "아무거나", "그냥 추천", "빨리", "모르겠", "상관없"]
    user_message = state["messages"][-1].content.lower() if state["messages"] else ""
    is_rejection = any(keyword in user_message for keyword in rejection_keywords)
    
    # 질문 상한 또는 거부 감지 시 폴백 트리거
    should_fallback = (question_count >= 3) or (question_count >= 2 and is_rejection)
    
    if should_fallback:
        # 폴백: 기본값으로 채우기
        fallback_prefs = {
            **current_prefs,
            "gender": current_prefs.get("gender", "Unisex"),
            # season, occasion은 None으로 두어 필터링 안 함 (모든 계절/상황 포함)
            "season": current_prefs.get("season"),
            "occasion": current_prefs.get("occasion"),
            "style": current_prefs.get("style", "Daily"),
            "target": current_prefs.get("target", "일반"),
        }
        fallback_frame_id = state.get("frame_id") or str(uuid.uuid4())
        
        print(
            f"      ⚠️ [Fallback] 질문 상한 도달 또는 거부 감지. 기본값으로 추천 진행: {json.dumps(fallback_prefs, ensure_ascii=False)}",
            flush=True,
        )
        
        return {
            "next_step": "researcher",
            "user_preferences": fallback_prefs,
            "status": "정보를 바탕으로 추천을 준비합니다...",
            "active_mode": None,
            "question_count": question_count,
            "fallback_triggered": True,
            "frame_id": fallback_frame_id,
            "recommended_history": state.get("recommended_history", []),
        }

    # 현재 정보를 문자열로 변환
    current_context_str = json.dumps(current_prefs, ensure_ascii=False)

    # [★수정] 여기서 CURRENT_CONTEXT만 채워주면 됩니다! (SUFFICIENCY_CRITERIA는 이미 들어있음)
    try:
        formatted_prompt = INTERVIEWER_PROMPT.format(
            CURRENT_CONTEXT=current_context_str
        )
    except Exception as e:
        # 혹시라도 포맷팅 에러가 나면 원본 프롬프트를 사용하여 멈추지 않게 함
        print(f"⚠️ Prompt Formatting Error: {e}")
        formatted_prompt = INTERVIEWER_PROMPT.replace(
            "{{CURRENT_CONTEXT}}", "정보 없음"
        )

    messages = [SystemMessage(content=formatted_prompt)] + state["messages"]

    try:
        interview_result = SMART_LLM.with_structured_output(InterviewResult).invoke(messages)

        current_query = state.get("user_query", "")
        recent_messages = state.get("messages", [])[-5:]
        if not current_query and state.get("messages"):
            last_msg = state["messages"][-1]
            if isinstance(last_msg, HumanMessage):
                current_query = last_msg.content

        classification = classify_followup(
            current_query=current_query,
            recent_messages=recent_messages,
            current_constraints=current_prefs,
        )

        # [★추가] 브랜드 제외 파싱 (세션 레벨 유지)
        session_exclude_brands = state.get("exclude_brands", [])
        current_exclude_brands, has_exclusion = parse_brand_exclusions(current_query)
        
        # 새로운 제외 요청이 있으면 누적
        if has_exclusion:
            session_exclude_brands = list(set(session_exclude_brands + current_exclude_brands))
            print(
                f"🚫 [Exclusion] Detected exclude_brands: {current_exclude_brands}, Session: {session_exclude_brands}",
                flush=True,
            )
        
        # 명시적 브랜드 요청 시 해당 브랜드 제외 목록에서 해제
        if current_prefs and current_prefs.get("brand"):
            requested_brand = current_prefs.get("brand")
            if requested_brand in session_exclude_brands:
                session_exclude_brands.remove(requested_brand)
                print(
                    f"   🔄 [Exclusion] Removed {requested_brand} from exclusion list due to explicit request",
                    flush=True,
                )

        current_frame_id = state.get("frame_id")
        if classification.intent in ["NEW_RECO", "RESET"]:
            frame_id = str(uuid.uuid4())
            # [★수정] 히스토리는 유지 (세션 내내 누적)
            new_recommended_history = None  # None = 기존 히스토리 유지
            print(
                f"🔄 [Frame] New frame created: {frame_id[:8]}... (intent={classification.intent})",
                flush=True,
            )
            print("📚 [History] Recommended history maintained (session-level)", flush=True)
            # [★제거] DB 클리어 안 함 - 세션 내내 유지
        else:
            frame_id = current_frame_id or str(uuid.uuid4())
            new_recommended_history = None
            print(
                f"✅ [Frame] Frame maintained: {frame_id[:8] if frame_id else 'new'}... (intent={classification.intent})",
                flush=True,
            )

        merged_prefs: Dict[str, Any] = {}
        for slot in classification.keep_slots:
            if current_prefs and slot in current_prefs and current_prefs[slot] is not None:
                merged_prefs[slot] = current_prefs[slot]

        new_prefs = interview_result.user_preferences
        for key, value in new_prefs.model_dump(exclude_none=True).items():
            merged_prefs[key] = value

        # [★추가] 브랜드 제외 처리
        merged_prefs["exclude_brands"] = session_exclude_brands
        # 제외 브랜드가 있으면 brand, reference_brand 클리어
        if should_clear_brand_fields(session_exclude_brands):
            merged_prefs["brand"] = None
            merged_prefs["reference_brand"] = None
            print(
                f"   → brand/reference_brand cleared due to exclusions",
                flush=True,
            )

        for slot in classification.drop_slots:
            if slot not in merged_prefs:
                merged_prefs[slot] = None

        print(
            f"📋 [Merge] Keep: {classification.keep_slots}, Drop: {classification.drop_slots}",
            flush=True,
        )
        print(f"📋 [Merge] Result: {list(merged_prefs.keys())}", flush=True)

        state["user_preferences"] = merged_prefs
        # [★추가] recommended_count를 state 최상위로 올림 (parallel_reco_node에서 사용)
        if merged_prefs.get("recommended_count"):
            state["recommended_count"] = merged_prefs["recommended_count"]
            state["is_count_explicit"] = True
        else:
            state["is_count_explicit"] = False

        if interview_result.is_sufficient:
            print(
                f"      ✅ [Handover] 정보 확보 완료! Researcher로 전달: {json.dumps(merged_prefs, ensure_ascii=False)}",
                flush=True,
            )
            return {
                "next_step": "researcher",
                "user_preferences": merged_prefs,
                "recommended_count": merged_prefs.get("recommended_count"),  # [★수정] 반환값에 명시적으로 포함
                "is_count_explicit": merged_prefs.get("recommended_count") is not None,  # [★추가] 명시적 요청 여부
                "status": "모든 정보가 확인되었습니다. 추천 전략을 수립합니다...",
                "active_mode": None,
                "question_count": question_count,
                "fallback_triggered": False,
                "frame_id": frame_id,
                "recommended_history": new_recommended_history if new_recommended_history is not None else state.get("recommended_history", []),
                "exclude_brands": session_exclude_brands,  # [★추가] 세션 레벨 제외 브랜드 유지
            }

        return {
            "messages": [AIMessage(content=interview_result.response_message)],
            "user_preferences": merged_prefs,
            "recommended_count": merged_prefs.get("recommended_count"),  # [★수정] 반환값에 명시적으로 포함
            "is_count_explicit": merged_prefs.get("recommended_count") is not None,  # [★추가] 명시적 요청 여부
            "active_mode": "interviewer",
            "next_step": "end",
            "question_count": question_count,
            "fallback_triggered": False,
            "frame_id": frame_id,
            "recommended_history": new_recommended_history if new_recommended_history is not None else state.get("recommended_history", []),
            "exclude_brands": session_exclude_brands,  # [★추가] 세션 레벨 제외 브랜드 유지
        }
    except Exception as e:
        print(f"Interviewer Error: {e}")
        return {"next_step": "writer", "question_count": question_count, "fallback_triggered": False}


# ==========================================
# [REMOVED] Old researcher_node and writer_node
# These have been replaced by parallel_reco_node which consolidates
# both functionalities with FCFS streaming.
# ==========================================


def _normalize_section_boundary(previous_text: str, next_text: str) -> str:
    if not previous_text or not next_text:
        return next_text
    if not next_text.lstrip().startswith("##"):
        return next_text
    prev_trimmed = previous_text.rstrip()
    if prev_trimmed.endswith("---") and not previous_text.endswith("\n"):
        if not next_text.startswith("\n"):
            return f"\n{next_text}"
    return next_text


def _merge_unique_ids(*iterables: List[int]) -> List[int]:
    merged: List[int] = []
    seen: Set[int] = set()
    for iterable in iterables:
        if not iterable:
            continue
        for value in iterable:
            if value is None:
                continue
            if value in seen:
                continue
            seen.add(value)
            merged.append(value)
    return merged


def _extract_saved_ids(messages: List[Any]) -> List[int]:
    save_refs = extract_save_refs(messages or [])
    saved_ids: List[int] = []
    for ref in save_refs:
        value = ref.get("id")
        if isinstance(value, int):
            saved_ids.append(value)
    return saved_ids


class RecoSearcher:
    def __init__(
        self,
        *,
        member_id: int,
        user_prefs: Dict[str, Any],
        researcher_prompt: str,
        plan_llm: Any,
        session_exclude_ids: Set[int],
        selection_lock: asyncio.Lock,
        batch_selected_ids: Set[int],
        brand_counts: Dict[str, int],
        search_fn: Any,
    ) -> None:
        self.member_id = member_id
        self.user_prefs = user_prefs
        self.current_context = json.dumps(user_prefs, ensure_ascii=False)
        self.researcher_prompt = researcher_prompt
        self.plan_llm = plan_llm
        self.session_exclude_ids = session_exclude_ids
        self.selection_lock = selection_lock
        self.batch_selected_ids = batch_selected_ids
        self.brand_counts = brand_counts
        self.search_fn = search_fn
        self.user_requested_brand = bool(
            user_prefs.get("brand") or user_prefs.get("reference_brand")
        )

    async def generate_user_label(self, plan_reason: str) -> str:
        """
        Generate user-friendly strategy label using LLM with denylist validation.

        Args:
            plan_reason: Strategy reason/intent
            plan_strategy_name: Internal strategy name (for context only)

        Returns:
            User-friendly label string
        """
        user_prefs_str = json.dumps(self.user_prefs, ensure_ascii=False)

        label_messages = [
            SystemMessage(
                content="당신은 향수 추천 전략을 사용자 친화적인 한 문장으로 표현하는 전문가입니다."
            ),
            HumanMessage(
                content=(
                    f"사용자 정보: {user_prefs_str}\n"
                    f"전략 의도: {plan_reason}\n\n"
                    "위 정보를 바탕으로, 사용자에게 보여줄 전략명을 작성하세요.\n\n"
                    "요구사항:\n"
                    "- 한 문장으로 작성 (예: \"강인하고 자신감 있는 첫인상\", \"우아하고 세련된 분위기\")\n"
                    "- 첫인상/무드 중심 표현 사용\n"
                    "- 다음 단어는 절대 사용 금지: 전략, 전략적, 이미지 강조, 이미지 보완, 이미지 반전\n\n"
                    "전략명:"
                )
            ),
        ]

        try:
            response = await SMART_LLM.ainvoke(
                label_messages, config={"tags": ["internal_helper"]}
            )
            user_label = response.content.strip()

            if not has_forbidden_words(user_label):
                return user_label

            retry_messages = [
                SystemMessage(
                    content="당신은 향수 추천 전략을 사용자 친화적인 한 문장으로 표현하는 전문가입니다."
                ),
                HumanMessage(
                    content=(
                        "이전 응답에 금지어가 포함되어 있습니다.\n\n"
                        "다시 한번 작성하세요. 절대 사용하면 안 되는 단어: 전략, 전략적, 이미지 강조, 이미지 보완, 이미지 반전\n\n"
                        f"사용자 정보: {user_prefs_str}\n"
                        f"전략 의도: {plan_reason}\n\n"
                        "전략명:"
                    )
                ),
            ]

            retry_response = await SMART_LLM.ainvoke(
                retry_messages, config={"tags": ["internal_helper"]}
            )
            user_label = retry_response.content.strip()

            if not has_forbidden_words(user_label):
                return user_label
        except Exception as e:
            print(f"[WARNING] User label generation failed: {e}", flush=True)

        return random.choice(UserFriendlyStrategyLabels.SAFE_LABELS)

    async def _snapshot_exclude_ids(self) -> List[int]:
        async with self.selection_lock:
            batch_ids = set(self.batch_selected_ids)
        return list(self.session_exclude_ids | batch_ids)

    async def _select_candidate(
        self, candidates: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        async with self.selection_lock:
            for candidate in candidates:
                candidate_id = candidate.get("id")
                if candidate_id is None:
                    continue
                try:
                    perfume_id = int(candidate_id)
                except (TypeError, ValueError):
                    continue
                brand = candidate.get("brand", "")
                if perfume_id in self.session_exclude_ids:
                    continue
                if perfume_id in self.batch_selected_ids:
                    continue
                if not self.user_requested_brand:
                    if self.brand_counts.get(brand, 0) >= 2:
                        continue
                self.batch_selected_ids.add(perfume_id)
                self.brand_counts[brand] = self.brand_counts.get(brand, 0) + 1
                candidate = dict(candidate)
                candidate["id"] = perfume_id
                return candidate
        return None

    async def _run_search(
        self,
        h_filters: Dict[str, Any],
        s_filters: Dict[str, Any],
        *,
        exclude_ids: List[int],
        query_text: str,
        rank_mode: str,
    ) -> Any:
        try:
            return await self.search_fn(
                h_filters,
                s_filters,
                exclude_ids=exclude_ids,
                query_text=query_text,
                rank_mode=rank_mode,
            )
        except TypeError as e:
            if "rank_mode" not in str(e):
                raise
            return await self.search_fn(
                h_filters,
                s_filters,
                exclude_ids=exclude_ids,
                query_text=query_text,
            )

    async def prepare_strategy(
        self, strategy_name: str, priority: int, rank_mode: str
    ) -> Dict[str, Any]:
        plan_messages = [
            SystemMessage(content=self.researcher_prompt),
            HumanMessage(
                content=(
                    f"사용자 요청 데이터: {self.current_context}\n"
                    f"전략 이름: {strategy_name}\n"
                    f"우선순위: {priority}\n"
                    "위 데이터를 바탕으로 전략을 수립해 주세요."
                )
            ),
        ]

        try:
            plan = await self.plan_llm.ainvoke(
                plan_messages, config={"tags": ["internal_helper"]}
            )
        except Exception as e:
            return {
                "error": True,
                "error_type": "llm_error",
                "error_detail": str(e),
                "section_data": None,
                "priority": priority,
            }

        user_label = await self.generate_user_label(plan.reason)

        try:
            h_filters = plan.hard_filters.model_dump(exclude_none=True)
            s_filters = plan.strategy_filters.model_dump(exclude_none=True)
        except Exception:
            h_filters = {}
            s_filters = {}

        try:
            exclude_ids = await self._snapshot_exclude_ids()
            # 로그: 전략별 검색 시 사용되는 제외 ID
            print(f"   🔍 [Strategy {priority}] Searching with {len(exclude_ids)} exclusions", flush=True)
            candidates, _match_type = await self._run_search(
                h_filters,
                s_filters,
                exclude_ids=exclude_ids,
                query_text=plan.reason,
                rank_mode=rank_mode,
            )
        except Exception as e:
            return {
                "error": True,
                "error_type": "tool_error",
                "error_detail": str(e),
                "section_data": None,
                "priority": priority,
            }

        if not candidates:
            return {
                "error": True,
                "error_type": "no_results",
                "error_detail": "No candidates returned",
                "section_data": None,
                "priority": priority,
            }

        selected_perfume = await self._select_candidate(candidates)

        # 로그: 선택된 향수
        if selected_perfume:
            print(f"   ✅ [Strategy {priority}] Selected perfume ID: {selected_perfume.get('id')}", flush=True)

        if not selected_perfume:
            try:
                exclude_ids = await self._snapshot_exclude_ids()
                # 로그: 재시도 시 제외 ID
                print(f"   🔄 [Strategy {priority}] Retry with {len(exclude_ids)} exclusions", flush=True)
                candidates, _match_type = await self._run_search(
                    h_filters,
                    s_filters,
                    exclude_ids=exclude_ids,
                    query_text=plan.reason,
                    rank_mode=rank_mode,
                )
            except Exception as e:
                return {
                    "error": True,
                    "error_type": "tool_error",
                    "error_detail": str(e),
                    "section_data": None,
                    "priority": priority,
                }
            selected_perfume = await self._select_candidate(candidates)

            # 로그: 재시도 후 선택된 향수
            if selected_perfume:
                print(f"   ✅ [Strategy {priority}] Selected perfume ID (retry): {selected_perfume.get('id')}", flush=True)

        if not selected_perfume:
            return {
                "error": True,
                "error_type": "no_candidates",
                "error_detail": "No candidates selected",
                "section_data": None,
                "priority": priority,
            }

        save_recommendation_log(
            member_id=self.member_id,
            perfumes=[selected_perfume],
            reason=plan.reason,
        )

        perfume_id = int(selected_perfume["id"])
        perfume_name = selected_perfume.get("name") or selected_perfume.get(
            "perfume_name"
        )
        perfume_brand = selected_perfume.get("brand") or selected_perfume.get(
            "perfume_brand"
        )
        perfume_name = str(perfume_name) if perfume_name is not None else "Unknown"
        perfume_brand = str(perfume_brand) if perfume_brand is not None else "Unknown"

        accords_text = selected_perfume.get("accords") or ""
        best_review = selected_perfume.get("best_review") or ""
        accord_value = f"{accords_text}\n[Best Review]: {best_review}".strip()

        strategy_result = StrategyResult(
            strategy_name=plan.strategy_name,
            strategy_keyword=plan.strategy_keyword,
            strategy_reason=plan.reason,
            perfumes=[
                PerfumeDetail(
                    id=perfume_id,
                    perfume_name=perfume_name,
                    perfume_brand=perfume_brand,
                    accord=accord_value,
                    notes=PerfumeNotes(
                        top=selected_perfume.get("top_notes") or "N/A",
                        middle=selected_perfume.get("middle_notes") or "N/A",
                        base=selected_perfume.get("base_notes") or "N/A",
                    ),
                    image_url=selected_perfume.get("image_url"),
                    gender=selected_perfume.get("gender", "Unisex"),
                    season=selected_perfume.get("seasons") or "All",
                    occasion=selected_perfume.get("occasions") or "Any",
                )
            ],
        )

        section_data = {
            "user_preferences": self.user_prefs,
            "strategy": {
                "internal_id": plan.strategy_name,
                "user_label": user_label,
                "reason": plan.reason,
                "keywords": plan.strategy_keyword,
                "priority": priority,
            },
            "perfume": strategy_result.perfumes[0].dict(),
        }

        return {
            "section_data": section_data,
            "priority": priority,
            "perfume_id": perfume_id,
        }


class RecoWriter:
    def __init__(self, state: AgentState) -> None:
        self.state = state
        self.user_mode = state.get("user_mode", "BEGINNER")

    def _build_expression_text(self, section_data: Dict[str, Any]) -> str:
        perfume_data = section_data.get("perfume", {})
        notes_data = perfume_data.get("notes", {})
        accord_str = perfume_data.get("accord", "")

        all_notes: List[str] = []
        for note_type in ["top", "middle", "base"]:
            note_str = notes_data.get(note_type, "")
            if note_str and note_str != "N/A":
                all_notes.extend([n.strip() for n in note_str.split(",")])

        accords: List[str] = []
        if accord_str:
            accord_part = accord_str.split("[Best Review]")[0].strip()
            accords = [a.strip() for a in accord_part.split(",") if a.strip()]

        loader = ExpressionLoader()

        expression_guide: List[str] = []

        if all_notes:
            expression_guide.append("### 노트 표현 가이드")
            for note in all_notes[:10]:
                desc = loader.get_note_desc(note)
                if desc:
                    expression_guide.append(f"- {note}: {desc}")

        if accords:
            expression_guide.append("\n### 어코드 표현 가이드")
            for accord in accords[:10]:
                desc = loader.get_accord_desc(accord)
                if desc:
                    expression_guide.append(f"- {accord}: {desc}")

        return "\n".join(expression_guide) if expression_guide else ""

    async def generate_section(
        self,
        prepared_data: Dict[str, Any],
        display_priority: int,
        *,
        is_first: bool,
        is_last: bool,
    ) -> Optional[str]:
        if not prepared_data:
            return None

        section_data = prepared_data.get("section_data")
        if not section_data:
            return None

        expression_text = self._build_expression_text(section_data)

        data_ctx = json.dumps(section_data, ensure_ascii=False, indent=2)

        if self.user_mode == "EXPERT":
            section_system = WRITER_RECOMMENDATION_PROMPT_EXPERT_SINGLE
        else:
            section_system = WRITER_RECOMMENDATION_PROMPT_SINGLE

        content_parts = [
            f"[섹션 번호]: {display_priority}",
            f"[도입부 포함]: {'예' if is_first else '아니오'}",
            f"[마지막 섹션 여부]: {'예' if is_last else '아니오'}",
            (
                f"[출력 규칙]: 도입부 포함이 '아니오'이면 첫 줄을 반드시 '## {display_priority}.'로 시작하고 도입부 문장을 쓰지 마세요."
            ),
        ]

        # [★추가] 마지막 섹션일 때 종합 의견 추가 지시
        if is_last:
            content_parts.append(
                "\n[마지막 섹션 지시사항]: 이 섹션이 마지막이므로, 향수 설명과 [[SAVE:...]] 태그를 모두 작성한 후 "
                "구분선(---)을 추가하고, 그 아래에 향수 사용에 대한 친절한 종합 의견을 2-3문장으로 작성해주세요. "
                "예: '마지막으로, 향을 처음 들이실 땐 1~2번만 가볍게 뿌려서 내 살결에 어떻게 남는지부터 확인해보세요. "
                "데일리일수록 \"과하지 않은 잔향\"이 가장 오래 갑니다.'"
            )


        if expression_text:
            content_parts.append(f"\n[감각 표현 참고]:\n{expression_text}")

        content_parts.append(f"\n[참고 데이터]:\n{data_ctx}")

        messages = [SystemMessage(content=section_system)] + self.state.get(
            "messages", []
        ) + [HumanMessage(content="\n".join(content_parts))]

        try:
            result_text = ""
            if hasattr(SUPER_SMART_LLM, "astream"):
                async for chunk in SUPER_SMART_LLM.astream(messages):
                    if chunk.content:
                        result_text += chunk.content
            else:
                response = await SUPER_SMART_LLM.ainvoke(messages)
                result_text = response.content or ""

            if result_text:
                header_index = result_text.find("##")
                if display_priority != 1 and header_index > 0:
                    result_text = result_text[header_index:]
                if result_text.startswith("##"):
                    lines = result_text.splitlines()
                    header_line = lines[0]
                    after = header_line[2:].lstrip()
                    idx = 0
                    while idx < len(after) and after[idx].isdigit():
                        idx += 1
                    if idx < len(after) and after[idx] == ".":
                        idx += 1
                    if idx < len(after) and after[idx] == " ":
                        idx += 1
                    rest = after[idx:]
                    lines[0] = (
                        f"## {display_priority}. {rest}"
                        if rest
                        else f"## {display_priority}."
                    )
                    result_text = "\n".join(lines)
            if result_text and not result_text.rstrip().endswith("---"):
                result_text = f"{result_text.rstrip()}\n---"
            return result_text
        except Exception as e:
            logger.error(f"Writer error: {e}")
            return None


async def parallel_reco_node(state: AgentState):
    member_id = state.get("member_id", 0)
    user_prefs = state.get("user_preferences", {})
    current_context = json.dumps(user_prefs, ensure_ascii=False)

    use_case = infer_use_case(user_prefs)

    personalization = {}
    if use_case == "SELF" and member_id > 0:
        personalization = get_personalization_summary(member_id) or {}
        if personalization.get("summary_text"):
            print(f"🎯 [Personalization] {personalization['summary_text']}", flush=True)
    else:
        if use_case == "GIFT":
            print(
                "🎁 [GIFT Mode] Personalization disabled for gift recommendations",
                flush=True,
            )

    researcher_prompt = RESEARCHER_SYSTEM_PROMPT
    if personalization.get("summary_text"):
        researcher_prompt += (
            "\n\n## 사용자 취향 정보\n"
            f"{personalization['summary_text']}\n\n"
            "이 정보를 참고하되, 현재 요청 조건(브랜드/계절/대상 등)이 최우선입니다."
        )

    plan_llm = SMART_LLM.with_structured_output(SearchStrategyPlan)

    recommended_history = state.get("recommended_history") or []
    saved_ids = _extract_saved_ids(state.get("messages", []))
    if not recommended_history and saved_ids:
        recommended_history = saved_ids
    merged_history = _merge_unique_ids(recommended_history, saved_ids)

    session_exclude_ids: Set[int] = set(merged_history)

    # 로그: 히스토리 기반 제외 ID
    if session_exclude_ids:
        print(f"🚫 [Exclude] History-based exclusions: {sorted(list(session_exclude_ids))}", flush=True)

    if use_case == "SELF":
        disliked_ids = []
        for disliked in personalization.get("disliked_perfumes", []):
            perfume_id = disliked.get("id")
            if perfume_id:
                session_exclude_ids.add(perfume_id)
                disliked_ids.append(perfume_id)

        # 로그: 싫어하는 향수 제외 ID
        if disliked_ids:
            print(f"🚫 [Exclude] Disliked perfumes: {sorted(disliked_ids)}", flush=True)

    # 로그: 최종 제외 ID 총합
    if session_exclude_ids:
        print(f"🚫 [Exclude] Total session exclusions: {len(session_exclude_ids)} IDs", flush=True)
    else:
        print(f"✅ [Exclude] No exclusions for this session", flush=True)

    selection_lock = asyncio.Lock()
    batch_selected_ids: Set[int] = set()
    brand_counts: Dict[str, int] = {}

    rank_mode = "DEFAULT"
    user_query = state.get("user_query", "")
    trending_keywords = [
        "유행",
        "인기",
        "트렌딩",
        "요즘",
        "잘나가는",
        "베스트",
        "trending",
        "popular",
        "hot",
    ]
    if any(k in user_query for k in trending_keywords):
        rank_mode = "POPULAR"
        print(f"🔥 [Ranking] Mode: {rank_mode}", flush=True)

    requested_count = state.get("recommended_count")
    if requested_count is None:
        parsed = parse_recommended_count(state.get("user_query", ""))
        requested_count = parsed if parsed is not None else 3

    target_count = normalize_recommended_count(requested_count)

    print(f"🔢 [Count] Target recommendations: {target_count}", flush=True)

    searcher = RecoSearcher(
        member_id=member_id,
        user_prefs=user_prefs,
        researcher_prompt=researcher_prompt,
        plan_llm=plan_llm,
        session_exclude_ids=session_exclude_ids,
        selection_lock=selection_lock,
        batch_selected_ids=batch_selected_ids,
        brand_counts=brand_counts,
        search_fn=smart_search_with_retry_async,
    )
    writer = RecoWriter(state)

    prep_tasks = [
        asyncio.create_task(searcher.prepare_strategy(f"STRAT_{i}", i, rank_mode))
        for i in range(1, target_count + 1)
    ]

    errors_encountered: List[Dict[str, str]] = []
    pending_result: Optional[Dict[str, Any]] = None
    output_texts: List[str] = []
    prepared_data_list: List[Dict[str, Any]] = []

    for future in asyncio.as_completed(prep_tasks):
        try:
            result = await future
        except Exception as e:
            errors_encountered.append({"type": "exception", "detail": str(e)})
            continue

        if not result:
            errors_encountered.append(
                {"type": "unknown", "detail": "Strategy returned empty result"}
            )
            continue

        if result.get("error"):
            error_type = result.get("error_type", "unknown")
            error_detail = result.get("error_detail", "")
            if error_type not in {"no_results", "no_candidates"}:
                errors_encountered.append(
                    {"type": error_type, "detail": error_detail}
                )
            continue

        if pending_result:
            section_number = len(output_texts) + 1
            output_text = await writer.generate_section(
                pending_result,
                section_number,
                is_first=section_number == 1,
                is_last=False,
            )
            if output_text:
                output_texts.append(output_text)
                prepared_data_list.append(pending_result)
            else:
                errors_encountered.append(
                    {
                        "type": "writer_error",
                        "detail": "Writer failed to produce output",
                    }
                )

        pending_result = result

    if pending_result:
        section_number = len(output_texts) + 1
        output_text = await writer.generate_section(
            pending_result,
            section_number,
            is_first=section_number == 1,
            is_last=True,
        )
        if output_text:
            output_texts.append(output_text)
            prepared_data_list.append(pending_result)
        else:
            errors_encountered.append(
                {
                    "type": "writer_error",
                    "detail": "Writer failed to produce output",
                }
            )

    if output_texts:
        full_text = output_texts[0]
        for next_text in output_texts[1:]:
            next_text = _normalize_section_boundary(full_text, next_text)
            full_text = f"{full_text}\n\n{next_text}"

        # [★추가] 스트리밍 후 안내 메시지 (케이스 1 + 케이스 2)
        actual_count = len(output_texts)
        is_explicit = state.get("is_count_explicit", False)

        # 케이스 1: 과다 요청 메시지
        pre_notice_msg = generate_pre_notice(requested_count, is_explicit)
        # 케이스 2: 부분 실패 메시지
        post_notice_msg = generate_post_notice(requested_count, actual_count, is_explicit)

        # 하나만 선택해서 추가 (우선순위: 케이스 1 > 케이스 2)
        notice_msg = ""
        if pre_notice_msg:
            # 케이스 1: 과다 요청 (우선순위 높음)
            notice_msg = pre_notice_msg.strip()
        elif post_notice_msg:
            # 케이스 2: 부분 실패 (과다 요청이 아닐 때만)
            notice_msg = post_notice_msg.strip()

        # [★수정] 종합 의견은 LLM이 마지막 섹션에서 자동 생성 (하드코딩 제거)
        # 안내 메시지만 조건부로 추가
        if notice_msg:
            full_text = f"{full_text}\n{notice_msg}"
            print(f"💬 [Notice] Added notice to end of response", flush=True)
    else:
        fallback_messages = [
            SystemMessage(content=WRITER_FAILURE_PROMPT),
            HumanMessage(content=f"사용자 정보: {current_context}"),
        ]
        fallback_response = await SUPER_SMART_LLM.ainvoke(fallback_messages)
        full_text = fallback_response.content

    if len(output_texts) >= 1:
        chat_outcome_status = "OK"
        if len(output_texts) < target_count:
            chat_outcome_reason_code = "partial_results"
            chat_outcome_reason_detail = (
                f"Generated {len(output_texts)}/{target_count} sections"
            )
        else:
            chat_outcome_reason_code = "success"
            chat_outcome_reason_detail = (
                f"Generated {len(output_texts)}/{target_count} sections"
            )
    elif errors_encountered:
        chat_outcome_status = "ERROR"
        chat_outcome_reason_code = errors_encountered[0]["type"]
        chat_outcome_reason_detail = (
            f"{len(errors_encountered)} errors: {errors_encountered[0]['detail'][:100]}"
        )
    else:
        chat_outcome_status = "NO_RESULTS"
        chat_outcome_reason_code = "no_candidates"
        chat_outcome_reason_detail = "All strategies failed to find suitable perfumes"

    current_batch_ids: List[int] = []
    for prepared_data in prepared_data_list:
        perfume_id = prepared_data.get("perfume_id")
        if perfume_id:
            current_batch_ids.append(perfume_id)

    # 로그: 이번 배치에서 추천된 향수 ID들
    if current_batch_ids:
        print(f"✨ [Batch] Recommended perfume IDs in this batch: {current_batch_ids}", flush=True)

    updated_history = _merge_unique_ids(merged_history, current_batch_ids)

    # 로그: 업데이트된 전체 히스토리
    if updated_history != merged_history:
        print(f"📚 [History] Updated total history: {len(updated_history)} IDs", flush=True)

    # [★추가] DB에 recommended_history 저장 (thread_id 안전성 검증)
    thread_id = state.get("thread_id")
    if thread_id and current_batch_ids:
        from .database import update_recommended_history
        try:
            update_recommended_history(thread_id, current_batch_ids, max_size=100)
        except Exception as e:
            print(f"   ⚠️ [DB] Failed to save recommended_history: {e}", flush=True)
            # DB 저장 실패해도 state의 recommended_history는 유지됨 (메모리 fallback)

    return {
        "messages": [AIMessage(content=full_text)],
        "next_step": "end",
        "recommended_history": updated_history,
        "user_preferences": user_prefs,
        "chat_outcome_status": chat_outcome_status,
        "chat_outcome_reason_code": chat_outcome_reason_code,
        "chat_outcome_reason_detail": chat_outcome_reason_detail,
    }


def parallel_reco_result_router(state: AgentState):
    """
    chat_outcome_status 값에 따라 다음 노드로 라우팅합니다.
    
    Returns:
        다음 노드 이름 ('parallel_reco_ok_writer' | 'parallel_reco_no_results' | 'parallel_reco_error')
    """
    status = state.get("chat_outcome_status", "OK")
    
    print(f"\n🔀 [Reco Router] Status: {status}", flush=True)
    
    if status == "NO_RESULTS":
        return "parallel_reco_no_results"
    elif status == "ERROR":
        return "parallel_reco_error"
    else:
        return "parallel_reco_ok_writer"


async def parallel_reco_ok_writer(_state: AgentState):
    """
    OK 상태일 때 - 이미 parallel_reco_node에서 메시지 생성 완료.
    추가 처리 없이 그대로 반환.
    """
    print(f"\n✅ [Reco OK Writer] 정상 추천 완료", flush=True)
    return {}


async def parallel_reco_no_results(state: AgentState):
    """
    NO_RESULTS 상태일 때 - WRITER_FAILURE_PROMPT 사용하여 대안 제시.
    """
    print(f"\n⚠️ [Reco No Results] 검색 결과 없음 처리", flush=True)
    
    user_prefs = state.get("user_preferences", {})
    current_context = json.dumps(user_prefs, ensure_ascii=False)
    
    fallback_messages = [
        SystemMessage(content=WRITER_FAILURE_PROMPT),
        HumanMessage(content=f"사용자 정보: {current_context}")
    ]
    
    fallback_response = await SUPER_SMART_LLM.ainvoke(fallback_messages)
    
    return {"messages": [AIMessage(content=fallback_response.content)]}


async def parallel_reco_error(_state: AgentState):
    """
    ERROR 상태일 때 - 고정 문구 출력 (내부 오류 노출 금지).
    """
    print(f"\n❌ [Reco Error] 기술적 오류 처리", flush=True)

    error_msg = "죄송합니다. 현재 알 수 없는 오류가 발생하였습니다. 잠시 후 다시 시도해 주세요. 🙏"

    return {"messages": [AIMessage(content=error_msg)]}


async def out_of_scope_handler(_state: AgentState):
    """
    향수와 관련 없는 질문 처리 - 고정 메시지 반환 (LLM 호출 없음).
    """
    print(f"\n🚫 [Out of Scope] 향수 관련 없는 질문 처리", flush=True)

    fixed_msg = "죄송하지만 저는 향수 큐레이션 챗봇이기 때문에 향수 추천이나 정보제공 이외의 답변을 드리기는 어렵습니다."

    return {
        "messages": [AIMessage(content=fixed_msg)],
        "chat_outcome_status": "OUT_OF_SCOPE"
    }


async def unsupported_request_handler(_state: AgentState):
    """
    DB에 없는 속성 요청 처리 - 카테고리별 커스터마이징된 고정 메시지 반환.
    """
    print(f"\n⚠️ [Unsupported Request] DB 미지원 속성 요청 처리", flush=True)

    category = _state.get("unsupported_category", "")

    # 카테고리별 메시지 (이유 + 대안)
    category_messages = {
        "제형": {
            "reason": "워터 퍼퓸, 오일 퍼퓸, 고체 향수 등 제형별 검색은 현재 지원하지 않습니다.",
            "alternative": "대신 원하시는 느낌(가벼운, 시원한, 물기 있는 등)을 말씀해주시면 비슷한 향수를 추천해드리겠습니다."
        },
        "성능": {
            "reason": "발향력, 지속력, 잔향 등 성능 정보는 데이터베이스에 없습니다.",
            "alternative": "대신 계절이나 상황에 맞는 향수를 추천해드릴 수 있습니다."
        },
        "가격": {
            "reason": "가격대별 검색은 지원하지 않습니다.",
            "alternative": "브랜드나 분위기로 검색하시면 원하시는 스타일을 찾으실 수 있습니다."
        },
        "레이어링": {
            "reason": "레이어링이나 조합 추천은 현재 지원하지 않습니다.",
            "alternative": "개별 향수 추천은 가능합니다! 레이어링 관련 질문은 Scentence의 레이어링 관련 서비스에서 진행해주세요!"
        },
        "구매정보": {
            "reason": "구매처나 매장 정보는 제공하지 않습니다.",
            "alternative": "특정 향수 정보를 알려드릴 수 있습니다."
        },
        "물리적": {
            "reason": "용량, 크기 등 물리적 정보는 보유하고 있지 않습니다.",
            "alternative": "향수의 특성(어코드, 노트 등)으로 검색해드릴 수 있습니다."
        },
        "추천_이유": {
            "reason": "추천 기준이나 이유에 대한 정보는 제공되지 않습니다.",
            "alternative": "대신 추천된 향수의 특성(어코드, 노트 등)에 대해 자세히 설명해드릴까요?"
        },
        "브랜드_전체": {
            "reason": "브랜드 전체 설명이나 브랜드의 모든 향수 나열은 지원하지 않습니다.",
            "alternative": "특정 향수명을 말씀해주시면 해당 향수에 대해 상세히 설명해드리겠습니다."
        },
        "향수_비교": {
            "reason": "두 향수를 비교하는 기능은 현재 지원하지 않습니다.",
            "alternative": "각 향수의 특성을 개별적으로 설명해드릴까요?"
        },
    }

    msg_data = category_messages.get(category, {
        "reason": "해당 요청은 현재 지원하지 않습니다.",
        "alternative": "다른 방식으로 질문해주시면 도움드리겠습니다."
    })
    
    specific_msg = f"죄송합니다. {msg_data['reason']}\n\n💡 {msg_data['alternative']}"

    return {
        "messages": [AIMessage(content=specific_msg)],
        "chat_outcome_status": "UNSUPPORTED_REQUEST"
    }


# ==========================================
# 4. Graph Build
# ==========================================
workflow = StateGraph(AgentState)

workflow.add_node("pre_validator", pre_validator_node)
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("interviewer", interviewer_node)
# workflow.add_node("researcher", researcher_node)  # Replaced by parallel_reco
# workflow.add_node("writer", writer_node)  # Replaced by parallel_reco
workflow.add_node("parallel_reco", parallel_reco_node)

# [Wave 2-3] Add status-based handler nodes
workflow.add_node("parallel_reco_ok_writer", parallel_reco_ok_writer)
workflow.add_node("parallel_reco_no_results", parallel_reco_no_results)
workflow.add_node("parallel_reco_error", parallel_reco_error)
workflow.add_node("out_of_scope_handler", out_of_scope_handler)
workflow.add_node("unsupported_request_handler", unsupported_request_handler)
workflow.add_node("info_retrieval_subgraph", call_info_graph_wrapper)

workflow.add_edge(START, "pre_validator")

# Pre-validator routing
workflow.add_conditional_edges(
    "pre_validator",
    lambda x: x.get("validation_result", "supported"),
    {
        "supported": "supervisor",
        "unsupported": "unsupported_request_handler"
    }
)

workflow.add_conditional_edges(
    "supervisor",
    lambda x: x["next_step"],
    {
        "interviewer": "interviewer",
        "info_retrieval": "info_retrieval_subgraph",
        "writer": "out_of_scope_handler",  # Out-of-scope questions (non-perfume related)
    },
)

workflow.add_conditional_edges(
    "interviewer",
    lambda x: x["next_step"],
    {"end": END, "researcher": "parallel_reco", "writer": "parallel_reco"},
)

# workflow.add_edge("researcher", "writer")  # Old flow - replaced
# workflow.add_edge("writer", END)  # Old flow - replaced

# [Wave 2-3 - Pattern A] parallel_reco → status 기반 직접 분기
workflow.add_conditional_edges(
    "parallel_reco",
    parallel_reco_result_router,
    {
        "parallel_reco_ok_writer": "parallel_reco_ok_writer",
        "parallel_reco_no_results": "parallel_reco_no_results",
        "parallel_reco_error": "parallel_reco_error",
    },
)

# [Wave 2-3] All status nodes → END
workflow.add_edge("parallel_reco_ok_writer", END)
workflow.add_edge("parallel_reco_no_results", END)
workflow.add_edge("parallel_reco_error", END)
workflow.add_edge("out_of_scope_handler", END)
workflow.add_edge("unsupported_request_handler", END)
workflow.add_edge("info_retrieval_subgraph", END)

checkpointer = MemorySaver()
app_graph = workflow.compile(checkpointer=checkpointer)
