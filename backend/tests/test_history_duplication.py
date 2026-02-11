"""
히스토리 중복 누적 재현 테스트

목적: DB 복원 + MemorySaver checkpointer 조합 시 메시지 중복 발생 확인
"""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def test_history_duplication_with_checkpointer():
    """
    재현: DB 복원 + MemorySaver의 메시지 중복 문제

    시나리오:
    1. 1턴: "안녕" → state.messages = [H1, A1]
    2. 2턴: DB에서 [H1, A1] 복원 → inputs = [H1, A1, H2]
           checkpointer가 [H1, A1] 로드
           add_messages 병합 → [H1, A1, H1, A1, H2] (중복!)
    """
    from langchain_core.messages import HumanMessage, AIMessage
    from langgraph.graph import StateGraph, START, END
    from langgraph.checkpoint.memory import MemorySaver
    from typing import Annotated, List
    from langchain_core.messages import BaseMessage
    from langgraph.graph.message import add_messages

    # 간단한 State 정의
    class TestState(dict):
        messages: Annotated[List[BaseMessage], add_messages]

    # 간단한 그래프
    def echo_node(state: TestState):
        last_msg = state["messages"][-1]
        return {"messages": [AIMessage(content=f"Echo: {last_msg.content}")]}

    workflow = StateGraph(TestState)
    workflow.add_node("echo", echo_node)
    workflow.add_edge(START, "echo")
    workflow.add_edge("echo", END)

    checkpointer = MemorySaver()
    app = workflow.compile(checkpointer=checkpointer)

    thread_id = "test_thread_123"
    config = {"configurable": {"thread_id": thread_id}}

    # === 1턴 실행 ===
    print("\n=== 1턴 실행 ===")
    turn1_input = {"messages": [HumanMessage(content="안녕")]}
    turn1_result = app.invoke(turn1_input, config=config)
    turn1_messages = turn1_result["messages"]

    print(f"1턴 후 messages 개수: {len(turn1_messages)}")
    print(f"1턴 messages: {[m.content for m in turn1_messages]}")

    assert len(turn1_messages) == 2, f"1턴 후 2개 메시지 예상, 실제: {len(turn1_messages)}"

    # DB 저장 시뮬레이션 (실제로는 여기서 DB에 저장됨)
    db_history = turn1_messages.copy()

    # === 2턴 실행 (DB 복원 시뮬레이션) ===
    print("\n=== 2턴 실행 (DB 복원) ===")
    # main.py처럼 DB에서 복원한 메시지 + 새 메시지
    turn2_input = {
        "messages": db_history + [HumanMessage(content="추천해줘")]
    }

    print(f"2턴 input messages 개수: {len(turn2_input['messages'])}")
    print(f"2턴 input messages: {[m.content for m in turn2_input['messages']]}")

    turn2_result = app.invoke(turn2_input, config=config)
    turn2_messages = turn2_result["messages"]

    print(f"2턴 후 messages 개수: {len(turn2_messages)}")
    print(f"2턴 messages: {[m.content for m in turn2_messages]}")

    # 검증: 중복이 발생했는가?
    expected_count = 4  # [H1, A1, H2, A2]
    actual_count = len(turn2_messages)

    if actual_count > expected_count:
        print(f"\n❌ 중복 발생! 예상: {expected_count}개, 실제: {actual_count}개")
        print("중복된 메시지 구조:")
        for i, msg in enumerate(turn2_messages):
            print(f"  [{i}] {msg.__class__.__name__}: {msg.content}")
        return True  # 중복 발생
    else:
        print(f"\n✅ 중복 없음. messages 개수: {actual_count}")
        return False  # 중복 없음


if __name__ == "__main__":
    duplicated = test_history_duplication_with_checkpointer()
    if duplicated:
        print("\n🔴 결론: DB 복원 + MemorySaver 조합 시 메시지 중복 발생 확인")
    else:
        print("\n🟢 결론: 메시지 중복 없음 (예상과 다름 - 재확인 필요)")
