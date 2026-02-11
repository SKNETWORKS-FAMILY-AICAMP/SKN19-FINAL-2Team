import pytest
import asyncio
import json
from unittest.mock import MagicMock, AsyncMock, patch

# Note: backend.agent.database is mocked in conftest.py

# Import graph after mocking (handled by conftest or simple import here if conftest works)
from backend.agent.graph import parallel_reco_node
from backend.agent.schemas import AgentState, SearchStrategyPlan

# Mock Chunk for astream
class MockChunk:
    def __init__(self, content):
        self.content = content

@pytest.mark.asyncio
async def test_parallel_reco_contiguous_numbering():
    """
    Test parallel_reco_node to ensure:
    1. It runs 3 strategies.
    2. If Strategy 2 fails (returns None), the output is contiguous (1, 2) instead of (1, 3).
    """
    
    # Mock State
    state = {
        "member_id": 123,
        "user_preferences": {"gender": "Unisex"},
        "messages": [],
        "recommended_history": []
    }
    
    # We need to mock the LLMs and Tools used INSIDE parallel_reco_node.
    # Since they are imported globally in graph.py, we patch them there.
    
    with patch("backend.agent.graph.SMART_LLM") as mock_smart, \
         patch("backend.agent.graph.SUPER_SMART_LLM") as mock_super, \
         patch("backend.agent.graph.advanced_perfume_search_tool") as mock_search, \
         patch("backend.agent.graph.get_personalization_summary", return_value={}), \
         patch("backend.agent.graph.save_recommendation_log"):
             
        # 1. Mock SMART_LLM (Planner & Labeler)
        # It's used for:
        # a) plan_llm.ainvoke (SearchStrategyPlan) -> We mock .with_structured_output().ainvoke
        # b) generate_user_label -> .ainvoke
        
        # Mock SearchStrategyPlan result
        # We must satisfy the Pydantic schema for SearchStrategyPlan
        mock_plan = SearchStrategyPlan(
            priority=1,
            strategy_name="TEST_STRAT",
            strategy_keyword=["k1"],
            reason="Test Reason",
            hard_filters={"gender": "Unisex"}, # Pydantic accepts dict for nested models
            strategy_filters={}
        )
        
        # Setup SMART_LLM for planning
        mock_smart.with_structured_output.return_value.ainvoke = AsyncMock(return_value=mock_plan)
        
        # Setup SMART_LLM for labeling (ainvoke returns AIMessage)
        mock_smart.ainvoke = AsyncMock(return_value=MagicMock(content="User Label"))
        
        # 2. Mock Search Tool (advanced_perfume_search_tool)
        # We need it to return results for Strat 1 & 3, but NONE for Strat 2.
        # But prepare_strategy calls it. 
        # The prompt to prepare_strategy includes "우선순위: {priority}".
        # However, smart_search_with_retry_async calls the tool.
        # It's hard to distinguish calls by priority inside the mock without checking arguments.
        
        # Let's mock `smart_search_with_retry_async` instead? 
        # It is defined in graph.py, so we can patch `backend.agent.graph.smart_search_with_retry_async`.
        
        async def mock_search_impl(h, s, exclude_ids, query_text):
            # Check the query_text or some side effect to decide success/fail.
            # But the query_text comes from the plan.reason.
            # We can make the plan reason different for each strategy?
            # But `prepare_strategy` calls LLM to get the plan.
            # We can mock the LLM to return different reasons based on the prompt priority?
            
            # Complex. Let's rely on the side effect of `prepare_strategy`.
            # prepare_strategy calls `smart_search_with_retry_async`.
            # If we mock `smart_search_with_retry_async` to use a counter?
            pass

    # EASIER APPROACH:
    # Patch `backend.agent.graph.prepare_strategy`?
    # No, it's an inner function. We can't patch it.
    
    # We must control the external dependencies.
    # Let's patch `backend.agent.graph.smart_search_with_retry_async`.
    
    call_count = 0
    async def side_effect_search(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        # Call 1 -> Strat 1 -> Success
        # Call 2 -> Strat 2 -> Fail (return [], "No Results")
        # Call 3 -> Strat 3 -> Success
        
        # Note: They run in parallel, so order isn't guaranteed!
        # But `prep_tasks` creates them in order 1, 2, 3.
        # However, `asyncio.create_task` starts them immediately.
        # To be safe, we can check the arguments, but args are generic filters.
        
        # Let's assume order for now or make all return success but filter later?
        # No, we want to test "None" return from prepare_strategy.
        # prepare_strategy returns None if search fails (Exception) or returns empty?
        # graph.py line 565: except Exception -> return None.
        # smart_search returns [], "No Results".
        # line 570 loops over candidates. If empty, loop doesn't run, selected_perfume is None.
        # line 582: if not selected_perfume: return None.
        
        # So returning empty list [] makes prepare_strategy return None.
        
        # How to map to Strategy 2?
        # The prompts passed to LLM contain "우선순위: X".
        # But we mocked the LLM to return a fixed plan.
        # So `smart_search` receives the SAME filters for all 3.
        
        # We can make the search fail randomly? No.
        # We can use a lock or counter, hoping the tasks start in order?
        # Since we use `create_task` sequentially in the list, they likely start in order.
        
        if call_count == 2:
            return [], "No Results"
        
        return [{"id": 100+call_count, "name": f"P{call_count}", "brand": "B", "accords": "A"}], "Perfect Match"

    with patch("backend.agent.graph.SMART_LLM") as mock_smart, \
         patch("backend.agent.graph.SUPER_SMART_LLM") as mock_super, \
         patch("backend.agent.graph.smart_search_with_retry_async", side_effect=side_effect_search) as mock_search, \
         patch("backend.agent.graph.get_personalization_summary", return_value={}), \
         patch("backend.agent.graph.save_recommendation_log"):
             
        # Setup mocks
        mock_smart.with_structured_output.return_value.ainvoke = AsyncMock(return_value=SearchStrategyPlan(
            priority=1,
            strategy_name="STRAT", 
            strategy_keyword=["k"], 
            reason="r", 
            hard_filters={"gender": "Unisex"}, 
            strategy_filters={}
        ))
        mock_smart.ainvoke = AsyncMock(return_value=MagicMock(content="Label"))
        
        # Mock SUPER_SMART_LLM.astream for generate_output
        # It needs to return text with "## X."
        async def mock_astream(messages):
            prompt = messages[-1].content
            import re
            match = re.search(r"\[섹션 번호\]: (\d+)", prompt)
            prio = match.group(1) if match else "?"
            yield MockChunk(content=f"## {prio}. Section {prio}")
            
        mock_super.astream = mock_astream
        
        # RUN THE NODE
        result = await parallel_reco_node(state)
        
        # CHECK OUTPUT
        message = result["messages"][0].content
        print(f"Result Message:\n{message}")
        
        # EXPECTATION (Fixed):
        # Strat 1 (Call 1) -> Success -> ## 1.
        # Strat 2 (Call 2) -> Fail -> None
        # Strat 3 (Call 3) -> Success -> ## 2. (Renumbered from 3)
        
        assert "## 1." in message
        assert "## 2." in message, f"Expected contiguous numbering (1, 2), but got gap:\n{message}"
        assert "## 3." not in message, "Should not produce gap (## 3.)"
