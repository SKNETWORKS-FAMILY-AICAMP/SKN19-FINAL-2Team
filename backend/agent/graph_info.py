# backend/agent/graph_info.py
import json
import asyncio
from typing import Literal, Any
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END

# [1] 스키마 임포트
from .schemas import InfoState, InfoRoutingDecision, IngredientAnalysisResult

# [2] 도구 임포트
from .tools import (
    lookup_perfume_info_tool,
    lookup_perfume_by_id_tool,
    lookup_note_info_tool,
    lookup_accord_info_tool,
    lookup_similar_perfumes_tool,
)

# [3] 프롬프트 임포트
from .prompts import (
    INFO_SUPERVISOR_PROMPT,
    PERFUME_DESCRIBER_PROMPT_BEGINNER,
    PERFUME_DESCRIBER_PROMPT_EXPERT,
    SIMILARITY_CURATOR_PROMPT_BEGINNER,
    SIMILARITY_CURATOR_PROMPT_EXPERT,
    INGREDIENT_SPECIALIST_PROMPT,
)

# [4] Expression Loader for dynamic dictionary injection
from .expression_loader import ExpressionLoader

load_dotenv()

# [LLM 이원화]
INFO_LLM = ChatOpenAI(model="gpt-4.1", temperature=0, streaming=True)
ROUTER_LLM = ChatOpenAI(model="gpt-4.1", temperature=0, streaming=False)


# ==========================================
# 4. Utility Functions (moved to utils.py)
# ==========================================

from .utils import (
    extract_save_refs,
    parse_ordinal,
    resolve_target_from_ordinal_or_pronoun,
    classify_info_status,
)


# ==========================================
# 5. Node Functions
# ==========================================


def info_supervisor_node(state: InfoState):
    """[Router] 분류 노드"""
    print(f"\n   ▶️ [Info Subgraph] Supervisor 노드 시작", flush=True)
    user_query = state.get("user_query", "")

    chat_history = state.get("messages", [])
    context_str = ""
    if chat_history:
        recent_msgs = chat_history[-3:] if len(chat_history) > 3 else chat_history
        for msg in recent_msgs:
            role = "User" if isinstance(msg, HumanMessage) else "AI"
            if msg.content:
                context_str += f"- {role}: {msg.content}\n"

    final_system_prompt = INFO_SUPERVISOR_PROMPT
    if context_str:
        final_system_prompt += f"\n\n[Recent Chat Context]\n{context_str}"

    final_system_prompt += "\n\n[Instruction]\nResolve the target name from context and classify based on the PRIORITY rules."

    messages = [
        SystemMessage(content=final_system_prompt),
        HumanMessage(content=user_query),
    ]

    # [Phase 0] Ordinal 번호 먼저 체크 (LLM 호출 전)
    save_refs = extract_save_refs(chat_history)
    ordinal = parse_ordinal(user_query)
    
    if ordinal and save_refs:
        # number 필드 기준으로 검색
        target_ref = None
        for ref in save_refs:
            if ref.get("number") == ordinal:
                target_ref = ref
                break
        
        if target_ref:
            # Ordinal로 직접 타겟 결정 (LLM 호출 불필요)
            target_id = target_ref['id']
            target_name = target_ref['name']
            
            # info_type 결정: "비슷한/추천/대체" 키워드 체크
            if any(kw in user_query for kw in ['비슷', '추천', '대체', '같은']):
                info_type = "similarity"
            else:
                info_type = "perfume"
            
            print(f"   ✅ [Ordinal] {ordinal}번째 향수 직접 선택: {target_name} (type: {info_type})", flush=True)
            
            return {
                "info_type": info_type,
                "target_id": target_id,
                "target_name": target_name,
                "target_brand": None,
                "target_name_kr": None
            }
        else:
            fail_msg = f"지금 추천은 1~{len(save_refs)}번째까지 있어요. 원하시는 번호로 다시 말씀해 주세요."
            return {"info_type": "unknown", "target_name": "unknown", "fail_msg": fail_msg}
    
    try:
        decision = ROUTER_LLM.with_structured_output(InfoRoutingDecision).invoke(
            messages
        )

        # [Phase 1] 기본 지식 질문이면 save_refs 체크 없이 바로 처리
        if decision.info_type in ["note", "accord", "ingredient"]:
            print(f"   📚 Basic knowledge query detected: {decision.info_type}", flush=True)
            return {
                "info_type": decision.info_type,
                "target_name": decision.target_name,
                "target_brand": decision.target_brand,
                "target_name_kr": decision.target_name_kr
            }

        # [Phase 3] 브랜드 및 이중 언어 추출
        final_target = decision.target_name
        final_brand = decision.target_brand
        final_target_kr = decision.target_name_kr

        resolved = resolve_target_from_ordinal_or_pronoun(
            user_query, final_target, save_refs
        )

        if resolved:
            ordinal = parse_ordinal(user_query)

            info_type = decision.info_type
            if any(kw in user_query for kw in ['비슷', '추천', '대체', '같은']):
                info_type = "similarity"
            elif resolved:
                info_type = "perfume"

            return {
                "info_type": info_type,
                "target_id": resolved['id'],
                "target_name": resolved['name'],
                "target_brand": final_brand,
                "target_name_kr": final_target_kr
            }

        if not save_refs and (parse_ordinal(user_query) or any(p in user_query for p in ['이거', '그거', '이 향수', '저거'])):
            fail_msg = "최근에 추천드린 향수 목록을 찾지 못했어요. 향수 이름을 직접 말씀해 주시면 바로 찾아드릴게요."
            return {"info_type": "unknown", "target_name": "unknown", "fail_msg": fail_msg}

        ordinal = parse_ordinal(user_query)
        if ordinal and ordinal > len(save_refs):
            fail_msg = f"지금 추천은 1~{len(save_refs)}번째까지 있어요. 원하시는 번호로 다시 말씀해 주세요."
            return {"info_type": "unknown", "target_name": "unknown", "fail_msg": fail_msg}

        if not final_target or final_target in [
            "이거",
            "그거",
            "이 향수",
            "추천해줘",
            "비슷한거",
        ]:
            return {"info_type": "unknown", "target_name": "unknown"}

        return {
            "info_type": decision.info_type,
            "target_name": final_target,
            "target_brand": final_brand,
            "target_name_kr": final_target_kr
        }

    except Exception as e:
        print(f"      ❌ Supervisor 에러 발생: {e}", flush=True)
        return {"info_type": "unknown", "target_name": "unknown"}


async def perfume_search_node(state: InfoState):
    """[Search] 향수 상세 정보 조회"""
    print(f"\n   🔍 [Perfume Search] 검색 시작", flush=True)

    target = state["target_name"]
    target_id = state.get("target_id")

    try:
        if target_id:
            search_result = await lookup_perfume_by_id_tool.ainvoke({"perfume_id": target_id})
        else:
            search_result = await lookup_perfume_info_tool.ainvoke(target)

        # [Wave 2] 검색 결과 상태 분류 (객체 기반)
        status = classify_info_status(search_result)

        if status != "OK":
            # Retry with name if we have both ID and name
            if target_id and target:
                search_result = await lookup_perfume_info_tool.ainvoke(target)
                status = classify_info_status(search_result)

        if status != "OK":
            return {"info_status": status}

        # 검색 성공 - info_payload에 JSON 문자열로 저장
        return {
            "info_payload": json.dumps(search_result, ensure_ascii=False),
            "info_status": "OK"
        }

    except Exception as e:
        print(f"      ❌ Perfume Search 에러: {e}", flush=True)
        return {"info_status": "ERROR"}


async def perfume_describer_node(state: InfoState):
    """[Writer] 향수 상세 정보 출력 (DB/도구 호출 금지)"""
    print(f"\n   ✍️ [Perfume Describer - Writer] 출력 생성 중", flush=True)

    target = state["target_name"]
    user_mode = state.get("user_mode", "BEGINNER")
    search_result_json = state.get("info_payload", "")

    if not search_result_json:
        print("      ⚠️ [Perfume Describer] info_payload 없음", flush=True)
        return {"info_status": "ERROR"}

    try:
        if user_mode == "EXPERT":
            print("      😎 [Mode] 전문가용 분석 프롬프트 적용", flush=True)
            selected_prompt = PERFUME_DESCRIBER_PROMPT_EXPERT
        else:
            print("      🐥 [Mode] 비기너용 도슨트 프롬프트 적용", flush=True)
            selected_prompt = PERFUME_DESCRIBER_PROMPT_BEGINNER

        # [★ Dynamic Expression Injection]
        # Parse perfume data to extract notes and accords
        try:
            perfume_data = json.loads(search_result_json)
            perfume_name = perfume_data.get("name", "Unknown")
            brand = perfume_data.get("brand", "Unknown")

            loader = ExpressionLoader()
            expression_guide = []
            injected_count = 0

            all_notes = []
            all_accords = []

            # Extract notes
            for note_type in ["top_notes", "middle_notes", "base_notes"]:
                note_str = perfume_data.get(note_type, "")
                if note_str and note_str != "N/A":
                    notes = [n.strip() for n in note_str.split(",")]
                    all_notes.extend(notes)
                    for note in notes[:5]:  # Limit per type
                        desc = loader.get_note_desc(note)
                        if desc:
                            expression_guide.append(f"- {note}: {desc}")
                            injected_count += 1

            # Extract accords
            accord_str = perfume_data.get("accords", "")
            if accord_str:
                accords = [a.strip() for a in accord_str.split(",")]
                all_accords = accords
                for accord in accords[:5]:
                    desc = loader.get_accord_desc(accord)
                    if desc:
                        expression_guide.append(f"- {accord}: {desc}")
                        injected_count += 1

            expression_text = "\n".join(expression_guide) if expression_guide else ""

        except Exception as e:
            expression_text = ""

        content_parts = [f"대상 향수: {target}"]
        if expression_text:
            content_parts.append(f"\n[감각 표현 참고]:\n{expression_text}")
        content_parts.append(f"\n[검색된 상세 정보]:\n{search_result_json}")

        messages = [
            SystemMessage(content=selected_prompt),
            HumanMessage(content="\n".join(content_parts)),
        ]
        response = await INFO_LLM.ainvoke(messages)

        return {"messages": [response], "final_answer": response.content, "info_status": "OK"}

    except Exception as e:
        print(f"      ❌ Perfume Describer 에러: {e}", flush=True)
        return {"info_status": "ERROR"}


async def ingredient_search_node(state: InfoState):
    """[Search] 노트/어코드 검색"""
    print(f"\n   🔍 [Ingredient Search] 검색 시작", flush=True)

    try:
        user_query = state.get("user_query", "")
        target_name = state.get("target_name", "")

        # 1. 쿼리 분석
        analysis_prompt = f"""
        You are a query analyzer. Separate 'Notes' and 'Accords'.
        Query: "{user_query}"
        Context Target: "{target_name}"
        Output JSON: {{ "notes": [], "accords": [], "is_ambiguous": false }}
        """

        try:
            analysis = await ROUTER_LLM.with_structured_output(
                IngredientAnalysisResult
            ).ainvoke(analysis_prompt, config={"tags": ["internal_helper"]})
            print(
                f"      - 분석 결과: Notes={analysis.notes}, Accords={analysis.accords}",
                flush=True,
            )
        except Exception as e:
            print(f"      ⚠️ 분석 실패: {e}", flush=True)
            analysis = IngredientAnalysisResult(notes=[target_name], accords=[])

        # 2. 병렬 도구 호출
        tasks = []
        tasks.append(
            lookup_note_info_tool.ainvoke({"keywords": analysis.notes})
            if analysis.notes
            else asyncio.sleep(0, result="")
        )
        tasks.append(
            lookup_accord_info_tool.ainvoke({"keywords": analysis.accords})
            if analysis.accords
            else asyncio.sleep(0, result="")
        )

        results = await asyncio.gather(*tasks)
        note_result, accord_result = results[0], results[1]

        # 3. 상세 로깅
        def print_result_log(category: str, result_obj: Any):
            if not result_obj:
                return
            try:
                # 객체를 직접 처리
                data = result_obj if isinstance(result_obj, dict) else {}
                if not data:
                    print(f"      🔍 [{category}]: 결과 없음 (Empty)", flush=True)
                    return
                for key, val in data.items():
                    if isinstance(val, dict):
                        perfumes = val.get("representative_perfumes", [])
                        perfume_log = ", ".join(perfumes) if perfumes else "없음"
                        print(
                            f"      🔍 [{category}] '{key}': (대표향수: {perfume_log})",
                            flush=True,
                        )
            except:
                pass

        print_result_log("Note DB", note_result)
        print_result_log("Accord DB", accord_result)

        # 4. 검색 결과 상태 분류 (객체 기반)
        note_status = classify_info_status(note_result)
        accord_status = classify_info_status(accord_result)

        # 둘 다 NO_RESULTS 또는 ERROR면 실패
        if note_status != "OK" and accord_status != "OK":
            if note_status == "ERROR" or accord_status == "ERROR":
                return {"info_status": "ERROR"}
            else:
                return {"info_status": "NO_RESULTS"}

        # 5. 검색 성공 - info_payload에 결과 저장 (JSON 직렬화)
        payload = {
            "analysis": {
                "notes": analysis.notes,
                "accords": analysis.accords,
            },
            "note_result": note_result,  # 이미 객체 (dict 또는 list)
            "accord_result": accord_result,  # 이미 객체 (dict 또는 list)
        }

        return {
            "info_payload": json.dumps(payload, ensure_ascii=False),
            "info_status": "OK",
        }

    except Exception as e:
        print(f"      ❌ Ingredient Search 에러: {e}", flush=True)
        return {"info_status": "ERROR"}


async def ingredient_specialist_node(state: InfoState):
    """[Writer] 노트/어코드 설명 출력 (DB/도구 호출 금지)"""
    print(f"\n   ✍️ [Ingredient Specialist - Writer] 출력 생성 중", flush=True)

    try:
        info_payload_str = state.get("info_payload", "")
        if not info_payload_str:
            print("      ⚠️ [Ingredient Specialist] info_payload 없음", flush=True)
            return {"info_status": "ERROR"}

        # info_payload 파싱
        payload = json.loads(info_payload_str)
        analysis_notes = payload["analysis"]["notes"]
        analysis_accords = payload["analysis"]["accords"]
        note_result = payload["note_result"]
        accord_result = payload["accord_result"]

        # Dynamic Expression Injection
        loader = ExpressionLoader()
        expression_guide = []

        for note in analysis_notes[:10]:
            desc = loader.get_note_desc(note)
            if desc:
                expression_guide.append(f"- {note}: {desc}")

        for accord in analysis_accords[:10]:
            desc = loader.get_accord_desc(accord)
            if desc:
                expression_guide.append(f"- {accord}: {desc}")

        expression_text = "\n".join(expression_guide) if expression_guide else ""

        context_parts = [
            f"[User Interest]: Notes: {analysis_notes}, Accords: {analysis_accords}",
        ]

        if expression_text:
            context_parts.append(f"\n[감각 표현 참고]:\n{expression_text}")

        # 객체를 JSON 문자열로 변환하여 LLM에 전달
        note_result_str = json.dumps(note_result, ensure_ascii=False) if isinstance(note_result, dict) else str(note_result)
        accord_result_str = json.dumps(accord_result, ensure_ascii=False) if isinstance(accord_result, dict) else str(accord_result)

        context_parts.append(f"""
        [Search Results]:
        --- Note Data ---
        {note_result_str}
        --- Accord Data ---
        {accord_result_str}
        """)

        combined_context = "\n".join(context_parts)

        messages = [
            SystemMessage(content=INGREDIENT_SPECIALIST_PROMPT),
            HumanMessage(content=combined_context),
        ]
        response = await INFO_LLM.ainvoke(messages)

        return {"messages": [response], "final_answer": response.content, "info_status": "OK"}

    except Exception as e:
        print(f"      ❌ Ingredient Specialist 에러: {e}", flush=True)
        return {"info_status": "ERROR"}


async def similarity_search_node(state: InfoState):
    """[Search] 유사 향수 검색"""
    print(f"\n   🔍 [Similarity Search] 검색 시작", flush=True)

    try:
        # [Phase 4] 브랜드 및 이중 언어 활용
        target_name = state["target_name"]
        target_brand = state.get("target_brand", "")
        target_name_kr = state.get("target_name_kr", "")

        # 파이프 구분자로 정보 전달 (브랜드|영어명|한글명)
        search_input = f"{target_brand}|{target_name}|{target_name_kr}"

        # 도구 호출 (객체 반환)
        search_result = await lookup_similar_perfumes_tool.ainvoke(search_input)

        # 검색 결과 상태 분류 (객체 기반)
        status = classify_info_status(search_result)

        if status != "OK":
            return {"info_status": status}

        # 검색 성공 - info_payload에 JSON 문자열로 저장
        return {
            "info_payload": json.dumps(search_result, ensure_ascii=False),
            "info_status": "OK",
        }

    except Exception as e:
        print(f"      ❌ Similarity Search 에러: {e}", flush=True)
        return {"info_status": "ERROR"}


async def similarity_curator_node(state: InfoState):
    """[Writer] 유사 향수 추천 출력 (DB/도구 호출 금지)"""
    print(f"\n   ✍️ [Similarity Curator - Writer] 출력 생성 중", flush=True)

    try:
        # [Phase 4] 한글명 우선 표시
        target_name_kr = state.get("target_name_kr")
        target_name = state.get("target_name", "")
        target = target_name_kr if target_name_kr else target_name

        user_mode = state.get("user_mode", "BEGINNER")
        search_result_json = state.get("info_payload", "")

        if not search_result_json:
            print("      ⚠️ [Similarity Curator] info_payload 없음", flush=True)
            return {"info_status": "ERROR"}

        if user_mode == "EXPERT":
            print("      😎 [Mode] 전문가용 큐레이터 프롬프트 적용", flush=True)
            selected_prompt = SIMILARITY_CURATOR_PROMPT_EXPERT
        else:
            print("      🐥 [Mode] 비기너용 도슨트 프롬프트 적용", flush=True)
            selected_prompt = SIMILARITY_CURATOR_PROMPT_BEGINNER

        messages = [
            SystemMessage(content=selected_prompt),
            HumanMessage(
                content=f"원본 향수: {target}\n\n[추천 후보군 데이터]:\n{search_result_json}"
            ),
        ]
        response = await INFO_LLM.ainvoke(messages)

        return {"messages": [response], "final_answer": response.content, "info_status": "OK"}

    except Exception as e:
        print(f"      ❌ Similarity Curator 에러: {e}", flush=True)
        return {"info_status": "ERROR"}


async def fallback_handler_node(state: InfoState):
    """[Fallback] 안내"""
    print(f"\n   ⚠️ [Info Subgraph] Fallback Handler 실행", flush=True)

    fail_msg = state.get("fail_msg")
    if fail_msg:
        return {"messages": [AIMessage(content=fail_msg)], "final_answer": fail_msg}

    fallback_msg = "죄송합니다. 말씀하신 향수가 무엇인지 정확히 파악하지 못했어요. 😅\n'샤넬 넘버5랑 비슷한 거 추천해줘' 처럼 향수 이름을 콕 집어서 다시 말씀해 주시겠어요?"
    return {"messages": [AIMessage(content=fallback_msg)], "final_answer": fallback_msg}


# ==========================================
# 5-1. Result Router and Status-Specific Nodes (Wave 2)
# ==========================================

def info_result_router_node(state: InfoState):
    """
    info_status 값에 따라 다음 노드로 라우팅합니다.
    
    Returns:
        다음 노드 이름 ('info_writer' | 'info_no_results' | 'info_error')
    """
    info_status = state.get("info_status", "OK")
    
    print(f"\n   🔀 [Info Router] Status: {info_status}", flush=True)
    
    if info_status == "NO_RESULTS":
        return "info_no_results"
    elif info_status == "ERROR":
        return "info_error"
    else:
        return "info_writer"


async def info_no_results_node(state: InfoState):
    """
    검색 결과가 없을 때 대안을 제시하는 노드입니다.
    """
    print(f"\n   ❌ [Info No Results] 검색 결과 없음 처리", flush=True)

    # [Phase 4] 한글명 우선 표시
    target_name_kr = state.get("target_name_kr")
    target_name = state.get("target_name", "해당 항목")
    display_name = target_name_kr if target_name_kr else target_name

    info_type = state.get("info_type", "unknown")

    if info_type == "perfume":
        msg = f"죄송합니다. '{display_name}'에 대한 상세 정보를 데이터베이스에서 찾을 수 없습니다. 😢\n\n다른 향수 이름으로 다시 검색해 보시거나, '플로랄 향수 추천해줘' 같은 방식으로 물어봐 주세요!"
    elif info_type in ["note", "accord", "ingredient"]:
        msg = f"죄송합니다. '{display_name}' 성분에 대한 상세 정보가 현재 데이터베이스에 등록되어 있지 않습니다. 😢\n\n'우디', '플로랄', '시트러스' 같은 일반적인 노트나 어코드로 다시 물어봐 주세요!"
    elif info_type == "similarity":
        msg = f"현재 저희 데이터베이스에는 '{display_name}'과 결이 비슷한 향수 정보가 충분하지 않네요. 😅\n\n다른 향수로 다시 찾아봐 드릴까요?"
    else:
        msg = f"죄송합니다. '{display_name}'에 대한 정보를 찾을 수 없습니다. 😢\n\n향수 이름을 정확히 말씀해 주시거나, 다른 방식으로 질문해 주세요!"

    return {"messages": [AIMessage(content=msg)], "final_answer": msg}


async def info_error_node(state: InfoState):
    """
    기술적 오류 발생 시 고정 문구를 출력하는 노드입니다.
    """
    print(f"\n   ❌ [Info Error] 기술적 오류 처리", flush=True)

    msg = "죄송합니다. 현재 알 수 없는 오류가 발생하였습니다. 잠시 후 다시 시도해 주세요. 🙏"

    return {"messages": [AIMessage(content=msg)], "final_answer": msg}


async def info_writer_node(state: InfoState):
    """
    OK 상태일 때 검색 결과를 형식화/요약하는 노드입니다.
    근거 없는 새 사실 생성 금지 (ZERO HALLUCINATION).
    """
    print(f"\n   ✍️ [Info Writer] 결과 형식화", flush=True)

    final_answer = state.get("final_answer")
    if final_answer:
        print(f"      ℹ️ [Info Writer] 기존 답변 사용 (이미 처리됨)", flush=True)
        return {"messages": [AIMessage(content=final_answer)]}

    print(f"      ⚠️ [Info Writer] final_answer 없음, fallback 처리", flush=True)
    msg = "죄송합니다. 답변을 생성하는 중 문제가 발생했습니다."
    return {"messages": [AIMessage(content=msg)], "final_answer": msg}


# ==========================================
# 6. Graph Build (Info Subgraph) - Search/Writer 분리
# ==========================================
info_workflow = StateGraph(InfoState)

# [Router]
info_workflow.add_node("info_supervisor", info_supervisor_node)

# [Search Nodes]
info_workflow.add_node("perfume_search", perfume_search_node)
info_workflow.add_node("ingredient_search", ingredient_search_node)
info_workflow.add_node("similarity_search", similarity_search_node)

# [Writer Nodes]
info_workflow.add_node("perfume_describer", perfume_describer_node)
info_workflow.add_node("ingredient_specialist", ingredient_specialist_node)
info_workflow.add_node("similarity_curator", similarity_curator_node)

# [Status Handler Nodes]
info_workflow.add_node("info_no_results", info_no_results_node)
info_workflow.add_node("info_error", info_error_node)
info_workflow.add_node("info_writer", info_writer_node)
info_workflow.add_node("fallback_handler", fallback_handler_node)

# [Routing] START → Supervisor
info_workflow.add_edge(START, "info_supervisor")

# [Routing] Supervisor → Search Nodes
info_workflow.add_conditional_edges(
    "info_supervisor",
    lambda x: x["info_type"],
    {
        "perfume": "perfume_search",
        "brand": "perfume_search",
        "note": "ingredient_search",
        "accord": "ingredient_search",
        "ingredient": "ingredient_search",
        "similarity": "similarity_search",
        "unknown": "fallback_handler",
    },
)

# [Routing] Search Nodes → Writer Nodes (status 기반)
info_workflow.add_conditional_edges(
    "perfume_search",
    info_result_router_node,
    {
        "info_writer": "perfume_describer",  # OK면 Writer로
        "info_no_results": "info_no_results",
        "info_error": "info_error",
    },
)

info_workflow.add_conditional_edges(
    "ingredient_search",
    info_result_router_node,
    {
        "info_writer": "ingredient_specialist",  # OK면 Writer로
        "info_no_results": "info_no_results",
        "info_error": "info_error",
    },
)

info_workflow.add_conditional_edges(
    "similarity_search",
    info_result_router_node,
    {
        "info_writer": "similarity_curator",  # OK면 Writer로
        "info_no_results": "info_no_results",
        "info_error": "info_error",
    },
)

# [Routing] Writer Nodes → info_writer (passthrough)
info_workflow.add_edge("perfume_describer", "info_writer")
info_workflow.add_edge("ingredient_specialist", "info_writer")
info_workflow.add_edge("similarity_curator", "info_writer")

# [Routing] Status Handler Nodes → END
info_workflow.add_edge("fallback_handler", END)
info_workflow.add_edge("info_writer", END)
info_workflow.add_edge("info_no_results", END)
info_workflow.add_edge("info_error", END)

info_graph = info_workflow.compile()
