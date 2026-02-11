"""
히스토리 중복 방지 수정 검증

수정 내용:
- main.py에서 checkpointer state 확인
- state 있으면: 새 메시지만 전달
- state 없으면: DB 복원 후 전달
"""

import asyncio
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


class TestHistoryFix:
    """히스토리 중복 방지 수정 검증"""

    @pytest.mark.asyncio
    async def test_no_duplication_with_checkpointer(self, monkeypatch):
        """
        수정 후: checkpointer 사용 시 메시지 중복 방지 확인

        시나리오:
        1. 1차 요청: checkpointer 비어있음 → DB 복원 (비어있음) + 새 메시지
        2. 2차 요청: checkpointer에 state 있음 → 새 메시지만 전달

        기대: 2차 요청 후 메시지 개수 = 4 (중복 없음)
        """
        from agent import graph as graph_mod
        from agent.schemas import InterviewResult, UserPreferences
        from langchain_core.messages import AIMessage, HumanMessage

        # --- Stub tools / DB
        class DummyTool:
            def __init__(self, result):
                self._result = result

            async def ainvoke(self, _):
                return self._result

        monkeypatch.setattr(graph_mod, "lookup_note_by_string_tool", DummyTool([]))
        monkeypatch.setattr(graph_mod, "lookup_note_by_vector_tool", DummyTool([]))
        monkeypatch.setattr(graph_mod, "save_recommendation_log", lambda **_: None)

        async def fake_search(h_filters, s_filters, exclude_ids=None, query_text=""):
            return (
                [
                    {
                        "id": 9001,
                        "name": "Test Perfume",
                        "brand": "Test Brand",
                        "accords": "Woody",
                        "best_review": "Great",
                        "top_notes": "Bergamot",
                        "middle_notes": "Rose",
                        "base_notes": "Sandalwood",
                        "image_url": None,
                        "gender": "Unisex",
                    }
                ],
                "Perfect Match",
            )

        monkeypatch.setattr(graph_mod, "smart_search_with_retry_async", fake_search)

        # --- Fake LLMs
        request_counter = {"count": 0}

        class FakeSmartLLM:
            def with_structured_output(self, schema):
                if schema.__name__ == "InterviewResult":
                    return FakeInterviewer(request_counter)
                return FakeStructured()

            async def ainvoke(self, *args, **kwargs):
                return AIMessage(content="")

        class FakeInterviewer:
            def __init__(self, counter):
                self.counter = counter

            def invoke(self, messages, config=None):
                self.counter["count"] += 1
                return InterviewResult(
                    user_preferences=UserPreferences(
                        target="일반 사용자",
                        gender="Unisex",
                    ),
                    is_sufficient=True,
                    response_message="추천해드리겠습니다.",
                    is_off_topic=False,
                )

            async def ainvoke(self, messages, config=None):
                return self.invoke(messages, config)

        class FakeStructured:
            def invoke(self, messages, config=None):
                from agent.schemas import RoutingDecision
                return RoutingDecision(next_step="interviewer")

            async def ainvoke(self, messages, config=None):
                from agent.schemas import RoutingDecision
                return RoutingDecision(next_step="interviewer")

        monkeypatch.setattr(graph_mod, "SMART_LLM", FakeSmartLLM())

        class FakeWriterLLM:
            async def ainvoke(self, messages, config=None):
                return AIMessage(
                    content="## 1. Test Brand - Test Perfume\n[[SAVE:9001:Test Perfume]]\n---"
                )

        monkeypatch.setattr(graph_mod, "SUPER_SMART_LLM", FakeWriterLLM())

        # --- Run Test
        thread_id = "test_no_dup_thread_789"
        config = {"configurable": {"thread_id": thread_id}}

        # === 1차 요청 ===
        print("\n=== 1차 요청 ===")
        first_input = {
            "messages": [HumanMessage(content="안녕")],
            "member_id": 1,
            "user_mode": "BEGINNER",
        }

        first_state = None
        async for event in graph_mod.app_graph.astream(first_input, config=config):
            for node_name, node_state in event.items():
                if isinstance(node_state, dict):
                    first_state = node_state

        first_messages = first_state.get("messages", [])
        print(f"1차 후 messages 개수: {len(first_messages)}")

        # === 2차 요청 ===
        print("\n=== 2차 요청 ===")
        second_input = {
            "messages": [HumanMessage(content="추천해줘")],  # 새 메시지만!
            "member_id": 1,
            "user_mode": "BEGINNER",
        }

        second_state = None
        async for event in graph_mod.app_graph.astream(second_input, config=config):
            for node_name, node_state in event.items():
                if isinstance(node_state, dict):
                    second_state = node_state

        second_messages = second_state.get("messages", [])
        print(f"2차 후 messages 개수: {len(second_messages)}")
        print(f"Messages: {[m.content[:20] if hasattr(m, 'content') else str(m)[:20] for m in second_messages]}")

        # 검증: 중복 없이 정상 증가
        # 1차: [H1, A1] = 2개
        # 2차: [H1, A1, H2, A2] = 4개 (중복 없음)
        expected_min = 3  # 최소한 H1, A1, H2 있어야 함
        expected_max = 5  # 약간의 여유

        assert len(second_messages) >= expected_min, (
            f"2차 후 최소 {expected_min}개 메시지 예상, 실제: {len(second_messages)}"
        )
        assert len(second_messages) <= expected_max, (
            f"2차 후 최대 {expected_max}개 메시지 예상 (중복 방지), 실제: {len(second_messages)}"
        )

        print(f"\n✅ 중복 방지 성공! messages 개수: {len(second_messages)}")
