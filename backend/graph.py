# ====== [ksu] 테스터 ==========
import os
import time  # [추가] time 모듈 임포트
from datetime import datetime
# ============================

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
FAST_MODEL = "gpt-4o"
HIGH_PERFORMANCE_MODEL = "gpt-5.2" 

# ==========================================
# 1. Supervisor (라우터)
# ==========================================


# graph.py 의 supervisor 함수 교체

def supervisor(state: State) -> State:
    try:
        query = state["user_query"]

        # ============================== [ksu] 테스터 =============================
        test_info = None
        # [👇 /t 명령어 처리 로직 추가됨]
        if query.startswith("/t"):
            try:
                # 예: /t [목적],[시나리오],[기대값] 실제질문
                # meta_part, real_query = query.split("]", 1)
                # meta_part = meta_part.replace("/t", "").replace("[", "").strip()
                # real_query = real_query.strip()
                
                # parts = [p.strip() for p in meta_part.split(",")]
                # if len(parts) >= 3:
                # 정규식으로 대괄호 [...] 안의 내용 추출
                # 예: /t [목적],[시나리오],[기대값] 질문 -> ['목적', '시나리오', '기대값']
                matches = re.findall(r"\[(.*?)\]", query)
                
                if len(matches) >= 3:
                    test_info = {
                        # "purpose": parts[0],
                        # "scenario": parts[1],
                        # "expected": parts[2]
                        "purpose": matches[0].strip(),
                        "scenario": matches[1].strip(),
                        "expected": matches[2].strip(),
                        "start_time": time.time() 
                    }
                    # query = real_query
                    # [중요] 실제 질문 추출 (마지막 ']' 이후의 모든 텍스트)
                    last_bracket_idx = query.rfind("]")
                    if last_bracket_idx != -1:
                        query = query[last_bracket_idx+1:].strip()
                        
                    print(f"🧪 [Test Mode] {test_info}", flush=True)
            except Exception:
                # pass
                print("⚠️ 파싱 에러 발생", flush=True)
        # ============================== [ksu] 테스터 =============================
        
        print(f"\n📡 [Supervisor] 입력: '{query}'", flush=True)
        
        prompt = f"""
        당신은 대화 흐름을 제어하는 관리자입니다.
        
        [입력]
        - 사용자 발화: "{query}"
        
        [판단 기준]
        1. **researcher (즉시 검색)**:
           - **[주의]** 문맥 없이도 검색 가능한 **완벽한 요청**일 때만 선택하세요.
           - 예: "조말론의 우디한 향수 추천해줘", "20대 여자가 쓸 장미향 향수"
           
        2. **interviewer (문맥 업데이트 및 질문)**:
           - **대부분의 경우는 이곳입니다.**
           - **짧은 답변/속성**: "귀여운 편이야", "시크해", "우디한 거", "20대" 등 사용자의 취향이나 특성을 나타내는 단어가 있으면 무조건 선택하세요.
           - **불완전한 요청**: "조말론 추천해줘" (어떤 향?)
           - **이유**: 이전 대화의 문맥(Brand 등)과 합치기 위해서입니다.
           
        3. **writer (잡담/종료)**:
           - 향수와 전혀 상관없는 인사("안녕"), 시스템 불만, 종료 요청.
           - **[중요] 애매하면 무조건 'interviewer'로 보내세요.**
        
        응답(JSON): {{"route": "interviewer" | "researcher" | "writer"}}
        """
        
        msg = client.chat.completions.create(
            model=FAST_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )

        # ============== [ksu] 토큰 사용량 집계 =================
        in_tok = msg.usage.prompt_tokens
        out_tok = msg.usage.completion_tokens
        current_in = state.get("input_tokens", 0) + in_tok
        current_out = state.get("output_tokens", 0) + out_tok
        # ===================================================

        route = safe_json_parse(msg.choices[0].message.content).get("route", "writer")
        
        print(f"   🚦 결정된 경로: {route}", flush=True)

        # ============== [ksu] 토큰 정보도 함께 리턴 =================
        # return {"route": route}
        return {"route": route,
                "input_tokens": current_in,
                "output_tokens": current_out,
                "user_query": query,            # [테스터] 파싱된 실제 질문
                "test_info": test_info}         # [테스터] 테스트 메타데이터
        # =======================================================
        
    except Exception:
        print("\n🚨 [Supervisor Error]", flush=True)
        traceback.print_exc()
        return {"route": "writer"}
    
    
def interviewer(state: State) -> State:
    try:
        query = state["user_query"]
        current_context = state.get("interview_context", "") or ""
        
        print(f"\n🎤 [Interviewer] 답변 분석 및 문맥 업데이트", flush=True)
        
        # 1. 정보 추출 (이미지/분위기 강조)
        extraction_prompt = f"""
        사용자 답변에서 향수 추천 정보를 있는 그대로 요약하세요.
        
        [핵심 지침]
        1. **이미지/분위기 포착**: 사용자가 '향'을 몰라도 '이미지(시크, 차가움, 러블리 등)'를 말했으면 반드시 기록하세요.
        2. **팩트 체크**: 사용자의 입력에 없는 내용은 절대 추측해서 적지 마세요.
        3. **형식**: "브랜드: OOO, 이미지: OOO, 취향: 정보 없음, 대상: OOO"
        
        - 기존 정보: {current_context}
        - 사용자 답변: {query}
        """
        msg = client.chat.completions.create(
            model=FAST_MODEL,
            messages=[{"role": "user", "content": extraction_prompt}]
        )

        # ================= [ksu] 1차 토큰 집계 ======================
        in_tok1 = msg.usage.prompt_tokens
        out_tok1 = msg.usage.completion_tokens
        # =========================================================

        updated_context = msg.choices[0].message.content
        print(f"   👉 업데이트된 정보: {updated_context}", flush=True)
        
        # 2. 판단 및 질문 생성 (유연한 판단 & 논리적 질문)
        judge_prompt = f"""
        현재 수집된 정보가 추천 검색을 시작하기에 충분한지 판단하세요.
        
        [판단 기준 - 유연함]
        1. **충분함(true)**: 
           - 구체적인 '향(Note)'을 몰라도, **명확한 '이미지/분위기'(예: 시크, 차가움, 도도함)**가 있다면 **충분**하다고 판단하세요. (Researcher가 이미지로 검색 가능함)
           - 브랜드와 대상만 있고 아무런 힌트가 없을 때만 '불충분'입니다.
           
        2. **부족함(false)**: 
           - 정말 아무런 단서(향도 모르고 이미지도 말 안 함)가 없을 때.
        
        [★질문 작성 가이드 - 문맥 유지 (Context Awareness)★]
        만약 질문이 필요하다면, **사용자가 방금 한 말**을 반영해서 물어보세요. (동문서답 금지)
        
        **Case A. 사용자가 '차가운/시크한' 이미지를 언급했는데 모호할 때:**
        - (나쁜 예): "따뜻한 커피 향은 어떠세요?" (사용자 말 무시)
        - (좋은 예): "**차가운 이미지**라고 하셨군요! 구체적으로 **도시적이고 날카로운 차가움(모던)**인가요, 아니면 **새벽 숲속 같은 서늘한 차가움(우디)**인가요?"
        
        **Case B. 전혀 정보가 없을 때:**
        - "평소 그분의 패션 스타일이나 분위기가 어떤가요? (예: 귀여운 편, 시크한 편)"
        
        정보: {updated_context}
        
        응답(JSON): 
        {{
            "is_sufficient": true/false, 
            "next_question": "생성된 질문 내용"
        }}
        """
        judge_msg = client.chat.completions.create(
            model=FAST_MODEL,
            messages=[{"role": "user", "content": judge_prompt}],
            response_format={"type": "json_object"}
        )

        # ========================= [ksu] 2차 토큰 집계 및 최종 합산 =========================
        in_tok2 = judge_msg.usage.prompt_tokens
        out_tok2 = judge_msg.usage.completion_tokens
        
        total_in = state.get("input_tokens", 0) + in_tok1 + in_tok2
        total_out = state.get("output_tokens", 0) + out_tok1 + out_tok2
        # ===============================================================================

        judge_result = safe_json_parse(judge_msg.choices[0].message.content)
        
        if judge_result.get("is_sufficient"):
            print("   ✅ 정보 충분(이미지/취향 포함됨) -> Researcher로 전달", flush=True)
            return {
                "route": "researcher", 
                "interview_context": updated_context,
                "user_query": f"{updated_context} (사용자 의도 반영)", 
                "input_tokens": total_in, # [ksu] 토큰 사용량 누적
                "output_tokens": total_out # [ksu] 토큰 사용량 누적
            }
        else:
            print("   ❓ 정보 부족 -> 사용자에게 재질문", flush=True)
            return {
                "route": "end",
                "interview_context": updated_context,
                "final_response": judge_result.get("next_question"),
                "input_tokens": total_in, # [ksu] 토큰 사용량 누적
                "output_tokens": total_out # [ksu] 토큰 사용량 누적
            }
            
    except Exception:
        print("\n🚨 [Interviewer Error]", flush=True)
        traceback.print_exc()
        return {"route": "writer", "final_response": "잠시 문제가 생겼습니다. 다시 말씀해 주시겠어요?"}

# ==========================================
# 3. Researcher (전략 수립) - 의도 중심 전략명 생성
# ==========================================
# graph.py

# [1] 상단 import에 DB 연결 함수 확인
from database import get_db_connection

# [2] 메타 데이터(유효 필터 값) 가져오는 헬퍼 함수 추가
def fetch_meta_filters():
    """
    DB에서 현재 존재하는 Season, Occasion, Accord의 유효한 값 목록을 가져옵니다.
    [수정] 테이블 이름 실제 DB(줄임말)에 맞게 변경
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 1. Season (계절) -> tb_perfume_season_m (이건 줄임말 아님)
        cur.execute("SELECT DISTINCT season FROM tb_perfume_season_m WHERE season IS NOT NULL")
        seasons = [r[0] for r in cur.fetchall()]
        
        # 2. Occasion (상황) -> [수정] tb_perfume_oca_m (줄임말 적용!)
        cur.execute("SELECT DISTINCT occasion FROM tb_perfume_oca_m WHERE occasion IS NOT NULL")
        occasions = [r[0] for r in cur.fetchall()]
        
        # 3. Accord (향조) -> tb_perfume_accord_m
        cur.execute("SELECT DISTINCT accord FROM tb_perfume_accord_m WHERE accord IS NOT NULL")
        accords = [r[0] for r in cur.fetchall()]
        
        conn.close()
        
        return (
            ", ".join([f"'{s}'" for s in seasons]),
            ", ".join([f"'{o}'" for o in occasions]),
            ", ".join([f"'{a}'" for a in accords])
        )
    except Exception as e:
        print(f"⚠️ Meta Filter Load Error: {e}")
        # DB 에러 시 기본값 리턴 (봇이 죽지 않도록)
        return (
            "'Spring', 'Summer', 'Fall', 'Winter'",
            "'Daily', 'Formal', 'Date', 'Party'",
            "'Citrus', 'Woody', 'Floral', 'Musk'"
        )

# [3] researcher 함수 교체
def researcher(state: State) -> State:
    try:
        query = state["user_query"]
        print(f"\n🕵️ [Researcher] DB 메타 데이터 기반 전략 수립: {query}", flush=True)

        # ★ DB에서 유효한 필터 값 실시간 로딩
        valid_seasons, valid_occasions, valid_accords = fetch_meta_filters()

        prompt = f"""
        당신은 보유한 데이터베이스를 완벽하게 활용하는 '퍼퓸 디렉터'입니다.
        사용자 요청("{query}")을 분석해 **가장 매력적인 3가지 스타일링 전략**을 수립하세요.
        
        === [1. 보유 데이터 매핑 (Data Mapping)] - ★핵심★ ===
        사용자의 말에서 아래 **[허용된 값 목록]**에 해당하는 정보가 나오면 **반드시 `filters`에 포함**시키세요.
        
        1. **Brand**: 브랜드명 (예: 'Chanel', 'Dior') -> `filters`
        2. **Gender**: 성별 (예: 'Feminine', 'Masculine') -> `filters`
        
        3. **Season (계절)**: 
           - **[허용된 값]**: [{valid_seasons}]
           - 사용자가 "여름"이라고 하면 위 목록 중 'Summer'를 찾아 `{{'column': 'season', 'value': 'Summer'}}`로 설정.
           
        4. **Occasion (상황)**: 
           - **[허용된 값]**: [{valid_occasions}]
           - 사용자가 "데일리"라고 하면 위 목록 중 매칭되는 값을 찾아 `filters`에 설정.
           
        5. **Accord (향조)**: 
           - **[허용된 값]**: [{valid_accords}]
           - 사용자가 "상큼한 시트러스"라고 하면 위 목록 중 'Citrus'를 찾아 `filters`에 설정.

        === [2. 시나리오별 행동 지침] ===
        **Type A. [이미지/분위기]** (예: "시크한", "포근한")
        - 전략: DB 허용 값에 없는 추상적 표현은 `note_keywords`에 넣어 벡터 검색.
        
        **Type B. [특정 조건]** (예: "여름에 뿌릴 시트러스")
        - 전략: **DB 필터링 우선!** (위 허용된 값 목록에 존재한다면 `filters` 사용)
        
        **Type D. [선물/입문]** (예: "여친 선물")
        - 전략: `note_keywords`에 "Soap", "Clean", "Light Floral" 등 호불호 없는 키워드 자동 추가.

        === [3. 전략 수립 프레임워크 (3-Step Styling)] ===
        **Plan 1. [동조 (Harmony)]**: "이미지 직관적 반영"
        **Plan 2. [반전 (Gap)]**: "의외의 매력 포인트"
        **Plan 3. [변화 (Shift)]**: "입체적 밸런스"

        === [4. 작성 규칙] ===
        1. `strategy_name`은 **"꽃향기", "비누 냄새", "살냄새"** 등 쉬운 한국어로 지으세요.
        2. 모든 필터 값(`value`)은 위 **[허용된 값]** 중에서만 골라야 하며, 반드시 **영어(English)**여야 합니다.
        
        응답(JSON) 예시:
        {{
            "scenario_type": "Type B (Specific)",
            "plans": [
                {{
                    "priority": 1,
                    "strategy_name": "여름 햇살 같은 상큼한 시트러스",
                    "filters": [
                        {{"column": "season", "value": "Summer"}},  // [허용된 값] 중 선택
                        {{"column": "accord", "value": "Citrus"}},  // [허용된 값] 중 선택
                        {{"column": "gender", "value": "Unisex"}}
                    ],
                    "note_keywords": ["Fresh", "Lime"], 
                    "use_vector_search": true
                }}
            ]
        }}
        """
        
        msg = client.chat.completions.create(
            model=HIGH_PERFORMANCE_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        # ================= [ksu] Researcher 토큰 집계 =================
        in_tok = msg.usage.prompt_tokens
        out_tok = msg.usage.completion_tokens
        
        # 이전 단계(Supervisor 등)에서 넘어온 토큰에 더하기
        total_in = state.get("input_tokens", 0) + in_tok
        total_out = state.get("output_tokens", 0) + out_tok
        # ================= [ksu] Researcher 토큰 집계 =================

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
            
            for f in plan.get("filters", []):
                if not isinstance(f, dict): continue
                col = f.get('column')
                val = f.get('value')
                if not col or not val: continue
                
                # 브랜드/향수명 오타 보정
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
            "route": "writer",
            "input_tokens": total_in,    # [ksu] 토큰 사용량 누적
            "output_tokens": total_out   # [ksu] 토큰 사용량 누적
        }
        
    except Exception:
        print("\n🚨 [Researcher Error]", flush=True)
        traceback.print_exc()
        return {"research_result": "오류 발생", "route": "writer"}


# ==========================================
# 4. Writer (글쓰기) - 1전략 1향수 & 의도 설명
# ==========================================
# 원본 규칙
# 459 : - 검색 결과가 없다면 반드시 검색된 결과가 없음을 알리고 다른 검색용 쿼리로 만들수 있을만한 질문을 던질 것.
# 460 : - 절대로 임의의 향수를 추천하지 않을 것.

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
        0. **검색결과에 따른 출력**:
            - 검색 결과가 있다면: 아래 규칙들을 엄격히 따라 추천할 것.
            - 검색 결과가 없다면:
                - 사용자가 향수 추천을 원한 경우: "검색된 결과가 없어서 추천이 어렵다"고 솔직히 말하고, 취향을 다시 물어볼 것.
                - 사용자가 '안녕', '고마워' 등 **단순 대화(Small Talk)**를 한 경우: **절대 DB나 검색 얘기를 꺼내지 말고** 자연스럽게 대화할 것. (앵무새 금지)
        
        1. **[★1전략 1향수 원칙★]**: 
            - 검색 결과에 여러 향수가 있더라도, **각 전략(Strategy) 당 가장 적합한 향수 딱 1개만** 선정하세요.
            - 결과적으로 총 3개의 향수만 추천되어야 합니다. (중복 추천 금지)
            - 단 출력시에 전략별로 딱 한개씩 추천한다는 내용을 직접적으로 언급하지 않도록 주의하세요.
        
        2. **목차 스타일 (전략 의도 강조)**: 
            - 형식: **`## 번호. [전략이름] 브랜드 - 향수명`**
            - **[전략이름]**에는 Researcher가 정한 전략명(예: "겉차속따 반전 매력")을 그대로 넣되 전략: 등의 딱딱한 표현은 제외시키고 전략으 설명만 사용하세요.
            - 예시: `## 1. [차가운 첫인상 속 따뜻한 반전] Chanel - Coco Noir`
        
        3. **이미지 필수**: `![향수명](이미지링크)`
        
        4. **[★매우 중요★] 서식 및 강조 규칙**:
            - **항목 제목(Label)**: 반드시 **`_` (언더바)**로 감싸세요. (파란색 제목)
            - 예: `_어떤 향인가요?_`, `_추천 이유_`, `_정보_`
            - **내용 강조(Highlight)**: 핵심 단어는 **`**` (별표 2개)**로 감싸세요. (핑크색 강조)
            - 예: `처음엔 **상큼한 귤 향**이 나요.`
        
        5. **구분선**: 향수 추천 사이에 `---` 삽입.
        
        6. **정보 표기**: 브랜드, 이름, 출시년도만 기재.
        
        7. **[★필수★] 향 설명 방식 (용어 절대 금지)**:
            - **[절대 금지]**: '탑', '미들', '베이스', '노트', '어코드'라는 단어나 `(탑)`, `(미들)` 같은 괄호 표기를 **절대** 쓰지 마세요.
            - **[작성법]**: 시간의 흐름을 자연스러운 문장으로만 표현하세요.
            - **[예외상황]**:탑/미들/베이스의 노트가 모두 동일할 경우 전체적으로 ~~ 향이 지속된다는 식으로 설명하세요
            - *Bad*: "처음에는 레몬 향이 나요(탑)."
            - *Good*: "처음에는 **막 짠 레몬즙**처럼 상큼하게 시작해요. 시간이 지나면..."
           
        8. **[핵심] 추천 논리 연결 (Why?)**:
            - `_추천 이유_`를 작성할 때, **"왜 이 전략(반전/직관 등)으로 이 향수를 뽑았는지"** 설명하세요.
            - 과한 마케팅 문구(예: "정석", "끝판왕", "감히 추천") 대신 **담백하고 논리적으로** 설득하세요.
            - *Bad*: "시크함의 정석이라 감히 추천드려요."
            - *Good*: "고객님이 **시크한 이미지**를 원하셨죠? 이 향은 **단맛 없이 건조한 나무 향**이라 깔끔하고 도시적인 느낌을 주기에 가장 적합해요."

        9. **[매우 중요] 묘사 및 강조 규칙**:
            - **전문 용어 금지**: 노트, 어코드, 탑/미들/베이스 등은 쓰지 마세요.
            - **쉬운 우리말 번역**: "비에 젖은 나무", "포근한 이불 냄새"처럼 오감이 느껴지게 쓰세요.
            - **★핵심 강조(필수)★**:
            - 향을 묘사하는 **핵심 키워드**나 **비유 표현**은 반드시 **굵게(`**...**`)** 처리하세요.
            - 예: "처음엔 **상큼한 귤껍질 향**이 나다가, 곧 **따뜻한 향신료 차**처럼 변해요."
        [출력 형식 예시]
        
        안녕하세요! 요청하신 시크한 느낌을 3가지 무드로 해석해봤어요.
        
        ## 1. [날카롭고 정돈된 시크] **Chanel - Sycomore**
        ![Sycomore](링크)
        
        - _어떤 향인가요?_: 처음엔 **비 온 뒤의 숲**처럼 차갑고 상쾌해요. 시간이 지나면 **마른 장작** 같은 나무 향이 진해지면서 단정하게 마무리돼요.
        - _추천 이유_: 군더더기 없이 **깔끔하고 드라이한 향**이에요. **차가운 도시 이미지**를 가장 직관적으로 표현하고 싶을 때 완벽한 선택이에요.
        - _정보_: Chanel / Sycomore / 2008년 출시
        
        ---
        
        ## 2. [겉차속따 반전 매력] **Chanel - Coco Noir**
        ...
        """
        
        msg = client.chat.completions.create(
            model=HIGH_PERFORMANCE_MODEL, 
            messages=[{"role": "user", "content": prompt}]
        )
        
        # ================= [ksu] Writer 토큰 집계 =================
        in_tok = msg.usage.prompt_tokens
        out_tok = msg.usage.completion_tokens
        
        total_in = state.get("input_tokens", 0) + in_tok
        total_out = state.get("output_tokens", 0) + out_tok
        # ================= [ksu] Writer 토큰 집계 =================

        raw_content = msg.choices[0].message.content
        
        # [후처리] 강조 공백 제거
        fixed_content = re.sub(r'\*\*\s*(.*?)\s*\*\*', r'**\1**', raw_content)
        
        # ================= [ksu] 테스터 리포트 저장 로직 =================
        test_info = state.get("test_info")
        if test_info:
            try:
                report_dir = "test_reports"
                os.makedirs(report_dir, exist_ok=True)
                
                today = datetime.now().strftime("%Y-%m-%d")
                report_file = os.path.join(report_dir, f"test_{today}.md")
                
                # 비용 & 시간 계산
                cost = (total_in * 1.75 + total_out * 14.00) / 1_000_000
                
                start_ts = test_info.get("start_time", time.time()) # 시작 시간 가져오기
                duration = round(time.time() - start_ts, 2)         # 걸린 시간 계산
                
                # 헤더 생성 (11개 컬럼 복구)
                if not os.path.exists(report_file):
                    headers = [
                        "시간", "목적", "시나리오", "환경", 
                        "입력", "기대값", "실제출력(요약)", 
                        "소요시간(초)", "비용($)", "토큰(In/Out)", "분석/비고"
                    ]
                    with open(report_file, "w", encoding="utf-8") as f:
                        f.write(f"# 🧪 Chat Test Report ({today})\n\n")
                        f.write("| " + " | ".join(headers) + " |\n")
                        f.write("|" + "---|" * len(headers) + "\n")
                # 행 추가
                now_time = datetime.now().strftime("%H:%M:%S")
                summary = fixed_content[:50].replace("\n", " ") + "..."
                row = [
                    now_time,
                    test_info['purpose'],
                    test_info['scenario'],
                    "Chat/GPT-5.2",
                    query,
                    test_info['expected'],
                    summary,
                    f"{duration}s",        # [추가됨]
                    f"${round(cost, 6)}",
                    f"{total_in}/{total_out}",
                    ""                     # [추가됨] 비고
                ]
                with open(report_file, "a", encoding="utf-8") as f:
                    f.write("| " + " | ".join([str(x) for x in row]) + " |\n")
                    
                print(f"📝 [Test Report] 기록 완료", flush=True)
            except Exception as e:
                print(f"⚠️ [Report Error] {e}", flush=True)
        # ========================= [ksu] 테스터 리포트 저장 로직 =========================

        return {"final_response": fixed_content,
                "input_tokens": total_in,   # [ksu] 토큰 사용량 누적
                "output_tokens": total_out}  # [ksu] 토큰 사용량 누적
        
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
        # {"researcher": "researcher", "end": END}
        {"researcher": "researcher", "writer": "writer", "end": END}
    )
    
    graph.add_edge("researcher", "writer")
    graph.add_edge("writer", END)
    
    # 메모리 저장소(Checkpointer) 적용
    memory = MemorySaver()
    
    return graph.compile(checkpointer=memory)