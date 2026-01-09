# graph.py
import json
from langgraph.graph import StateGraph, START, END
from schemas import State
from database import METADATA
from tools import (
    client,
    safe_json_parse,
    search_notes_smart,
    search_exact_entity_name,
    execute_search_with_fallback,
)


def supervisor(state: State) -> State:
    return {"route": "researcher"}  # 편의상 고정 (테스트용)


def researcher(state: State) -> State:
    query = state.get("clarified_query") or state["user_query"]
    print(f"\n🕵️ [Researcher] 검색 설계 시작: '{query}'")

    # 👇 [수정됨] 프롬프트에 3번 규칙을 강화했습니다.
    prompt = f"""
    당신은 SQL 검색 조건을 설계하는 전문가입니다.
    사용자 질문: "{query}"
    DB 메타데이터: {json.dumps(METADATA, indent=2, ensure_ascii=False)}
    
    [규칙]
    1. 'filters'에 SQL 조건을 담되, **중요한 조건 순서대로** 배치하세요.
    2. **[필수] 노트(향) 키워드는 반드시 영어(English)로 번역해서 'note_keywords'에 담으세요.** (예: 레몬->Lemon, 흙->Earth)
    3. **[중요] 브랜드나 향수 이름이 한국어인 경우, 반드시 '영어(English)'로 번역해서 'entity_keyword'에 담으세요.** (예: 샤넬 -> Chanel, 디올 -> Dior, 조말론 -> Jo Malone)
    
    응답(JSON):
    {{
        "filters": [ {{ "column": "accord", "value": "Citrus" }} ],
        "note_search_needed": true,
        "note_keywords": ["Lemon"], 
        "entity_search_needed": true,
        "entity_keyword": "Chanel" 
    }}
    """
    try:
        msg = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        plan = safe_json_parse(msg.choices[0].message.content)

        final_filters = []
        if plan.get("entity_search_needed"):
            ex_name = search_exact_entity_name(
                plan["entity_keyword"], plan.get("entity_type", "brand")
            )
            if ex_name:
                final_filters.insert(0, {"column": "brand", "value": ex_name})

        if plan.get("note_search_needed"):
            notes = []
            for k in plan.get("note_keywords", []):
                notes.extend(search_notes_smart(k))
            if notes:
                final_filters.append({"column": "note", "value": list(set(notes))})

        for f in plan.get("filters", []):
            final_filters.append(f)

        result = execute_search_with_fallback(final_filters)
    except Exception as e:
        result = f"오류 발생: {e}"

    return {"research_result": result, "route": "writer"}


def writer(state: State) -> State:
    print("\n✍️ [Writer] 답변 생성 중...")
    prompt = f"""
    당신은 전문 조향사입니다. 아래 [DB 검색 결과]를 바탕으로 추천 답변을 작성하세요.
    
    [사용자 질문]: {state['user_query']}
    [DB 검색 결과]: 
    {state.get('research_result')}
    
    [지침]
    1. **DB에서 찾은 정보(노트, 어코드, 분위기 등)를 상세히 인용하여 설명하세요.**
    2. 단순히 나열하지 말고, "이 향수는 ~한 노트가 어우러져 ~한 느낌을 줍니다" 처럼 스토리텔링 하세요.
    3. 검색된 향수가 없다면 솔직히 말하고 대안을 제시하세요.
    """
    msg = client.chat.completions.create(
        model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}]
    )
    return {"final_response": msg.choices[0].message.content}


def build_graph():
    graph = StateGraph(State)
    graph.add_node("supervisor", supervisor)
    graph.add_node("researcher", researcher)
    graph.add_node("writer", writer)
    graph.add_edge(START, "supervisor")
    graph.add_edge("supervisor", "researcher")
    graph.add_edge("researcher", "writer")
    graph.add_edge("writer", END)
    return graph.compile()
