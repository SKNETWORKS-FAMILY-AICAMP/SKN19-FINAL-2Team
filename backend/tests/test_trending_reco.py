import pytest
import asyncio
import sys
from unittest.mock import MagicMock, patch, AsyncMock

# Remove the globally mocked module from conftest so we can re-import the real one
if "backend.agent.database" in sys.modules:
    del sys.modules["backend.agent.database"]

# We need to patch the connection pool creation inside database.py BEFORE import
# because it runs at module level.
with patch("psycopg2.pool.ThreadedConnectionPool") as mock_pool_cls:
    from backend.agent.database import rerank_perfumes_async

@pytest.mark.asyncio
async def test_rerank_perfumes_popular():
    """
    Test that rerank_perfumes_async sorts by popularity (vote count) 
    when rank_mode='POPULAR'.
    """
    
    # Mock candidates
    candidates = [
        {"id": 1, "name": "Perfume A"},
        {"id": 2, "name": "Perfume B"},
        {"id": 3, "name": "Perfume C"},
    ]
    
    # Mock DB connection and cursor
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    
    # Mock fetchall result for vote counts
    # Assume the query returns:
    # ID 1 -> 10 votes
    # ID 2 -> 50 votes (Most popular)
    # ID 3 -> 5 votes (Least popular)
    mock_fetchall_result = [
        {"perfume_id": 1, "total_vote": 10},
        {"perfume_id": 2, "total_vote": 50},
        {"perfume_id": 3, "total_vote": 5},
    ]
    mock_cur.fetchall.return_value = mock_fetchall_result
    
    mock_conn.cursor.return_value = mock_cur
    
    # Patch get_db_connection inside the module
    # Note: Since we re-imported, we patch it on the imported module object
    # But we imported function directly. We can patch 'backend.agent.database.get_db_connection'
    
    with patch("backend.agent.database.get_db_connection", return_value=mock_conn):
        # Call the function
        result = await rerank_perfumes_async(candidates, query_text="dummy", top_k=3, rank_mode="POPULAR")
        
        # Verify the order: B (50), A (10), C (5)
        assert result[0]["id"] == 2
        assert result[1]["id"] == 1
        assert result[2]["id"] == 3
        
        # Verify review_score/vote was attached
        assert result[0]["review_score"] == 50
        assert "인기도(Vote): 50" in result[0]["best_review"]

@pytest.mark.asyncio
async def test_rerank_perfumes_default_fallback():
    """
    Test that it falls back to semantic search (or mock thereof)
    when rank_mode is DEFAULT.
    """
    
    candidates = [{"id": 1, "name": "A"}]
    
    # We need to mock the async_client and get_embedding_async because default path uses them
    with patch("backend.agent.database.async_client") as mock_client, \
         patch("backend.agent.database.get_embedding_async", return_value=[0.1, 0.2]) as mock_embed, \
         patch("backend.agent.database.get_db_connection") as mock_conn:
             
        # Mock translation response
        mock_completion = MagicMock()
        mock_completion.choices[0].message.content = "translated query"
        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)
        
        # Mock DB for vector search
        mock_cur = MagicMock()
        # Returns score, best_review
        mock_cur.fetchall.return_value = [{"perfume_id": 1, "similarity_score": 0.9, "best_review": "Good"}]
        mock_conn.return_value.cursor.return_value = mock_cur
        
        result = await rerank_perfumes_async(candidates, query_text="q", rank_mode="DEFAULT")
        
        assert len(result) == 1
        # It should have used semantic scoring (0.9)
        assert result[0]["review_score"] == 0.9
