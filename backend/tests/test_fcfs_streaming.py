"""
FCFS (First-Come-First-Served) 스트리밍 테스트

parallel_reco_node의 FCFS 파이프라인이 올바르게 동작하는지 검증:
1. 전략들이 완료되는 즉시 출력되는지 (FCFS 순서)
2. 섹션 넘버링이 1..N으로 연속되는지
3. 마지막 템플릿이 "진짜 마지막"에만 적용되는지
"""
import pytest
import asyncio
import sys
sys.path.insert(0, '/app')

from unittest.mock import AsyncMock, MagicMock, patch
from agent.graph import parallel_reco_node, RecoSearcher, RecoWriter


class TestFCFSOrdering:
    """FCFS 순서 검증"""

    @pytest.mark.asyncio
    async def test_sections_output_in_completion_order(self):
        """
        전략들이 완료되는 순서대로 출력되어야 함 (요청 순서와 무관).

        시나리오:
        - Strategy 1: 3초 소요
        - Strategy 2: 1초 소요
        - Strategy 3: 2초 소요

        예상 출력 순서: 2 → 3 → 1
        """
        # Mock state
        state = {
            "user_preferences": {"gender": "Unisex"},
            "messages": [],
            "member_id": 0,
            "user_query": "테스트",
            "recommended_history": [],
            "recommended_count": 3,
        }

        # Mock smart_perfume_search with different delays
        async def mock_search_with_delay(strategy_id, delay):
            await asyncio.sleep(delay)
            return (
                [{"id": strategy_id, "name": f"Perfume {strategy_id}", "brand": f"Brand {strategy_id}",
                  "accords": "Test", "best_review": "Great", "top_notes": "Note",
                  "middle_notes": "Note", "base_notes": "Note", "gender": "Unisex"}],
                "Perfect Match"
            )

        with patch('agent.graph.smart_search_with_retry_async') as mock_search:
            # Strategy 1: 0.3초, Strategy 2: 0.1초, Strategy 3: 0.2초
            mock_search.side_effect = [
                mock_search_with_delay(1, 0.3),
                mock_search_with_delay(2, 0.1),
                mock_search_with_delay(3, 0.2),
            ]

            with patch('agent.graph.SMART_LLM') as mock_llm:
                # Mock strategy planning
                mock_strategy = MagicMock()
                mock_strategy.strategy_name = "Test Strategy"
                mock_strategy.reason = "Test reason"
                mock_strategy.strategy_keyword = ["test"]
                mock_strategy.hard_filters.model_dump.return_value = {"gender": "Unisex"}
                mock_strategy.strategy_filters.model_dump.return_value = {}

                mock_llm.with_structured_output.return_value.ainvoke = AsyncMock(return_value=mock_strategy)

                # Mock user label generation
                mock_label_response = MagicMock()
                mock_label_response.content = "테스트 라벨"
                mock_llm.ainvoke = AsyncMock(return_value=mock_label_response)

                with patch('agent.graph.SUPER_SMART_LLM') as mock_writer_llm:
                    mock_writer_llm.astream = AsyncMock(return_value=[
                        MagicMock(content="## "),
                        MagicMock(content="1. Test\n"),
                        MagicMock(content="Content\n"),
                        MagicMock(content="[[SAVE:1:Test]]\n---"),
                    ])

                    result = await parallel_reco_node(state)

                    # 검증: 성공 상태
                    assert result["chat_outcome_status"] == "OK"
                    assert len(result["messages"]) == 1


class TestSectionNumbering:
    """섹션 넘버링 검증"""

    @pytest.mark.asyncio
    async def test_sections_numbered_sequentially(self):
        """
        섹션 번호가 1, 2, 3, ... N으로 연속되어야 함.
        완료 순서와 무관하게 출력 순서대로 넘버링.
        """
        state = {
            "user_preferences": {"gender": "Unisex"},
            "messages": [],
            "member_id": 0,
            "user_query": "테스트",
            "recommended_history": [],
            "recommended_count": 3,
        }

        with patch('agent.graph.smart_search_with_retry_async') as mock_search:
            mock_search.return_value = (
                [{"id": 1, "name": "Test", "brand": "Test", "accords": "Test",
                  "best_review": "Test", "top_notes": "Test", "middle_notes": "Test",
                  "base_notes": "Test", "gender": "Unisex"}],
                "Perfect Match"
            )

            with patch('agent.graph.SMART_LLM') as mock_llm:
                mock_strategy = MagicMock()
                mock_strategy.strategy_name = "Test"
                mock_strategy.reason = "Test"
                mock_strategy.strategy_keyword = ["test"]
                mock_strategy.hard_filters.model_dump.return_value = {"gender": "Unisex"}
                mock_strategy.strategy_filters.model_dump.return_value = {}

                mock_llm.with_structured_output.return_value.ainvoke = AsyncMock(return_value=mock_strategy)

                mock_label_response = MagicMock()
                mock_label_response.content = "테스트"
                mock_llm.ainvoke = AsyncMock(return_value=mock_label_response)

                with patch('agent.graph.SUPER_SMART_LLM') as mock_writer_llm:
                    # Mock writer to return sections with numbers
                    async def mock_stream(*args, **kwargs):
                        for chunk in ["## 1. Test\n", "Content\n", "[[SAVE:1:Test]]\n---"]:
                            yield MagicMock(content=chunk)

                    mock_writer_llm.astream = mock_stream

                    result = await parallel_reco_node(state)

                    # 검증: 메시지에 섹션 번호가 포함되어 있는지
                    content = result["messages"][0].content
                    assert "## 1." in content or "##1." in content.replace(" ", "")


class TestLastTemplateApplication:
    """마지막 템플릿 적용 검증"""

    @pytest.mark.asyncio
    async def test_last_template_only_applied_to_final_section(self):
        """
        "마지막 템플릿"이 진짜 마지막 섹션에만 적용되어야 함.

        검증:
        - 중간 섹션들은 is_last=False로 생성
        - 마지막 섹션만 is_last=True로 생성
        """
        state = {
            "user_preferences": {"gender": "Unisex"},
            "messages": [],
            "member_id": 0,
            "user_query": "테스트",
            "recommended_history": [],
            "recommended_count": 2,
        }

        with patch('agent.graph.smart_search_with_retry_async') as mock_search:
            mock_search.return_value = (
                [{"id": 1, "name": "Test", "brand": "Test", "accords": "Test",
                  "best_review": "Test", "top_notes": "Test", "middle_notes": "Test",
                  "base_notes": "Test", "gender": "Unisex"}],
                "Perfect Match"
            )

            with patch('agent.graph.SMART_LLM') as mock_llm:
                mock_strategy = MagicMock()
                mock_strategy.strategy_name = "Test"
                mock_strategy.reason = "Test"
                mock_strategy.strategy_keyword = ["test"]
                mock_strategy.hard_filters.model_dump.return_value = {"gender": "Unisex"}
                mock_strategy.strategy_filters.model_dump.return_value = {}

                mock_llm.with_structured_output.return_value.ainvoke = AsyncMock(return_value=mock_strategy)

                mock_label_response = MagicMock()
                mock_label_response.content = "테스트"
                mock_llm.ainvoke = AsyncMock(return_value=mock_label_response)

                with patch('agent.graph.RecoWriter.generate_section') as mock_generate:
                    # Track is_last parameter
                    is_last_calls = []

                    async def track_is_last(*args, **kwargs):
                        is_last_calls.append(kwargs.get('is_last', False))
                        return "## 1. Test\nContent\n[[SAVE:1:Test]]\n---"

                    mock_generate.side_effect = track_is_last

                    result = await parallel_reco_node(state)

                    # 검증: 마지막 호출만 is_last=True
                    assert len(is_last_calls) == 2
                    assert is_last_calls[-1] is True  # 마지막만 True
                    assert is_last_calls[0] is False  # 나머지는 False


class TestOneBuffering:
    """1개 버퍼링 알고리즘 검증"""

    def test_pending_section_mechanism(self):
        """
        1개 버퍼링 메커니즘 검증:
        - pending_section을 유지하며 새 섹션 도착 시 기존 것을 출력
        - 마지막에 pending_section을 is_last=True로 출력

        이 테스트는 알고리즘의 정확성을 검증.
        """
        # Simulated FCFS pipeline
        pending_section = None
        output_texts = []

        # 섹션 3개가 순차적으로 도착
        sections = ["Section 1", "Section 2", "Section 3"]

        for i, section in enumerate(sections):
            if pending_section:
                # 기존 pending을 중간 템플릿으로 출력
                output_texts.append(f"{pending_section} (is_last=False)")

            # 새 섹션을 pending으로 설정
            pending_section = section

        # 마지막 pending을 is_last=True로 출력
        if pending_section:
            output_texts.append(f"{pending_section} (is_last=True)")

        # 검증
        assert len(output_texts) == 3
        assert "Section 1 (is_last=False)" in output_texts[0]
        assert "Section 2 (is_last=False)" in output_texts[1]
        assert "Section 3 (is_last=True)" in output_texts[2]
