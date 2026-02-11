"""
Tests for chat endpoints to prevent regression.
Covers GET /chat/history/{thread_id} and GET /chat/rooms/{member_id}
"""

import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def make_client(monkeypatch):
    """Create a test client with mocked database functions."""
    from main import app
    from agent import database

    # Mock get_chat_history to return sample messages
    def mock_get_chat_history(thread_id: str):
        if thread_id == "thread_123":
            return [
                {"role": "user", "text": "What is bergamot?", "metadata": None},
                {"role": "assistant", "text": "Bergamot is a citrus note...", "metadata": None},
            ]
        return []

    # Mock get_user_chat_list to return sample rooms
    def mock_get_user_chat_list(member_id: int):
        if member_id == 1:
            return [
                {"thread_id": "thread_123", "title": "Perfume Chat", "last_chat_dt": "2025-01-15T10:30:00"},
                {"thread_id": "thread_456", "title": "Fragrance Tips", "last_chat_dt": "2025-01-14T15:45:00"},
            ]
        return []

    monkeypatch.setattr(database, "get_chat_history", mock_get_chat_history)
    monkeypatch.setattr(database, "get_user_chat_list", mock_get_user_chat_list)

    return TestClient(app)


def test_get_history_with_messages(monkeypatch):
    """Test: GET /chat/history/{thread_id} returns 200 with messages array."""
    client = make_client(monkeypatch)

    response = client.get("/chat/history/thread_123")

    assert response.status_code == 200
    data = response.json()
    assert "messages" in data
    assert isinstance(data["messages"], list)
    assert len(data["messages"]) == 2
    assert data["messages"][0]["role"] == "user"
    assert data["messages"][0]["text"] == "What is bergamot?"
    assert data["messages"][1]["role"] == "assistant"


def test_get_history_empty_thread(monkeypatch):
    """Test: GET /chat/history/{thread_id} returns 200 with empty array for non-existent thread."""
    client = make_client(monkeypatch)

    response = client.get("/chat/history/nonexistent_thread")

    assert response.status_code == 200
    data = response.json()
    assert "messages" in data
    assert data["messages"] == []


def test_get_rooms_with_chats(monkeypatch):
    """Test: GET /chat/rooms/{member_id} returns 200 with rooms array."""
    client = make_client(monkeypatch)

    response = client.get("/chat/rooms/1")

    assert response.status_code == 200
    data = response.json()
    assert "rooms" in data
    assert isinstance(data["rooms"], list)
    assert len(data["rooms"]) == 2
    assert data["rooms"][0]["thread_id"] == "thread_123"
    assert data["rooms"][0]["title"] == "Perfume Chat"
    assert "last_chat_dt" in data["rooms"][0]


def test_get_rooms_no_chats(monkeypatch):
    """Test: GET /chat/rooms/{member_id} returns 200 with empty array for member with no chats."""
    client = make_client(monkeypatch)

    response = client.get("/chat/rooms/999")

    assert response.status_code == 200
    data = response.json()
    assert "rooms" in data
    assert data["rooms"] == []


def test_get_rooms_member_zero(monkeypatch):
    """Test: GET /chat/rooms/0 returns 200 with empty array (member_id=0 allowed)."""
    client = make_client(monkeypatch)

    response = client.get("/chat/rooms/0")

    assert response.status_code == 200
    data = response.json()
    assert "rooms" in data
    assert data["rooms"] == []
