# schemas.py
from typing import List, Any, Optional
from typing_extensions import TypedDict, Literal
from pydantic import BaseModel, Field

# LangGraph 상태 (State)
class State(TypedDict):
    user_query: str
    messages: List[Any]  # 대화 히스토리 (Supervisor 판단용)
    
    # 라우팅 및 인터뷰 정보
    route: Literal["interviewer", "researcher", "writer", "end"]
    interview_context: str  # 누적된 사용자 취향 정보 (예: "계절: 겨울, 노트: 우디")
    missing_info: str       # (Optional) Supervisor가 판단한 부족한 정보
    
    # 검색 전략 및 결과
    search_plans: List[dict] # Researcher가 수립한 전략 리스트
    search_logs: List[str]   # 실행 로그 (프론트엔드 전송용)
    research_result: str     # 최종 검색 결과 텍스트
    
    # 최종 응답
    final_response: str
    
    # [ksu] 토큰 사용량 누적 (비용 계산용)
    input_tokens: int
    output_tokens: int
    
    # [ksu] 테스트 정보 저장용 (목적, 시나리오, 기대값)
    test_info: Optional[dict]

# API 요청 바디
class ChatRequest(BaseModel):
    user_query: str = Field(..., min_length=1, description="사용자 입력")
    history: List[dict] = Field(default=[], description="대화 히스토리 [{'role': 'user', 'content': '...'}, ...]")