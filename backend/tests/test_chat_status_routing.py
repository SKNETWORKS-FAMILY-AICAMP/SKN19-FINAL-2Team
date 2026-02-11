"""
Regression prevention tests for chat agent status routing.

These tests verify the 4 invariants identified in Wave 1 to prevent
regression of the writer_node removal bug (f8df0a54).
"""
import pytest
import sys
sys.path.insert(0, '/app')

from agent.graph import parallel_reco_result_router, app_graph


class TestInvariant1StatusClassification:
    """Invariant 1: All /chat flows must have chat_outcome_status"""
    
    def test_router_function_exists(self):
        """
        parallel_reco_result_router must exist.
        This prevents regression where status routing was removed.
        """
        assert parallel_reco_result_router is not None
        assert callable(parallel_reco_result_router)


class TestInvariant2ErrorNoInternalDetails:
    """Invariant 2: ERROR status must not expose internal details"""
    
    def test_error_status_routes_to_error_handler(self):
        """
        chat_outcome_status=ERROR must route to error handler (not expose internals).
        """
        state = {"chat_outcome_status": "ERROR"}
        result = parallel_reco_result_router(state)
        
        assert result == "parallel_reco_error"
    
    def test_error_with_reason_still_routes_correctly(self):
        """
        Error with reason_detail should still route to safe error handler.
        """
        state = {
            "chat_outcome_status": "ERROR",
            "chat_outcome_reason_detail": "Exception: DB connection failed",
        }
        
        next_node = parallel_reco_result_router(state)
        assert next_node == "parallel_reco_error"


class TestInvariant3NoResultsAlternatives:
    """Invariant 3: NO_RESULTS status must suggest alternatives"""
    
    def test_no_results_status_routing(self):
        """
        chat_outcome_status=NO_RESULTS must route to no_results handler.
        """
        state = {"chat_outcome_status": "NO_RESULTS"}
        result = parallel_reco_result_router(state)
        
        assert result == "parallel_reco_no_results"


class TestInvariant4StatusRoutesToDifferentPaths:
    """Invariant 4: Different statuses must use different prompts/paths"""
    
    def test_ok_routes_to_ok_writer(self):
        """OK status routes to ok_writer"""
        state = {"chat_outcome_status": "OK"}
        assert parallel_reco_result_router(state) == "parallel_reco_ok_writer"
    
    def test_no_results_routes_correctly(self):
        """NO_RESULTS routes to no_results handler"""
        state = {"chat_outcome_status": "NO_RESULTS"}
        assert parallel_reco_result_router(state) == "parallel_reco_no_results"
    
    def test_error_routes_correctly(self):
        """ERROR routes to error handler"""
        state = {"chat_outcome_status": "ERROR"}
        assert parallel_reco_result_router(state) == "parallel_reco_error"
    
    def test_all_statuses_route_to_different_nodes(self):
        """Verify all statuses route to different nodes (no overlap)"""
        ok_node = parallel_reco_result_router({"chat_outcome_status": "OK"})
        no_results_node = parallel_reco_result_router({"chat_outcome_status": "NO_RESULTS"})
        error_node = parallel_reco_result_router({"chat_outcome_status": "ERROR"})
        
        # All should be different
        assert ok_node != no_results_node
        assert no_results_node != error_node
        assert error_node != ok_node


class TestRouterFunction:
    """Test the routing function itself"""

    def test_router_returns_correct_node_names(self):
        """Verify router returns valid node names"""
        valid_nodes = {
            "parallel_reco_ok_writer",
            "parallel_reco_no_results",
            "parallel_reco_error",
        }

        for status in ["OK", "NO_RESULTS", "ERROR"]:
            state = {"chat_outcome_status": status}
            result = parallel_reco_result_router(state)
            assert result in valid_nodes, f"Status {status} routed to invalid node: {result}"

    def test_default_status_routes_to_ok(self):
        """If status is missing, default to OK (safe fallback)"""
        state = {}
        result = parallel_reco_result_router(state)
        assert result == "parallel_reco_ok_writer"

    def test_router_with_extra_state_fields(self):
        """Router should work even with extra state fields"""
        state = {
            "chat_outcome_status": "NO_RESULTS",
            "messages": [],
            "user_query": "test",
            "extra_field": "should be ignored",
        }
        result = parallel_reco_result_router(state)
        assert result == "parallel_reco_no_results"


class TestRecoGraphTopology:
    """Pattern A topology tests - router node should be removed"""

    def test_router_not_in_graph_nodes(self):
        """
        Pattern A: parallel_reco_result_router should NOT be a node.
        It's used as a conditional edge function, not a node.
        """
        node_names = list(app_graph.nodes.keys())
        assert "parallel_reco_result_router" not in node_names

    def test_status_specific_nodes_exist(self):
        """Pattern A: Status-specific handler nodes must exist"""
        node_names = list(app_graph.nodes.keys())

        assert "parallel_reco_ok_writer" in node_names
        assert "parallel_reco_no_results" in node_names
        assert "parallel_reco_error" in node_names

    def test_parallel_reco_node_exists(self):
        """The main parallel_reco node must exist"""
        node_names = list(app_graph.nodes.keys())
        assert "parallel_reco" in node_names
