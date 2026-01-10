import json
import traceback
import re
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver 
from schemas import State
from database import METADATA
from tools import (
    client, 
    safe_json_parse, 
    execute_precise_search, 
    search_notes_vector, 
    search_exact_entity
)

# ==========================================
# ⚙️ 모델 설정
# ==========================================
FAST_MODEL = "gpt-4o-mini"
HIGH_PERFORMANCE_MODEL = "gpt-4o" 

# ==========================================
# 1. Supervisor (라우터)
# ==========================================
def supervisor(state: State) -> State:
    try:
        query = state["user_query"]
        
        print(f"\n📡 [Supervisor] 입력: '{query}'", flush=True)
        
        prompt = f"""
        당신은 대화 흐름을 제어하는 관리자입니다.
        
        [입력]
        - 사용자 발화: "{query}"
        
        [판단 기준]
        1. **interviewer**: 향수 추천을 위해 추가 정보가 필요한 경우 (질문).
        2. **researcher**: 구체적 추천 요청이거나 정보가 충분한 경우.
        3. **writer**: 단순 인사, 잡담, 또는 추천이 끝난 후의 마무리.
        
        응답(JSON): {{"route": "interviewer" | "researcher" | "writer"}}
        """
        
        msg = client.chat.completions.create(
            model=FAST_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        route = safe_json_parse(msg.choices[0].message.content).get("route", "writer")
        return {"route": route}
        
    except Exception:
        print("\n🚨 [Supervisor Error]", flush=True)
        traceback.print_exc()
        return {"route": "writer"}

# ==========================================
# 2. Interviewer (정보 수집)
# ==========================================
def interviewer(state: State) -> State:
    try:
        query = state["user_query"]
        current_context = state.get("interview_context", "") or ""
        
        print(f"\n🎤 [Interviewer] 답변 분석 및 문맥 업데이트", flush=True)
        
        extraction_prompt = f"""
        사용자 답변에서 향수 추천 정보(계절, 성별, 취향, 이미지 등)를 추출해 요약하세요.
        - 기존 정보: {current_context}
        - 사용자 답변: {query}
        형식 예: "성별: 남성, 이미지: 차도남, 계절: 겨울"
        """
        msg = client.chat.completions.create(
            model=FAST_MODEL,
            messages=[{"role": "user", "content": extraction_prompt}]
        )
        updated_context = msg.choices[0].message.content
        print(f"   👉 업데이트된 정보: {updated_context}", flush=True)
        
        judge_prompt = f"""
        추천 검색이 가능한가요? (최소한 향 취향, 브랜드, 분위기 중 하나 존재)
        정보: {updated_context}
        응답(JSON): {{"is_sufficient": true/false, "next_question": "질문 내용"}}
        """
        judge_msg = client.chat.completions.create(
            model=FAST_MODEL,
            messages=[{"role": "user", "content": judge_prompt}],
            response_format={"type": "json_object"}
        )
        judge_result = safe_json_parse(judge_msg.choices[0].message.content)
        
        if judge_result.get("is_sufficient"):
            print("   ✅ 정보 충분 -> Researcher로 전달", flush=True)
            return {
                "route": "researcher", 
                "interview_context": updated_context,
                "user_query": f"{updated_context} (사용자 의도 반영 추천)" 
            }
        else:
            print("   ❓ 정보 부족 -> 사용자에게 재질문", flush=True)
            return {
                "route": "end",
                "interview_context": updated_context,
                "final_response": judge_result.get("next_question")
            }
            
    except Exception:
        print("\n🚨 [Interviewer Error]", flush=True)
        traceback.print_exc()
        return {"route": "writer", "final_response": "잠시 문제가 생겼습니다. 다시 말씀해 주시겠어요?"}

# ==========================================
# 3. Researcher (전략 수립)
# ==========================================
def researcher(state: State) -> State:
    try:
        query = state["user_query"]
        print(f"\n🕵️ [Researcher] 상황별 맞춤 전략 수립: {query}", flush=True)

        meta_summary = {k: v[:20] for k, v in METADATA.items()}

        prompt = f"""
        당신은 최고의 퍼스널 퍼퓸 컨설턴트입니다.
        사용자 요청: "{query}"
        DB 메타데이터: {json.dumps(meta_summary, ensure_ascii=False)}
        
        [임무]
        사용자의 요청 의도를 분석하고, 아래 **[시나리오 라이브러리]** 중 가장 적합한 하나를 골라 3가지 검색 전략(Plan)을 수립하세요.
        
        === [시나리오 라이브러리] ===
        Type A. [이미지/분위기] (예: "차가운 도시 남자", "청순한 느낌")
        Type B. [특정 향료/노트] (예: "장미 향 좋아해", "우디한 거")
        Type C. [TPO/상황] (예: "소개팅", "데일리", "면접")
        Type D. [유사 향수 찾기] (예: "샤넬 넘버5 같은 거")
        Type E. [선물/입문/정보부족] (예: "여친 선물", "입문용")
        
        === [작성 규칙] ===
        1. 3개의 Plan을 작성하세요.
        2. **strategy_name**은 전략 이름(예: "직관적 일치")을 그대로 사용하세요.
        3. **필수**: 노트(Note) 키워드는 반드시 **영어(English)**로 변환하세요.
        4. 추상적 표현은 'use_vector_search': true로 설정하세요.
        
        응답(JSON) 예시:
        {{
            "scenario_type": "Type A",
            "plans": [
                {{
                    "priority": 1,
                    "strategy_name": "직관적 일치",
                    "filters": [],
                    "note_keywords": ["Mint", "Aquatic"],
                    "use_vector_search": true
                }},
                ... (총 3개)
            ]
        }}
        """
        
        msg = client.chat.completions.create(
            model=HIGH_PERFORMANCE_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        parsed = safe_json_parse(msg.choices[0].message.content)
        plans = parsed.get("plans", []) if parsed else []
        scenario_type = parsed.get("scenario_type", "Unknown")
        
        print(f"   💡 선택된 시나리오: {scenario_type}", flush=True)
        
        search_logs = []
        final_result_text = ""
        
        for plan in plans:
            priority = plan.get('priority', '?')
            strategy = plan.get('strategy_name', f"Strategy-{priority}")
            
            print(f"   👉 [Priority {priority}] 실행: {strategy}", flush=True)
            
            current_filters = []
            
            # 방어 코드: 필터가 문자열 등으로 잘못 오면 무시
            for f in plan.get("filters", []):
                if not isinstance(f, dict):
                    print(f"   ⚠️ [Warning] 잘못된 필터 형식 무시됨: {f}", flush=True)
                    continue
                    
                col = f.get('column')
                val = f.get('value')
                if not col or not val: continue
                
                if col in ['brand', 'perfume_name']:
                    corrected = search_exact_entity(val, col)
                    if corrected: f['value'] = corrected
                current_filters.append(f)
            
            notes = []
            if plan.get("use_vector_search"):
                notes.extend(search_notes_vector(query, top_k=3))
            
            for k in plan.get("note_keywords", []):
                notes.extend(search_notes_vector(k, top_k=2))
                
            if notes:
                current_filters.append({"column": "note", "value": list(set(notes))})
            
            # 검색 실행
            result_text = execute_precise_search(current_filters)
            
            if result_text:
                print(f"     ✅ 결과 확보", flush=True)
                search_logs.append(f"전략 [{strategy}] 성공")
                final_result_text += f"\n=== [전략: {strategy}] ===\n{result_text}\n"
            else:
                print(f"     ❌ 결과 없음", flush=True)
                search_logs.append(f"전략 [{strategy}] 결과 없음")
        
        if not final_result_text:
            final_result_text = "검색 결과가 없습니다."

        return {
            "search_plans": plans,
            "search_logs": search_logs,
            "research_result": final_result_text,
            "route": "writer"
        }
        
    except Exception:
        print("\n🚨 [Researcher Error]", flush=True)
        traceback.print_exc()
        return {"research_result": "오류 발생", "route": "writer"}


# ==========================================
# 4. Writer (글쓰기)
# ==========================================
def writer(state: State) -> State:
    try:
        print("✍️ [Writer] 답변 작성", flush=True)
        query = state["user_query"]
        result = state.get("research_result", "")
        
        prompt = f"""
        당신은 향수를 잘 모르는 초보자를 위한 세상에서 가장 친절한 향수 컨설턴트입니다.
        
        [사용자 요청]: "{query}"
        
        [검색된 향수 데이터]: 
        {result}
        
        [작성 규칙 - 필독]
        1. **목차 스타일**: 
           - '전략:' 단어 금지.
           - **`## 번호. [전략이름] 브랜드 - 향수명`** 형식 엄수.
           - 예: `## 1. [세련된 니치] Loewe - Agua de Loewe Ella`
        
        2. **이미지 필수**: `![향수명](이미지링크)`
        
        3. **[★매우 중요★] 서식 및 강조 규칙**:
           - **항목 제목(Label)**: 반드시 **`_` (언더바)**로 감싸세요. (파란색 제목)
             - 예: `_어떤 향인가요?_`, `_추천 이유_`, `_정보_`
           - **내용 강조(Highlight)**: 핵심 단어는 **`**` (별표 2개)**로 감싸세요. (핑크색 강조)
             - 예: `처음엔 **상큼한 귤 향**이 나요.`
        
        4. **구분선**: 향수 추천 사이에 `---` 삽입.
        
        5. **정보 표기**: 브랜드, 이름, 출시년도만 기재.
        
        6. **[필수] 향 설명 방식 (시간 순서)**:
           - **"처음에는 ~(탑), 시간이 지나면 ~(미들), 끝으로 ~(베이스)"** 순서로 설명하세요.
           - 전문 용어(노트, 어코드 등) 대신 쉬운 비유를 사용하세요.
           
        7. **[핵심] 추천 논리 연결 (Why?)**:
           - `_추천 이유_`를 작성할 때, 단순히 "좋아요"라고 하지 마세요.
           - **[사용자 질문의 키워드(나이, 성별, 상황)]**와 **[향수의 특징]**을 논리적으로 연결해서 설명하세요.
           - 예시 1: "20대 여성분에게 선물하신다고 하셨죠? 이 나이대에는 너무 무거운 향보다는 **상큼한 과일 향**이 생기 발랄한 이미지를 줘서 호불호 없이 잘 어울려요."
           - 예시 2: "소개팅용 향수를 찾으셨는데, 이 향의 **은은한 비누 잔향**이 상대방에게 **깔끔하고 단정한 인상**을 심어주기에 완벽해요."
        
        [출력 형식 예시]
        
        안녕하세요! 요청하신 느낌에 맞춰 3가지 향수를 골라봤어요.
        
        ## 1. [깨끗한 비누] **Santa Maria Novella - Fresia**
        ![Fresia](링크)
        
        - _어떤 향인가요?_: 처음엔 **막 씻고 나온 듯한 비누 거품 냄새**가 확 풍겨요. 시간이 지나면 **은은한 생화 꽃향기**가 올라오고, 마지막엔 **포근한 살냄새**가 남아요.
        - _추천 이유_: **20대 여성분**에게 선물하기 가장 좋은 향이에요. **과하지 않은 깨끗함**이 청순한 이미지를 만들어줘서 데일리로 쓰기 딱 좋거든요.
        - _정보_: Santa Maria Novella / Fresia / 1993년 출시
        
        ---
        ...
        """
        
        msg = client.chat.completions.create(
            model=HIGH_PERFORMANCE_MODEL, 
            messages=[{"role": "user", "content": prompt}]
        )
        
        raw_content = msg.choices[0].message.content
        
        # [후처리] 강조 공백 제거
        fixed_content = re.sub(r'\*\*\s*(.*?)\s*\*\*', r'**\1**', raw_content)
        
        return {"final_response": fixed_content}
    except Exception:
        print("\n🚨 [Writer Error]", flush=True)
        traceback.print_exc()
        return {"final_response": "답변 생성 중 오류가 발생했습니다."}


# ==========================================
# Graph Build
# ==========================================
def build_graph():
    graph = StateGraph(State)
    
    graph.add_node("supervisor", supervisor)
    graph.add_node("interviewer", interviewer)
    graph.add_node("researcher", researcher)
    graph.add_node("writer", writer)
    
    graph.add_edge(START, "supervisor")
    
    def route_decision(state: State):
        return state["route"]
    
    graph.add_conditional_edges(
        "supervisor",
        route_decision,
        {"interviewer": "interviewer", "researcher": "researcher", "writer": "writer"}
    )
    
    graph.add_conditional_edges(
        "interviewer",
        route_decision,
        {"researcher": "researcher", "end": END}
    )
    
    graph.add_edge("researcher", "writer")
    graph.add_edge("writer", END)
    
    # 메모리 저장소(Checkpointer) 적용
    memory = MemorySaver()
    
    return graph.compile(checkpointer=memory)