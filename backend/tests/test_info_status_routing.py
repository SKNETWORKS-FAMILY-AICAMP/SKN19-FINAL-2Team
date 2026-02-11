# backend/tests/test_info_status_routing.py
"""
Info 그래프의 상태 기반 라우팅 테스트

Wave 2에서 구현한 info_status 분기 로직을 검증합니다.
"""
import pytest
import sys
sys.path.insert(0, '/app')

from agent.graph_info import classify_info_status, info_result_router_node


class TestClassifyInfoStatus:
    """classify_info_status 함수 테스트"""
    
    def test_error_detection(self):
        """ERROR 상태 감지"""
        assert classify_info_status("DB 에러 발생") == "ERROR"
        assert classify_info_status("Error occurred") == "ERROR"
        assert classify_info_status("검색 중 Error") == "ERROR"
    
    def test_no_results_detection(self):
        """NO_RESULTS 상태 감지"""
        assert classify_info_status("{}") == "NO_RESULTS"
        assert classify_info_status("[]") == "NO_RESULTS"
        assert classify_info_status("") == "NO_RESULTS"
        assert classify_info_status("검색 실패") == "NO_RESULTS"
        assert classify_info_status("찾을 수 없습니다") == "NO_RESULTS"
        assert classify_info_status("결과가 없습니다") == "NO_RESULTS"
    
    def test_ok_detection(self):
        """OK 상태 감지"""
        assert classify_info_status("정상 데이터") == "OK"
        assert classify_info_status('{"name": "샤넬"}') == "OK"
        assert classify_info_status("향수 정보가 있습니다") == "OK"


class TestInfoResultRouter:
    """info_result_router_node 라우팅 테스트"""
    
    def test_route_to_no_results(self):
        """NO_RESULTS 상태 → info_no_results 노드로 라우팅"""
        state = {"info_status": "NO_RESULTS"}
        result = info_result_router_node(state)
        assert result == "info_no_results"
    
    def test_route_to_error(self):
        """ERROR 상태 → info_error 노드로 라우팅"""
        state = {"info_status": "ERROR"}
        result = info_result_router_node(state)
        assert result == "info_error"
    
    def test_route_to_writer(self):
        """OK 상태 → info_writer 노드로 라우팅"""
        state = {"info_status": "OK"}
        result = info_result_router_node(state)
        assert result == "info_writer"
    
    def test_default_route(self):
        """info_status 없을 때 기본값 OK → info_writer"""
        state = {}
        result = info_result_router_node(state)
        assert result == "info_writer"


class TestInfoGraphCompilation:
    """Info 그래프 컴파일 테스트"""
    
    def test_graph_compiles(self):
        """그래프가 정상적으로 컴파일되는지 확인"""
        from agent.graph_info import info_graph
        assert info_graph is not None
        # Pattern A: router 노드 제거로 노드 수가 변경됨. 대신 핵심 노드 존재를 검증
        assert len(info_graph.nodes) >= 9  # 최소 필수 노드 수

    def test_new_nodes_exist(self):
        """핵심 노드가 그래프에 존재하는지 확인"""
        from agent.graph_info import info_graph
        node_names = list(info_graph.nodes.keys())

        # Pattern A: info_result_router 노드는 제거됨
        # 핵심 노드만 검증
        assert "info_supervisor" in node_names
        assert "perfume_describer" in node_names
        assert "ingredient_specialist" in node_names
        assert "similarity_curator" in node_names
        assert "fallback_handler" in node_names
        assert "info_no_results" in node_names
        assert "info_error" in node_names
        assert "info_writer" in node_names
