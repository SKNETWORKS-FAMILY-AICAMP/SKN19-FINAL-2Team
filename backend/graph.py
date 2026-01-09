# graph.py
import json
import traceback
from langgraph.graph import StateGraph, START, END
from schemas import State
from database import METADATA
from tools import (
    client, 
    safe_json_parse, 
    execute_precise_search, 
    search_notes_vector, 
    search_exact_entity
)

# 모델 설정 (실제 배포 시 사용 가능한 최상위 모델로 변경)
MODEL_NAME = "gpt-5.2" 

# ==========================================
# 1. Supervisor (라우터)
# ==========================================
def supervisor(state: State) -> State:
    try:
        query = state["user_query"]
        history = state.get("messages", [])
        
        last_ai_msg = ""
        if history and history[-1]["role"] == "assistant":
            last_ai_msg = history[-1]["content"]

        print(f"\n📡 [Supervisor] 입력: '{query}' (이전 질문: '{last_ai_msg[:20]}...')")
        
        prompt = f"""
        당신은 대화 흐름을 제어하는 관리자입니다.
        
        [입력]
        - 사용자 발화: "{query}"
        - 이전 AI 질문: "{last_ai_msg}"
        
        [판단 기준]
        1. **interviewer**: 이전 AI 질문에 대한 답변이거나 정보가 너무 부족한 경우.
        2. **researcher**: 구체적 추천 요청이거나 정보가 충분한 경우.
        3. **writer**: 단순 인사, 잡담.
        
        응답(JSON): {{"route": "interviewer" | "researcher" | "writer"}}
        """
        
        msg = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        route = safe_json_parse(msg.choices[0].message.content).get("route", "writer")
        return {"route": route}
        
    except Exception:
        print("\n🚨 [Supervisor Error]")
        traceback.print_exc()
        return {"route": "writer"}

# ==========================================
# 2. Interviewer (정보 수집)
# ==========================================
def interviewer(state: State) -> State:
    try:
        query = state["user_query"]
        current_context = state.get("interview_context", "") or ""
        
        print(f"\n🎤 [Interviewer] 답변 분석 및 문맥 업데이트")
        
        extraction_prompt = f"""
        사용자 답변에서 향수 추천 정보(계절, 성별, 취향, 이미지 등)를 추출해 요약하세요.
        - 기존 정보: {current_context}
        - 사용자 답변: {query}
        형식 예: "성별: 남성, 이미지: 차도남, 계절: 겨울"
        """
        msg = client.chat.completions.create(
            model="gpt-4o-mini", messages=[{"role": "user", "content": extraction_prompt}]
        )
        updated_context = msg.choices[0].message.content
        print(f"   👉 업데이트된 정보: {updated_context}")
        
        judge_prompt = f"""
        추천 검색이 가능한가요? (최소한 향 취향, 브랜드, 분위기 중 하나 존재)
        정보: {updated_context}
        응답(JSON): {{"is_sufficient": true/false, "next_question": "질문 내용"}}
        """
        judge_msg = client.chat.completions.create(
            model="gpt-4o-mini", 
            messages=[{"role": "user", "content": judge_prompt}],
            response_format={"type": "json_object"}
        )
        judge_result = safe_json_parse(judge_msg.choices[0].message.content)
        
        if judge_result.get("is_sufficient"):
            print("   ✅ 정보 충분 -> Researcher로 전달")
            return {
                "route": "researcher", 
                "interview_context": updated_context,
                "user_query": f"{updated_context} (사용자 의도 반영 추천)" 
            }
        else:
            print("   ❓ 정보 부족 -> 사용자에게 재질문")
            return {
                "route": "end",
                "interview_context": updated_context,
                "final_response": judge_result.get("next_question")
            }
            
    except Exception:
        print("\n🚨 [Interviewer Error]")
        traceback.print_exc()
        return {"route": "writer", "final_response": "잠시 문제가 생겼습니다. 다시 말씀해 주시겠어요?"}

# ==========================================
# 3. Researcher (상황별 동적 전략 수립)
# ==========================================
def researcher(state: State) -> State:
    try:
        query = state["user_query"]
        print(f"\n🕵️ [Researcher] 상황별 맞춤 전략 수립: {query}")

        meta_summary = {k: v[:20] for k, v in METADATA.items()}

        # 👇 [핵심 수정] 5가지 시나리오 라이브러리 정의
        prompt = f"""
        당신은 최고의 퍼스널 퍼퓸 컨설턴트입니다.
        사용자 요청: "{query}"
        DB 메타데이터: {json.dumps(meta_summary, ensure_ascii=False)}
        
        [임무]
        사용자의 요청 의도를 분석하고, 아래 **[시나리오 라이브러리]** 중 가장 적합한 하나를 골라 3가지 검색 전략(Plan)을 수립하세요.
        
        === [시나리오 라이브러리] ===
        
        Type A. [이미지/분위기] (예: "차가운 도시 남자", "청순한 느낌")
        - 전략 1: **직관적 일치** (이미지와 100% 매칭되는 향)
        - 전략 2: **반전 매력** (이미지를 보완해주는 따뜻/부드러운 향)
        - 전략 3: **입체적 매력** (첫 향과 잔향이 다른 독특한 향)
        
        Type B. [특정 향료/노트] (예: "장미 향 좋아해", "우디한 거")
        - 전략 1: **노트의 정석** (해당 노트가 메인인 향수)
        - 전략 2: **조화로운 블렌드** (해당 노트와 궁합이 좋은 노트와의 조합)
        - 전략 3: **유니크한 해석** (해당 노트를 독특하게 해석한 향수)
        
        Type C. [TPO/상황] (예: "소개팅", "데일리", "면접")
        - 전략 1: **실패 없는 정석** (가장 대중적이고 안전한 선택)
        - 전략 2: **강렬한 인상** (상대방에게 기억에 남을 매력적인 향)
        - 전략 3: **감각적인 분위기** (은은하게 분위기를 더해주는 향)
        
        Type D. [유사 향수 찾기] (예: "샤넬 넘버5 같은 거", "조말론 비슷한 거")
        - 전략 1: **DNA 일치** (메인 노트와 구조가 가장 유사한 향)
        - 전략 2: **현대적 해석** (비슷하지만 더 트렌디하거나 모던한 느낌)
        - 전략 3: **다른 계절감** (비슷한 느낌이지만 더 가볍거나/무거운 버전)
        
        Type E. [선물/입문/정보부족] (예: "여친 선물", "입문용")
        - 전략 1: **호불호 없는 베스트** (대중성 1위, 실패 확률 0%)
        - 전략 2: **트렌디한 유행** (요즘 가장 핫한 브랜드나 향)
        - 전략 3: **세련된 니치** (흔하지 않고 고급스러운 선물)
        
        === [작성 규칙] ===
        1. 위 시나리오 중 하나를 선택하여 3개의 Plan을 작성하세요.
        2. **strategy_name**은 위에서 정의한 전략 이름(예: "직관적 일치")을 그대로 사용하세요.
        3. **필수**: 노트(Note) 키워드는 반드시 **영어(English)**로 변환하세요. (장미->Rose)
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
            model=MODEL_NAME, 
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        parsed = safe_json_parse(msg.choices[0].message.content)
        plans = parsed.get("plans", []) if parsed else []
        scenario_type = parsed.get("scenario_type", "Unknown")
        
        print(f"   💡 선택된 시나리오: {scenario_type}")
        
        search_logs = []
        final_result_text = ""
        
        for plan in plans:
            strategy = plan.get('strategy_name', f"Strategy-{plan.get('priority')}")
            print(f"   👉 실행: {strategy}")
            
            # 필터 조립
            current_filters = []
            for f in plan.get("filters", []):
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
                print(f"     ✅ 결과 확보")
                search_logs.append(f"전략 [{strategy}] 성공")
                # 결과 텍스트에 전략 이름을 붙여서 Writer가 구분할 수 있게 함
                final_result_text += f"\n=== [전략: {strategy}] ===\n{result_text}\n"
            else:
                print(f"     ❌ 결과 없음")
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
        print("\n🚨 [Researcher Error]")
        traceback.print_exc()
        return {"research_result": "오류 발생", "route": "writer"}


# ==========================================
# 4. Writer (동적 전략 반영 스토리텔링)
# ==========================================
# graph.py

def writer(state: State) -> State:
    try:
        print("✍️ [Writer] 답변 작성")
        query = state["user_query"]
        result = state.get("research_result", "")
        
        # 👇 [수정됨] HTML 태그 방식 포기 -> 표준 마크다운 방식 사용
        # 프론트엔드 호환성을 위해 가장 안전한 방법을 선택합니다.
        
        prompt = f"""
        당신은 향수를 잘 모르는 초보자를 위한 세상에서 가장 친절한 향수 컨설턴트입니다.
        
        [사용자 요청]: "{query}"
        
        [검색된 향수 데이터]: 
        {result}
        
        [작성 규칙 - 필독]
        1. **목차 구성**: 검색 결과의 전략 이름(예: '직관적 일치' 등)을 그대로 사용하세요.
        
        2. **이미지 필수 (표준 마크다운)**: 
           - 반드시 아래 형식을 지키세요.
           - `![향수명](이미지링크)`
           - 예: `![Chanel No.5](https://...)`
        
        3. **[매우 중요] 전문 용어 절대 사용 금지 🚫**:
           - **금지어**: 노트(Note), 어코드(Accord), 탑/미들/베이스, 우디, 스파이시, 시트러스, 플로럴, 머스크, 시프레, 푸제르, 오리엔탈 등.
           - **번역 지침**: 무조건 오감이 느껴지는 **쉬운 우리말**로 풀어서 쓰세요.
             - 우디 -> 비에 젖은 숲속 나무 냄새, 오래된 종이 냄새
             - 스파이시 -> 코끝이 찡한 후추 느낌, 톡 쏘는 매력
             - 시트러스 -> 갓 짠 레몬의 상큼함, 귤껍질 깔 때 나는 향
             - 머스크 -> 포근한 살결 냄새, 뽀송뽀송한 이불 냄새
             - 레더리 -> 새 가죽 재킷에서 나는 묵직한 냄새
             - 플로럴 -> 꽃집에 들어갔을 때 나는 생화 향기

        4. **정보 표기**: 브랜드, 이름, 출시년도, 조향사 정보는 하단에 깔끔하게 적으세요.
        
        [출력 형식 예시]
        
        안녕하세요! [이미지/요청]에 딱 맞는 향수 3가지를 골라봤어요.
        
        ### 1. [전략이름] **브랜드 - 향수명**
        ![향수이미지](링크)
        
        - **어떤 향인가요?**: 톡 쏘는 레몬 향으로 시작해서, 시간이 지나면 비 온 뒤 숲속에 있는 듯한 차분한 나무 냄새가 남아요.
        - **추천 이유**: 차가운 도시 남자의 이미지를 완성시켜 줄 세련된 향이에요.
        - **정보**: 2023년 출시 / 조향사 OOO
        
        ... (나머지 동일)
        """
        
        msg = client.chat.completions.create(
            model=MODEL_NAME, 
            messages=[{"role": "user", "content": prompt}]
        )
        return {"final_response": msg.choices[0].message.content}
    except Exception:
        print("\n🚨 [Writer Error]")
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
    
    return graph.compile()