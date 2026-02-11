import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

# Mock backend.agent.database to avoid DB connections
import sys
if "backend.agent.database" not in sys.modules:
    mock_db = MagicMock()
    mock_db.save_recommendation_log = MagicMock()
    mock_db.fetch_meta_data = MagicMock(return_value={
        "genders": "Male,Female,Unisex",
        "seasons": "Spring,Summer,Fall,Winter",
        "occasions": "Daily,Special",
        "accords": "Citrus,Woody"
    })
    sys.modules["backend.agent.database"] = mock_db

# Mock tools
if "backend.agent.tools" not in sys.modules:
    mock_tools = MagicMock()
    sys.modules["backend.agent.tools"] = mock_tools

from backend.agent.graph import parallel_reco_node
from backend.agent.schemas import AgentState, SearchStrategyPlan, HardFilters, StrategyFilters

@pytest.mark.asyncio
async def test_recommendation_deduplication():
    """
    Verify that perfumes in recommended_history are excluded from search results.
    """
    # 1. Setup State with history
    history_ids = [101, 102]
    state = {
        "member_id": 1,
        "user_preferences": {"target": "Me"},
        "recommended_history": history_ids,
        "messages": [HumanMessage(content="추천해줘")],
        "user_query": "추천해줘"
    }

    # 2. Mock Dependencies
    with patch("backend.agent.graph.get_personalization_summary", return_value={}), \
         patch("backend.agent.graph.SMART_LLM") as mock_smart_llm, \
         patch("backend.agent.graph.smart_search_with_retry_async") as mock_search, \
         patch("backend.agent.graph.save_recommendation_log"):

        # Mock Plan LLM
        mock_plan = SearchStrategyPlan(
            priority=1,
            strategy_name="TestStrat",
            strategy_keyword=["test"],
            reason="Test Reason",
            hard_filters=HardFilters(gender="Unisex"),
            strategy_filters=StrategyFilters()
        )
        mock_smart_llm.with_structured_output.return_value.ainvoke = AsyncMock(return_value=mock_plan)
        mock_smart_llm.ainvoke = AsyncMock(return_value=AIMessage(content="Test Strategy"))

        # Mock SUPER_SMART_LLM
        with patch("backend.agent.graph.SUPER_SMART_LLM") as mock_super_llm:
            # Mock astream to yield content
            async def mock_astream(*args, **kwargs):
                yield AIMessage(content="## 1. Test Output\nResult")
            mock_super_llm.astream = mock_astream
            
            # Mock ainvoke just in case
            mock_super_llm.ainvoke = AsyncMock(return_value=AIMessage(content="Fallback"))

            # Mock search to verify exclude_ids
            async def search_side_effect(h, s, exclude_ids=None, query_text="", rank_mode="DEFAULT"):
                assert 101 in exclude_ids
                assert 102 in exclude_ids
                return ([{"id": 103, "name": "New Perfume", "brand": "Brand A", "accords": "Citrus"}], "Match")
            
            mock_search.side_effect = search_side_effect

            # Run Node
            result = await parallel_reco_node(state)
            
            # Verify updated history
            new_history = result["recommended_history"]
            assert 103 in new_history
            assert 101 in new_history

@pytest.mark.asyncio
async def test_personalization_injection():
    """
    Verify that personalization summary is injected into the Researcher prompt.
    """
    # 1. Setup State
    state = {
        "member_id": 999,
        "user_preferences": {"target": "Me"},
        "messages": [HumanMessage(content="추천해줘")]
    }

    # 2. Mock Personalization
    summary_text = "User likes Citrus and hates Musk."
    disliked_item = {"id": 500, "name": "Bad Perfume"}
    
    mock_personalization_data = {
        "summary_text": summary_text,
        "disliked_perfumes": [disliked_item]
    }

    with patch("backend.agent.graph.get_personalization_summary", return_value=mock_personalization_data) as mock_get_pers, \
         patch("backend.agent.graph.SMART_LLM") as mock_smart_llm, \
         patch("backend.agent.graph.smart_search_with_retry_async") as mock_search, \
         patch("backend.agent.graph.SUPER_SMART_LLM") as mock_super_llm, \
         patch("backend.agent.graph.save_recommendation_log"):

        # Mock Plan LLM
        mock_plan = SearchStrategyPlan(
            priority=1,
            strategy_name="TestStrat",
            strategy_keyword=["test"],
            reason="Test Reason",
            hard_filters=HardFilters(gender="Unisex"),
            strategy_filters=StrategyFilters()
        )
        mock_smart_llm.with_structured_output.return_value.ainvoke = AsyncMock(return_value=mock_plan)
        mock_smart_llm.ainvoke = AsyncMock(return_value=AIMessage(content="Label"))
        
        # Mock Search (Empty to hit fallback fast)
        mock_search.return_value = ([], "No Results") 

        # Mock Fallback LLM
        mock_super_llm.ainvoke = AsyncMock(return_value=AIMessage(content="Fallback Message"))

        # Run Node
        await parallel_reco_node(state)

        # 3. Verify get_personalization_summary called
        mock_get_pers.assert_called_with(999)

        # 4. Verify Disliked ID in exclude_ids
        call_args = mock_search.call_args
        assert call_args is not None
        _, kwargs = call_args
        exclude_ids = kwargs.get("exclude_ids", [])
        assert 500 in exclude_ids, f"Disliked perfume 500 not in exclude_ids: {exclude_ids}"

        # 5. Verify Summary Text in Prompt
        plan_call_args = mock_smart_llm.with_structured_output.return_value.ainvoke.call_args
        assert plan_call_args is not None
        messages, _ = plan_call_args
        system_msg = messages[0][0] 
        assert isinstance(system_msg, SystemMessage)
        assert summary_text in system_msg.content, "Personalization summary not found in Researcher prompt"
