"""
도구 반환값 계약 테스트

모든 Info 도구들이 표준화된 반환값 계약을 따르는지 검증:
1. 성공 시: dict 또는 유효한 데이터 반환
2. 결과 없음 시: 빈 리스트 [] 반환
3. 기술적 에러 시: Exception raise
"""
import pytest
import sys
sys.path.insert(0, '/app')

from unittest.mock import patch, MagicMock
from agent.tools import (
    lookup_perfume_info_tool,
    lookup_perfume_by_id_tool,
    lookup_note_info_tool,
    lookup_accord_info_tool,
    lookup_similar_perfumes_tool,
)
from agent.utils import classify_info_status


class TestPerfumeInfoToolContract:
    """lookup_perfume_info_tool 반환값 계약"""

    def test_returns_dict_on_success(self):
        """성공 시 dict 반환"""
        with patch('agent.tools.get_db_connection') as mock_conn:
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = {
                "perfume_id": 1,
                "perfume_name": "Test",
                "perfume_brand": "Test Brand",
                "img_link": "http://test.com",
                "gender": "Unisex",
                "top_notes": "Rose",
                "middle_notes": "Jasmine",
                "base_notes": "Musk",
                "accords": "Floral",
                "seasons": "Spring",
                "occasions": "Daily",
            }
            mock_conn.return_value.cursor.return_value = mock_cursor

            with patch('agent.tools.NORMALIZER_LLM') as mock_llm:
                mock_response = MagicMock()
                mock_response.content = '{"brand": "Test Brand", "name": "Test"}'
                mock_llm.invoke.return_value = mock_response

                result = lookup_perfume_info_tool.invoke("Test Perfume")

                # 검증: dict 반환
                assert isinstance(result, dict)
                assert result["perfume_id"] == 1
                assert result["perfume_name"] == "Test"

    def test_returns_empty_list_on_no_results(self):
        """결과 없음 시 빈 리스트 [] 반환"""
        with patch('agent.tools.get_db_connection') as mock_conn:
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = None  # No results

            mock_conn.return_value.cursor.return_value = mock_cursor

            with patch('agent.tools.NORMALIZER_LLM') as mock_llm:
                mock_response = MagicMock()
                mock_response.content = '{"brand": "Unknown", "name": "Unknown"}'
                mock_llm.invoke.return_value = mock_response

                result = lookup_perfume_info_tool.invoke("NonExistent Perfume")

                # 검증: 빈 리스트 반환
                assert isinstance(result, list)
                assert len(result) == 0

    def test_raises_exception_on_db_error(self):
        """DB 에러 시 Exception raise"""
        with patch('agent.tools.get_db_connection') as mock_conn:
            mock_cursor = MagicMock()
            mock_cursor.execute.side_effect = Exception("DB Connection Error")

            mock_conn.return_value.cursor.return_value = mock_cursor

            with patch('agent.tools.NORMALIZER_LLM') as mock_llm:
                mock_response = MagicMock()
                mock_response.content = '{"brand": "Test", "name": "Test"}'
                mock_llm.invoke.return_value = mock_response

                # 검증: Exception raise
                with pytest.raises(Exception, match="DB 에러"):
                    lookup_perfume_info_tool.invoke("Test")


class TestNoteInfoToolContract:
    """lookup_note_info_tool 반환값 계약"""

    def test_returns_dict_on_success(self):
        """성공 시 dict 반환"""
        with patch('agent.tools.get_db_connection') as mock_conn:
            mock_cursor = MagicMock()
            # Mock successful query results
            mock_cursor.fetchall.side_effect = [
                [{"perfume_brand": "Brand1", "perfume_name": "Perfume1"}],  # First note
            ]
            mock_cursor.fetchone.return_value = {"description": "Test description"}

            mock_conn.return_value.cursor.return_value = mock_cursor

            with patch('agent.tools.NORMALIZER_LLM') as mock_llm:
                mock_response = MagicMock()
                mock_response.content = '["Rose"]'
                mock_llm.invoke.return_value = mock_response

                with patch('agent.tools._expression_loader') as mock_loader:
                    mock_loader.get_note_desc.return_value = "감각적 묘사"

                    result = lookup_note_info_tool.invoke(["Rose"])

                    # 검증: dict 반환
                    assert isinstance(result, dict)
                    assert "Rose" in result

    def test_returns_empty_list_on_no_results(self):
        """결과 없음 시 빈 리스트 [] 반환"""
        with patch('agent.tools.get_db_connection') as mock_conn:
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = []  # No perfumes found

            mock_conn.return_value.cursor.return_value = mock_cursor

            with patch('agent.tools.NORMALIZER_LLM') as mock_llm:
                mock_response = MagicMock()
                mock_response.content = '["UnknownNote"]'
                mock_llm.invoke.return_value = mock_response

                result = lookup_note_info_tool.invoke(["UnknownNote"])

                # 검증: 빈 리스트 반환
                assert isinstance(result, list)
                assert len(result) == 0


class TestAccordInfoToolContract:
    """lookup_accord_info_tool 반환값 계약"""

    def test_returns_dict_on_success(self):
        """성공 시 dict 반환"""
        with patch('agent.tools.get_db_connection') as mock_conn:
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = [
                {"perfume_brand": "Brand1", "perfume_name": "Perfume1"}
            ]

            mock_conn.return_value.cursor.return_value = mock_cursor

            with patch('agent.tools.NORMALIZER_LLM') as mock_llm:
                mock_response = MagicMock()
                mock_response.content = '["Floral"]'
                mock_llm.invoke.return_value = mock_response

                with patch('agent.tools._expression_loader') as mock_loader:
                    mock_loader.get_accord_desc.return_value = "꽃향기"

                    result = lookup_accord_info_tool.invoke(["Floral"])

                    # 검증: dict 반환
                    assert isinstance(result, dict)
                    assert "Floral" in result

    def test_returns_empty_list_on_no_results(self):
        """결과 없음 시 빈 리스트 [] 반환"""
        with patch('agent.tools.get_db_connection') as mock_conn:
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = []

            mock_conn.return_value.cursor.return_value = mock_cursor

            with patch('agent.tools.NORMALIZER_LLM') as mock_llm:
                mock_response = MagicMock()
                mock_response.content = '["UnknownAccord"]'
                mock_llm.invoke.return_value = mock_response

                result = lookup_accord_info_tool.invoke(["UnknownAccord"])

                # 검증: 빈 리스트 반환
                assert isinstance(result, list)
                assert len(result) == 0


class TestSimilarPerfumesToolContract:
    """lookup_similar_perfumes_tool 반환값 계약"""

    def test_returns_dict_on_success(self):
        """성공 시 dict 반환 (target_perfume + similar_list)"""
        with patch('agent.tools.get_db_connection') as mock_conn:
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = [
                {
                    "perfume_id": 2,
                    "perfume_brand": "Similar Brand",
                    "perfume_name": "Similar Perfume",
                    "img_link": "http://test.com",
                    "score": 10,
                }
            ]

            mock_conn.return_value.cursor.return_value = mock_cursor

            with patch('agent.tools.NORMALIZER_LLM') as mock_llm:
                mock_response = MagicMock()
                mock_response.content = '{"brand": "Test Brand", "name": "Test Perfume"}'
                mock_llm.invoke.return_value = mock_response

                result = lookup_similar_perfumes_tool.invoke("Test Perfume")

                # 검증: dict 반환
                assert isinstance(result, dict)
                assert "target_perfume" in result
                assert "similar_list" in result
                assert isinstance(result["similar_list"], list)

    def test_returns_empty_list_on_no_results(self):
        """결과 없음 시 빈 리스트 [] 반환"""
        with patch('agent.tools.get_db_connection') as mock_conn:
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = []  # No similar perfumes

            mock_conn.return_value.cursor.return_value = mock_cursor

            with patch('agent.tools.NORMALIZER_LLM') as mock_llm:
                mock_response = MagicMock()
                mock_response.content = '{"brand": "Test", "name": "Test"}'
                mock_llm.invoke.return_value = mock_response

                result = lookup_similar_perfumes_tool.invoke("Test")

                # 검증: 빈 리스트 반환
                assert isinstance(result, list)
                assert len(result) == 0


class TestClassifyInfoStatus:
    """classify_info_status 함수 객체 기반 검증"""

    def test_list_empty_returns_no_results(self):
        """빈 리스트 → NO_RESULTS"""
        result = []
        status = classify_info_status(result)
        assert status == 'NO_RESULTS'

    def test_list_with_data_returns_ok(self):
        """데이터가 있는 리스트 → OK"""
        result = [{"id": 1, "name": "Test"}]
        status = classify_info_status(result)
        assert status == 'OK'

    def test_dict_empty_returns_no_results(self):
        """빈 딕셔너리 → NO_RESULTS"""
        result = {}
        status = classify_info_status(result)
        assert status == 'NO_RESULTS'

    def test_dict_with_data_returns_ok(self):
        """데이터가 있는 딕셔너리 → OK"""
        result = {"perfume_id": 1, "name": "Test"}
        status = classify_info_status(result)
        assert status == 'OK'

    def test_string_empty_returns_no_results(self):
        """빈 문자열 → NO_RESULTS (하위 호환)"""
        result = ""
        status = classify_info_status(result)
        assert status == 'NO_RESULTS'

    def test_string_with_error_keyword_returns_error(self):
        """에러 키워드 포함 문자열 → ERROR (하위 호환)"""
        result = "DB 에러: Connection failed"
        status = classify_info_status(result)
        assert status == 'ERROR'

    def test_string_with_data_returns_ok(self):
        """데이터가 있는 문자열 → OK (하위 호환)"""
        result = '{"perfume_id": 1, "name": "Test"}'
        status = classify_info_status(result)
        assert status == 'OK'

    def test_none_returns_no_results(self):
        """None → NO_RESULTS"""
        result = None
        status = classify_info_status(result)
        assert status == 'NO_RESULTS'


class TestToolReturnTypeConsistency:
    """모든 도구의 반환 타입 일관성 검증"""

    def test_all_tools_return_dict_or_list(self):
        """
        모든 도구가 dict 또는 list를 반환하는지 검증.
        Exception은 raise되어야 함.
        """
        # 이 테스트는 타입 힌트를 확인하여 계약을 보장
        from inspect import signature

        tools = [
            lookup_perfume_info_tool,
            lookup_perfume_by_id_tool,
            lookup_note_info_tool,
            lookup_accord_info_tool,
            lookup_similar_perfumes_tool,
        ]

        for tool in tools:
            sig = signature(tool.func)
            return_annotation = sig.return_annotation

            # 검증: 반환 타입이 Dict | List 형태여야 함
            assert "Dict" in str(return_annotation) or "List" in str(return_annotation), \
                f"{tool.name} should return Dict or List, got {return_annotation}"
