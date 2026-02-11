"""
TDD RED Phase: 브랜드 누수 방지 테스트

이 테스트는 현재 상태에서 FAIL해야 함 (RED phase).
같은 thread_id에서 주제가 전환될 때 이전 브랜드가 user_preferences에 누수되는 것을 탐지.

테스트 목표:
1. 1차 요청: "딥디크 추천해줘" → user_preferences에 brand="딥디크" 포함
2. 2차 요청: "겨울 남자 향수 추천해줘" → user_preferences에 brand가 없거나 "딥디크"가 아님
3. 현재 버그: 2차 요청에서도 brand="딥디크"가 유지됨 (누수 발생)
"""

import asyncio
import sys
from pathlib import Path

import pytest  # type: ignore[import-not-found]


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


class TestBrandLeakage:
    """브랜드 누수 방지 테스트 스위트"""
    
    @pytest.mark.asyncio
    async def test_brand_leakage_across_topic_changes(self, monkeypatch):
        """
        RED: 같은 thread_id에서 주제 전환 시 이전 브랜드가 누수되는지 확인
        
        현재 상태에서 이 테스트는 FAIL해야 함.
        (user_preferences 병합 로직이 {**old, **new} 패턴을 사용하여 
         이전 브랜드가 제거되지 않고 유지되기 때문)
        
        시나리오:
        1. "딥디크 추천해줘" → brand="딥디크"
        2. "겨울 남자 향수 추천해줘" → brand 없음 (또는 다른 값)
        
        기대: 2차 요청에서 brand가 "딥디크"로 고정되지 않아야 함
        실제 (버그): 2차 요청에서도 brand="딥디크"가 유지됨
        """
        from agent import graph as graph_mod
        from agent.schemas import InterviewResult, UserPreferences
        from langchain_core.messages import AIMessage, HumanMessage  # type: ignore[import-not-found]
        
        # --- Stub tools / DB
        class DummyTool:
            def __init__(self, result):
                self._result = result
            
            async def ainvoke(self, _):
                return self._result
        
        monkeypatch.setattr(graph_mod, "lookup_note_by_string_tool", DummyTool([]))
        monkeypatch.setattr(graph_mod, "lookup_note_by_vector_tool", DummyTool([]))
        monkeypatch.setattr(graph_mod, "save_recommendation_log", lambda **_: None)
        
        # Stub search to avoid actual DB calls
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
        
        # --- Fake SMART_LLM (Interviewer, Supervisor, Researcher planner)
        # Track which request we're on
        request_counter = {"count": 0}
        
        class FakeSmartLLM:
            def with_structured_output(self, schema):
                # For InterviewResult
                if schema.__name__ == "InterviewResult":
                    return FakeInterviewer(request_counter)
                # For other structured outputs (RoutingDecision, ResearchActionPlan, etc.)
                return FakeStructured()
            
            async def ainvoke(self, *args, **kwargs):
                # For supervisor/other LLM calls
                return AIMessage(content="")
        
        class FakeInterviewer:
            def __init__(self, counter):
                self.counter = counter

            def invoke(self, messages, config=None):
                self.counter["count"] += 1

                # 1차 요청: "딥디크 추천해줘"
                if self.counter["count"] == 1:
                    return InterviewResult(
                        user_preferences=UserPreferences(  # type: ignore[call-arg]
                            target="일반 사용자",
                            gender="Unisex",
                            brand="딥디크",  # 브랜드 하드 필터 설정
                        ),
                        is_sufficient=True,
                        response_message="딥디크 향수를 추천해드리겠습니다.",
                        is_off_topic=False,
                    )

                # 2차 요청: "겨울 남자 향수 추천해줘"
                else:
                    return InterviewResult(
                        user_preferences=UserPreferences(  # type: ignore[call-arg]
                            target="남성",
                            gender="Men",
                            season="겨울",
                            # brand 없음 (새로운 주제, 브랜드 지정 없음)
                        ),
                        is_sufficient=True,
                        response_message="겨울 남성 향수를 추천해드리겠습니다.",
                        is_off_topic=False,
                    )

            async def ainvoke(self, messages, config=None):
                return self.invoke(messages, config)
        
        class FakeStructured:
            def invoke(self, messages, config=None):
                # For RoutingDecision - always route to interviewer
                from agent.schemas import RoutingDecision
                return RoutingDecision(next_step="interviewer")

            async def ainvoke(self, messages, config=None):
                # For RoutingDecision - always route to interviewer
                from agent.schemas import RoutingDecision
                return RoutingDecision(next_step="interviewer")
        
        monkeypatch.setattr(graph_mod, "SMART_LLM", FakeSmartLLM())
        
        # --- Fake SUPER_SMART_LLM (Writer)
        class FakeWriterLLM:
            async def ainvoke(self, messages, config=None):
                return AIMessage(
                    content="## 1. Test Brand - Test Perfume\n[[SAVE:9001:Test Perfume]]\n---"
                )
        
        monkeypatch.setattr(graph_mod, "SUPER_SMART_LLM", FakeWriterLLM())
        
        # --- Run Test
        thread_id = "test_brand_leak_thread_123"
        config = {"configurable": {"thread_id": thread_id}}
        
        # 1차 요청: "딥디크 추천해줘"
        first_input = {
            "messages": [HumanMessage(content="딥디크 추천해줘")],
            "member_id": 1,
            "user_mode": "BEGINNER",
        }
        
        first_state = None
        async for state in graph_mod.app_graph.astream(
            first_input,
            config=config,
            stream_mode="values",
        ):
            first_state = state
        
        # 1차 검증: user_preferences에 brand="딥디크" 포함
        assert first_state is not None, "첫 번째 요청이 완료되지 않았습니다"
        first_prefs = first_state.get("user_preferences", {})
        assert first_prefs.get("brand") == "딥디크", (
            f"1차 요청 후 brand가 '딥디크'이어야 합니다. "
            f"실제: {first_prefs.get('brand')}"
        )
        
        print(f"\n[1차 요청 완료] user_preferences: {first_prefs}")
        
        # 2차 요청: "겨울 남자 향수 추천해줘" (같은 thread_id)
        second_input = {
            "messages": [HumanMessage(content="겨울 남자 향수 추천해줘")],
            "member_id": 1,
            "user_mode": "BEGINNER",
        }
        
        second_state = None
        async for state in graph_mod.app_graph.astream(
            second_input,
            config=config,
            stream_mode="values",
        ):
            second_state = state
        
        # 2차 검증: user_preferences에 brand="딥디크"가 없어야 함
        assert second_state is not None, "두 번째 요청이 완료되지 않았습니다"
        second_prefs = second_state.get("user_preferences", {})
        
        print(f"\n[2차 요청 완료] user_preferences: {second_prefs}")
        
        # RED phase: 이 assertion은 FAIL해야 함 (현재는 "딥디크"가 누수됨)
        assert second_prefs.get("brand") != "딥디크", (
            f"[RED PHASE] 브랜드 누수 발생! "
            f"2차 요청에서 brand가 '딥디크'로 유지되어서는 안 됩니다. "
            f"실제 user_preferences: {second_prefs}"
        )
        
        # 추가 검증: brand가 None이거나 다른 값이어야 함
        # (주제가 전환되었으므로 이전 브랜드 필터가 제거되어야 함)
        assert second_prefs.get("brand") is None or second_prefs.get("brand") == "", (
            f"2차 요청에서 brand가 비어있어야 합니다. "
            f"실제: {second_prefs.get('brand')}"
        )
        
        print(f"\n[성공] 브랜드 누수가 방지되었습니다!")
    
    
    @pytest.mark.asyncio
    async def test_brand_preference_cleared_on_topic_change(self, monkeypatch):
        """
        RED: reference_brand (소프트 필터)도 주제 전환 시 누수되지 않아야 함
        
        시나리오:
        1. "조말론 같은 향수 추천해줘" → reference_brand="조말론"
        2. "여름 향수 추천해줘" → reference_brand 없음
        
        기대: 2차 요청에서 reference_brand가 "조말론"로 고정되지 않아야 함
        """
        from agent import graph as graph_mod
        from agent.schemas import InterviewResult, UserPreferences
        from langchain_core.messages import AIMessage, HumanMessage  # type: ignore[import-not-found]
        
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
                        "id": 9002,
                        "name": "Summer Perfume",
                        "brand": "Summer Brand",
                        "accords": "Citrus",
                        "best_review": "Refreshing",
                        "top_notes": "Lemon",
                        "middle_notes": "Orange",
                        "base_notes": "Musk",
                        "image_url": None,
                        "gender": "Unisex",
                    }
                ],
                "Perfect Match",
            )
        
        monkeypatch.setattr(graph_mod, "smart_search_with_retry_async", fake_search)
        
        # --- Fake LLM
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

                # 1차: "조말론 같은 향수 추천해줘"
                if self.counter["count"] == 1:
                    return InterviewResult(
                        user_preferences=UserPreferences(  # type: ignore[call-arg]
                            target="일반 사용자",
                            gender="Unisex",
                            reference_brand="조말론",  # 참고 브랜드 (소프트 필터)
                        ),
                        is_sufficient=True,
                        response_message="조말론과 유사한 향수를 추천해드리겠습니다.",
                        is_off_topic=False,
                    )

                # 2차: "여름 향수 추천해줘"
                else:
                    return InterviewResult(
                        user_preferences=UserPreferences(  # type: ignore[call-arg]
                            target="일반 사용자",
                            gender="Unisex",
                            season="여름",
                            # reference_brand 없음
                        ),
                        is_sufficient=True,
                        response_message="여름 향수를 추천해드리겠습니다.",
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
                    content="## 1. Summer Brand - Summer Perfume\n[[SAVE:9002:Summer Perfume]]\n---"
                )
        
        monkeypatch.setattr(graph_mod, "SUPER_SMART_LLM", FakeWriterLLM())
        
        # --- Run Test
        thread_id = "test_ref_brand_leak_thread_456"
        config = {"configurable": {"thread_id": thread_id}}
        
        # 1차 요청
        first_input = {
            "messages": [HumanMessage(content="조말론 같은 향수 추천해줘")],
            "member_id": 1,
            "user_mode": "BEGINNER",
        }
        
        first_state = None
        async for state in graph_mod.app_graph.astream(
            first_input,
            config=config,
            stream_mode="values",
        ):
            first_state = state
        
        assert first_state is not None, "첫 번째 요청이 완료되지 않았습니다"
        first_prefs = first_state.get("user_preferences", {})
        assert first_prefs.get("reference_brand") == "조말론"
        print(f"\n[1차 요청] reference_brand: {first_prefs.get('reference_brand')}")
        
        # 2차 요청
        second_input = {
            "messages": [HumanMessage(content="여름 향수 추천해줘")],
            "member_id": 1,
            "user_mode": "BEGINNER",
        }
        
        second_state = None
        async for state in graph_mod.app_graph.astream(
            second_input,
            config=config,
            stream_mode="values",
        ):
            second_state = state
        
        assert second_state is not None, "두 번째 요청이 완료되지 않았습니다"
        second_prefs = second_state.get("user_preferences", {})
        print(f"\n[2차 요청] user_preferences: {second_prefs}")
        
        # RED phase: reference_brand가 누수되어서는 안 됨
        assert second_prefs.get("reference_brand") != "조말론", (
            f"[RED PHASE] reference_brand 누수 발생! "
            f"2차 요청에서 '조말론'이 유지되어서는 안 됩니다. "
            f"실제: {second_prefs.get('reference_brand')}"
        )
        
        assert second_prefs.get("reference_brand") is None or second_prefs.get("reference_brand") == ""
        print(f"\n[성공] reference_brand 누수가 방지되었습니다!")
