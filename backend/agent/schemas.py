# backend/agent/schemas.py
from typing import List, Optional, Dict, Literal, Annotated, Any
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

# =================================================================
# 1. 공통 상태 및 요청 (Common State)
# =================================================================
class ChatRequest(BaseModel):
    user_query: str = Field(description="사용자가 입력한 질문 텍스트")
    thread_id: Optional[str] = Field(None, description="세션 관리를 위한 스레드 ID")
    member_id: int = Field(0, description="로그인한 사용자 ID")
    user_mode: Optional[str] = Field("BEGINNER", description="사용자 모드 (BEGINNER 또는 EXPERT)")
    recommended_count: Optional[int] = Field(
        None, description="추천 개수 (명시 시 파싱보다 우선 적용)"
    )


class AgentState(Dict):
    """
    [최적화] Annotated와 add_messages를 추가하여 대화 히스토리가
    노드 실행 시마다 초기화되지 않고 누적(Append)되도록 합니다.
    """

    messages: Annotated[List[BaseMessage], add_messages]
    user_query: str
    active_mode: Optional[str]
    next_step: Optional[str]
    user_preferences: Optional[Dict]
    research_results: Optional[List]
    member_id: Optional[int]
    user_mode: Optional[str]
    status: Optional[str]
    
    # [★추가] 정보 검색(Info Graph) 에이전트와 상태를 공유하기 위한 필드
    info_type: Optional[str] 
    target_name: Optional[str]
    
    # [★추가] 인터뷰어 질문 상한 및 폴백 추적
    question_count: Optional[int]
    fallback_triggered: Optional[bool]
    
    # [★추가] 세션 레벨 추천 다양성 추적
    recommended_history: Optional[List[int]]

    # [★추가] 추천 개수 요청
    recommended_count: Optional[int]
    is_count_explicit: Optional[bool]  # 사용자가 명시적으로 개수를 요청했는지

    # [★추가] 프레임 컨텍스트/제약 메타데이터
    frame_id: str | None = None
    constraint_scope: Literal["FRAME", "SESSION", "PROFILE"] | None = None
    constraint_source: Literal["explicit_user", "inferred", "system_default"] | None = None

    # [★Wave 2] 상태 분류 필드 (OK/NO_RESULTS/ERROR 통합 관리)
    chat_outcome_status: Optional[Literal["OK","NO_RESULTS","ERROR"]]
    chat_outcome_reason_code: Optional[str]  # 예: "partial_results", "tool_error", "no_candidates"
    chat_outcome_reason_detail: Optional[str]  # 사용자 노출 금지, 로그/테스트용

    # [★추가] DB 백업을 위한 스레드 ID
    thread_id: Optional[str]

    # [★추가] Pre-Validator 결과 필드
    validation_result: Optional[str] = None  # "supported" | "unsupported"
    unsupported_category: Optional[str] = None  # "제형", "성능", "가격" 등
    unsupported_reason: Optional[str] = None


# =================================================================
# 2. 인터뷰 및 라우팅 (Interviewer & Router)
# =================================================================
class UserPreferences(BaseModel):
    """인터뷰어가 사용자 대화에서 추출한 핵심 정보입니다."""
    target: str = Field(description="대상 정보 (예: 20대 여성, 30대 남성 등)")
    gender: str = Field(description="성별 정보 (Women, Men, Unisex)")

    reference_brand: Optional[str] = Field(None, description="참고 브랜드 (유사한 향 찾기 - 소프트 필터)")
    brand: Optional[str] = Field(None, description="특정 브랜드 (해당 브랜드만 - 하드 필터)")
    perfume: Optional[str] = Field(None, description="특정 향수")
    situation: Optional[str] = Field(None, description="상황 정보")
    season: Optional[str] = Field(None, description="계절 정보")
    like: Optional[str] = Field(None, description="취향 정보")
    style: Optional[str] = Field(None, description="이미지 정보")

    # [★수정] Accord(계열)와 Note(원료)를 엄격하게 분리
    accord: Optional[str] = Field(None, description="선호하는 향의 분위기나 계열 (예: Woody, Floral, Citrus, Spicy)")
    note: Optional[str] = Field(None, description="구체적으로 선호하는 향 원료 (예: Rose, Vetiver, Sandalwood, Vanilla)")
    
    # [★추가] 추천 개수 (사용자가 명시한 경우)
    recommended_count: Optional[int] = Field(None, description="사용자가 요청한 추천 향수 개수")
    
    # [★추가] 제외 브랜드 (말고/제외/빼고)
    exclude_brands: Optional[List[str]] = Field(None, description="검색에서 제외할 브랜드 목록 (최대 5개, 정규화된 브랜드명)")
    
    # [★추가] 사용 목적 구분 (본인용 vs 선물용)
    use_case: Optional[Literal['SELF', 'GIFT']] = Field(None, description="사용 목적 (SELF: 본인용, GIFT: 선물용)")

class InterviewResult(BaseModel):
    user_preferences: UserPreferences = Field(description="추출된 사용자 선호 정보")
    is_sufficient: bool = Field(description="필수 정보 충족 여부")
    response_message: str = Field(description="안내 멘트")
    is_off_topic: bool = Field(description="주제 이탈 여부")


class RoutingDecision(BaseModel):
    """
    [★수정] Supervisor가 결정할 수 있는 다음 단계입니다.
    - interviewer: 향수 추천 요청인 경우 (정보가 충분하든 부족하든 이쪽으로 보냄)
    - info_retrieval: 특정 향수/노트/어코드에 대한 지식/정보 질문인 경우 (신규)
    - writer: 향수와 관련 없는 질문인 경우 (범위 외 질문, 잡담 등)
    * 'researcher' 선택지가 삭제되었습니다 (Interviewer를 통해서만 진입 가능)
    """

    next_step: Literal["interviewer", "info_retrieval", "writer"] = Field(
        description="질문 의도에 따른 다음 담당 에이전트"
    )


class ValidationResult(BaseModel):
    """
    Pre-Validator가 반환하는 검증 결과.
    요청이 시스템에서 지원 가능한지 판단합니다.
    """
    is_unsupported: bool = Field(
        description="True면 지원 불가능, False면 지원 가능"
    )
    unsupported_category: Optional[str] = Field(
        None,
        description="불가능한 경우 카테고리: '제형', '성능', '가격', '레이어링', '구매정보' 등"
    )
    reason: str = Field(
        description="판단 이유 설명"
    )


# =================================================================
# 3. 리서처 전략 수립 (Researcher Planning) - [변경 없음]
# =================================================================
class HardFilters(BaseModel):
    gender: str = Field(description="성별 (Women, Men, Unisex)")
    brand: Optional[str] = Field(None, description="특정 브랜드 (하드 필터)")
    season: Optional[str] = Field(None, description="계절")
    occasion: Optional[str] = Field(None, description="상황")
    accord: Optional[str] = Field(None, description="어코드")
    note: Optional[str] = Field(None, description="특정 노트")


class StrategyFilters(BaseModel):
    accord: Optional[List[str]] = Field(None, description="향의 분위기")
    occasion: Optional[List[str]] = Field(None, description="상황")
    note: Optional[List[str]] = Field(None, description="구체적 노트")


class SearchStrategyPlan(BaseModel):
    priority: int = Field(description="전략 우선순위")
    strategy_name: str = Field(description="전략 이름 (한글)")
    reason: str = Field(description="전략 의도 (한글)")
    hard_filters: HardFilters = Field(description="필수 필터")
    strategy_filters: StrategyFilters = Field(description="전략 필터")
    strategy_keyword: List[str] = Field(description="핵심 키워드")


class ResearchActionPlan(BaseModel):
    plans: List[SearchStrategyPlan] = Field(description="3가지 검색 전략")


# =================================================================
# 4. 리서처 결과 및 라이터 전달 (Researcher Output) - [변경 없음]
# =================================================================
class PerfumeNotes(BaseModel):
    top: str = Field(description="탑 노트")
    middle: str = Field(description="미들 노트")
    base: str = Field(description="베이스 노트")


class PerfumeDetail(BaseModel):
    id: int = Field(description="향수 고유 ID (DB Primary Key)")
    perfume_name: str = Field(description="향수 이름")
    perfume_brand: str = Field(description="향수 브랜드")
    accord: str = Field(description="주요 어코드")
    season: str = Field(description="추천 계절")
    occasion: str = Field(description="추천 상황")
    gender: str = Field(description="추천 성별")
    notes: PerfumeNotes = Field(description="노트 정보")
    image_url: Optional[str] = Field(None, description="이미지 URL")


class StrategyResult(BaseModel):
    strategy_name: str = Field(description="전략 이름")
    strategy_keyword: List[str] = Field(description="사용된 키워드 리스트")
    strategy_reason: str = Field(description="수립 의도와 이유 (한글)")
    perfumes: List[PerfumeDetail] = Field(description="검색된 향수 리스트")


class ResearcherOutput(BaseModel):
    results: List[StrategyResult] = Field(description="최종 결과 리스트")


# =================================================================
# 5. 정보 검색 전용 스키마 (Info Graph)
# =================================================================
class InfoState(Dict):
    user_query: str
    info_type: Literal["perfume", "note", "accord", "brand", "similarity", "unknown"]
    target_name: str  # 영어명 (기본)
    target_name_kr: Optional[str]  # [Phase 2] 한글명
    target_brand: Optional[str]  # [Phase 2] 브랜드
    target_id: Optional[int]

    search_result: Optional[Dict]
    final_answer: Optional[str]
    fail_msg: Optional[str]
    user_mode: Optional[str]
    info_status: Optional[Literal["OK", "NO_RESULTS", "ERROR"]]
    messages: List[Any]
    info_payload: Optional[Any] = None


class InfoRoutingDecision(BaseModel):
    """사용자 질문이 무엇에 관한 것인지 분류"""

    info_type: Literal["perfume", "note", "accord", "brand", "similarity"] = Field(
        description="질문의 대상 카테고리 (향수, 노트, 어코드, 브랜드, 유사추천)"
    )
    target_brand: Optional[str] = Field(
        None,
        description="[Phase 2] 브랜드 이름 (예: 'Dior', 'Jo Malone', 'Chanel')"
    )
    target_name: str = Field(
        description="[Phase 2] 영어 향수명 (예: 'J'adore', 'Wood Sage & Sea Salt', 'No.5')"
    )
    target_name_kr: Optional[str] = Field(
        None,
        description="[Phase 2] 한글 향수명 - 원본 유지 (예: '자도르', '우드세이지', '넘버5')"
    )
    intent: str = Field(
        description="사용자가 궁금해하는 구체적인 내용 (예: '지속력이 궁금해', '비슷한거 추천해줘')"
    )


# =================================================================
# 6. 도구 입력/분석 스키마 (Tools)
# =================================================================
class LookupNoteInput(BaseModel):
    """노트(향료) 명칭 조회를 위한 입력 스키마"""

    keyword: str = Field(
        description="조회하거나 교정할 향기 키워드 (예: 'Rose', '숲의 향')"
    )


class AdvancedSearchInput(BaseModel):
    """
    [고도화된 향수 검색]
    1차로 메타 데이터 필터를 통해 후보군을 넓게 확보한 뒤,
    'query_text'(전략 의도)와 리뷰 데이터를 비교해 정밀하게 리랭킹(Reranking)합니다.
    """

    hard_filters: Dict[str, Any] = Field(
        description="타협 불가능한 필수 조건 (gender, brand 등). DB 컬럼과 일치해야 함."
    )
    strategy_filters: Dict[str, List[str]] = Field(
        description="이미지 전략에 따른 유연 조건 (season, accord, note, occasion 등)"
    )
    exclude_ids: Optional[List[int]] = Field(
        default=None, description="이미 추천되어 결과에서 제외할 향수 ID 리스트"
    )
    exclude_brands: Optional[List[str]] = Field(
        default=None, description="검색에서 제외할 브랜드 목록 (정규화된 브랜드명, 최대 5개)"
    )
    query_text: str = Field(
        description="리랭킹을 위한 전략 의도(Reason) 또는 검색 키워드. (예: '비 오는 날 숲속의 차분한 느낌')"
    )
    rank_mode: str = Field(
        default="DEFAULT",
        description="랭킹 모드: 'DEFAULT' (의미 기반) 또는 'POPULAR' (인기순)",
    )


class NoteSearchInput(BaseModel):
    """노트(원료) 검색 도구 입력 스키마"""

    keywords: List[str] = Field(
        description="검색할 노트(원료) 이름 리스트 (예: ['Rose', 'Vetiver', 'Tonka Bean'])"
    )


class AccordSearchInput(BaseModel):
    """어코드(향조/분위기) 검색 도구 입력 스키마"""

    keywords: List[str] = Field(
        description="검색할 어코드(향조) 이름 리스트 (예: ['Woody', 'Citrus', 'Powdery'])"
    )


class PerfumeIdSearchInput(BaseModel):
    """향수 ID 기반 검색 도구 입력 스키마"""

    perfume_id: int = Field(
        description="조회할 향수의 perfume_id (예: 12345)"
    )


class IngredientAnalysisResult(BaseModel):
    """사용자 질문을 분석하여 노트와 어코드를 분류한 결과"""

    notes: List[str] = Field(
        default=[],
        description="질문에서 식별된 노트(구체적 원료) 리스트 (예: Rose, Musk)",
    )
    accords: List[str] = Field(
        default=[],
        description="질문에서 식별된 어코드(향의 분위기/계열) 리스트 (예: Woody, Floral)",
    )
    is_ambiguous: bool = Field(
        default=False,
        description="사용자 질문이 향수와 관련 없거나 모호한 경우 True",
    )
