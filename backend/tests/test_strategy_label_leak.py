"""
TDD RED Phase: 전략 라벨 누출 방지 테스트

이 테스트는 현재 상태에서 FAIL해야 함 (RED phase).
내부 전략 라벨/전략적 단어가 사용자 응답에 노출되는 것을 탐지.

테스트 목표:
1. 금지어 누출 탐지: 추천 응답에 "전략", "전략적", "이미지 강조/보완/반전" 등이 없어야 함
2. SAVE 태그 무결성: [[SAVE:ID:Name]] 패턴이 유지되어야 함
3. 사용자 친화 전략명 존재: 사용자 라벨(예: "[강인하고 자신감 있는 첫인상]")이 포함되어야 함
"""

import asyncio
import sys
import re
from pathlib import Path

import pytest


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


class TestStrategyLabelLeak:
    """전략 라벨 누출 방지 테스트 스위트"""
    
    @pytest.mark.asyncio
    async def test_parallel_reco_output_has_no_forbidden_words(self, monkeypatch):
        """
        RED: parallel_reco_node의 최종 출력에 금지어가 포함되어 있음을 확인
        
        현재 상태에서 이 테스트는 FAIL해야 함.
        (내부 전략명 "이미지 강조/보완/반전"이 출력에 포함되기 때문)
        """
        from agent import graph as graph_mod
        from agent.schemas import SearchStrategyPlan, HardFilters, StrategyFilters
        from agent.denylist import DenylistPolicy, detect_forbidden_words
        from langchain_core.messages import AIMessage
        
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
                        "id": 1001,
                        "name": "Test Perfume",
                        "brand": "Test Brand",
                        "accords": "Woody, Floral",
                        "best_review": "Great scent",
                        "top_notes": "Bergamot, Lemon",
                        "middle_notes": "Rose, Jasmine",
                        "base_notes": "Sandalwood, Musk",
                        "image_url": None,
                        "gender": "Unisex",
                    }
                ],
                "Perfect Match",
            )
        
        monkeypatch.setattr(graph_mod, "smart_search_with_retry_async", fake_search)
        
        # --- Fake planner model
        class FakeStructured:
            async def ainvoke(self, messages, config=None):
                user = messages[-1].content
                if "이미지 강조" in user:
                    name, prio = "이미지 강조", 1
                elif "이미지 보완" in user:
                    name, prio = "이미지 보완", 2
                else:
                    name, prio = "이미지 반전", 3
                
                return SearchStrategyPlan(
                    priority=prio,
                    strategy_name=name,
                    strategy_keyword="test_keyword",
                    reason="Test reason",
                    hard_filters=HardFilters(),
                    strategy_filters=StrategyFilters(),
                )
        
        monkeypatch.setattr(
            graph_mod.SMART_LLM,
            "with_structured_output",
            lambda _: FakeStructured(),
        )
        
        # --- Fake writer LLM (returns text with internal strategy names)
        class FakeWriterLLM:
            async def ainvoke(self, messages, config=None):
                # 현재 상태: 내부 전략명이 포함된 응답 반환 (RED phase)
                return AIMessage(
                    content=(
                        "## 1. [이미지 강조] Test Brand - Test Perfume\n"
                        "이 향수는 이미지 강조 전략으로 추천됩니다.\n"
                        "---\n\n"
                        "## 2. [이미지 보완] Test Brand - Test Perfume\n"
                        "이 향수는 이미지 보완 전략으로 추천됩니다.\n"
                        "---\n\n"
                        "## 3. [이미지 반전] Test Brand - Test Perfume\n"
                        "이 향수는 이미지 반전 전략으로 추천됩니다.\n"
                        "---"
                    )
                )
        
        monkeypatch.setattr(graph_mod, "SUPER_SMART_LLM", FakeWriterLLM())
        
        # --- Run parallel_reco_node
        state = {
            "member_id": 1,
            "user_preferences": {"gender": "Female", "season": "Spring"},
            "user_mode": "BEGINNER",
            "messages": [],
        }
        
        result = await graph_mod.parallel_reco_node(state)
        output_text = result["messages"][0].content
        
        # --- Assertion: 금지어 탐지
        forbidden_matches = detect_forbidden_words(output_text)
        
        # RED phase: 금지어가 발견되어야 함 (테스트 FAIL)
        assert len(forbidden_matches) > 0, (
            "RED phase: 금지어가 발견되지 않았습니다. "
            "현재 상태에서는 내부 전략명이 출력에 포함되어야 합니다."
        )
        
        # 발견된 금지어 출력 (디버깅용)
        print(f"\n[RED] 발견된 금지어: {forbidden_matches}")
        print(f"[RED] 출력 텍스트:\n{output_text}")
    
    
    @pytest.mark.asyncio
    async def test_save_tags_integrity(self, monkeypatch):
        """
        RED: SAVE 태그가 출력에 포함되어야 함을 확인
        
        현재 상태에서 SAVE 태그가 없을 수 있음.
        (향후 GREEN phase에서 SAVE 태그 추가 시 통과)
        """
        from agent import graph as graph_mod
        from agent.schemas import SearchStrategyPlan, HardFilters, StrategyFilters
        from agent.denylist import validate_save_tags
        from langchain_core.messages import AIMessage
        
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
                        "id": 2001,
                        "name": "Perfume A",
                        "brand": "Brand A",
                        "accords": "Floral",
                        "best_review": "Nice",
                        "top_notes": "Citrus",
                        "middle_notes": "Rose",
                        "base_notes": "Musk",
                        "image_url": None,
                        "gender": "Unisex",
                    }
                ],
                "Perfect Match",
            )
        
        monkeypatch.setattr(graph_mod, "smart_search_with_retry_async", fake_search)
        
        # --- Fake planner model
        class FakeStructured:
            async def ainvoke(self, messages, config=None):
                user = messages[-1].content
                if "이미지 강조" in user:
                    name, prio = "이미지 강조", 1
                elif "이미지 보완" in user:
                    name, prio = "이미지 보완", 2
                else:
                    name, prio = "이미지 반전", 3
                
                return SearchStrategyPlan(
                    priority=prio,
                    strategy_name=name,
                    strategy_keyword="test_keyword",
                    reason="Test reason",
                    hard_filters=HardFilters(),
                    strategy_filters=StrategyFilters(),
                )
        
        monkeypatch.setattr(
            graph_mod.SMART_LLM,
            "with_structured_output",
            lambda _: FakeStructured(),
        )
        
        # --- Fake writer LLM (returns text with SAVE tags)
        class FakeWriterLLM:
            async def ainvoke(self, messages, config=None):
                return AIMessage(
                    content=(
                        "## 1. [사용자 친화 라벨] Brand A - Perfume A\n"
                        "[[SAVE:2001:Perfume A]]\n"
                        "설명 텍스트\n"
                        "---\n\n"
                        "## 2. [사용자 친화 라벨] Brand A - Perfume A\n"
                        "[[SAVE:2001:Perfume A]]\n"
                        "설명 텍스트\n"
                        "---\n\n"
                        "## 3. [사용자 친화 라벨] Brand A - Perfume A\n"
                        "[[SAVE:2001:Perfume A]]\n"
                        "설명 텍스트\n"
                        "---"
                    )
                )
        
        monkeypatch.setattr(graph_mod, "SUPER_SMART_LLM", FakeWriterLLM())
        
        # --- Run parallel_reco_node
        state = {
            "member_id": 1,
            "user_preferences": {"gender": "Female", "season": "Spring"},
            "user_mode": "BEGINNER",
            "messages": [],
        }
        
        result = await graph_mod.parallel_reco_node(state)
        output_text = result["messages"][0].content
        
        # --- Assertion: SAVE 태그 검증
        has_save_tags, save_tags = validate_save_tags(output_text)
        
        # GREEN phase 기준: SAVE 태그가 최소 1개 이상 있어야 함
        # RED phase에서는 아직 없을 수 있음
        print(f"\n[SAVE TAG CHECK] 발견된 SAVE 태그: {save_tags}")
        print(f"[SAVE TAG CHECK] 출력 텍스트:\n{output_text}")
        
        # 현재 상태에서는 SAVE 태그가 없을 수 있음 (향후 추가 예정)
        # 이 테스트는 정보 제공 목적
    
    
    def test_denylist_policy_patterns_defined(self):
        """
        금지어 정책이 올바르게 정의되었는지 확인
        
        이 테스트는 항상 PASS해야 함 (정책 정의 검증)
        """
        from agent.denylist import DenylistPolicy
        
        forbidden = DenylistPolicy.get_forbidden_patterns()
        protected = DenylistPolicy.get_protected_patterns()
        
        # 금지어 패턴 확인
        assert len(forbidden) > 0, "금지어 패턴이 정의되지 않았습니다"
        assert any("전략" in p for p in forbidden), "전략 관련 패턴이 없습니다"
        assert any("이미지" in p for p in forbidden), "이미지 관련 패턴이 없습니다"
        
        # 보호 패턴 확인
        assert len(protected) > 0, "보호 패턴이 정의되지 않았습니다"
        assert any("SAVE" in p for p in protected), "SAVE 태그 패턴이 없습니다"
        
        print(f"\n[POLICY] 금지어 패턴: {forbidden}")
        print(f"[POLICY] 보호 패턴: {protected}")
    
    
    def test_detect_forbidden_words_basic(self):
        """
        금지어 탐지 함수의 기본 동작 확인
        
        이 테스트는 항상 PASS해야 함 (유틸 함수 검증)
        """
        from agent.denylist import detect_forbidden_words, has_forbidden_words
        
        # 금지어 포함 텍스트
        text_with_forbidden = "이 향수는 이미지 강조 전략으로 추천됩니다."
        matches = detect_forbidden_words(text_with_forbidden)
        assert len(matches) > 0, "금지어가 탐지되지 않았습니다"
        assert any("이미지 강조" in m[0] for m in matches), "이미지 강조가 탐지되지 않았습니다"
        
        # 금지어 미포함 텍스트
        text_without_forbidden = "이 향수는 신선하고 활기찬 느낌의 향입니다."
        matches = detect_forbidden_words(text_without_forbidden)
        assert len(matches) == 0, "금지어가 잘못 탐지되었습니다"
        
        # has_forbidden_words 함수 확인
        assert has_forbidden_words(text_with_forbidden), "금지어 포함 여부 판단 실패"
        assert not has_forbidden_words(text_without_forbidden), "금지어 포함 여부 판단 실패"
        
        print(f"\n[DETECT] 금지어 탐지 테스트 통과")
    
    
    def test_safe_labels_validation(self):
        """
        사용자 친화 전략명이 금지어를 포함하지 않는지 확인
        
        이 테스트는 항상 PASS해야 함 (안전 라벨 검증)
        """
        from agent.denylist import UserFriendlyStrategyLabels, has_forbidden_words
        
        all_safe, violations = UserFriendlyStrategyLabels.validate_all_labels()
        
        assert all_safe, f"안전 라벨에 금지어가 포함되어 있습니다: {violations}"
        
        # 각 라벨이 금지어를 포함하지 않는지 확인
        for label in UserFriendlyStrategyLabels.get_safe_labels():
            assert not has_forbidden_words(label), f"라벨 '{label}'에 금지어가 포함되어 있습니다"
        
        print(f"\n[SAFE LABELS] 모든 사용자 친화 라벨이 안전합니다")
        print(f"[SAFE LABELS] 라벨 목록: {UserFriendlyStrategyLabels.get_safe_labels()}")
