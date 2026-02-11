import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


class FakeCursor:
    def __init__(self, basic_row, note_rows, accord_rows, season_rows, occasion_rows):
        self.basic_row = basic_row
        self.note_rows = note_rows
        self.accord_rows = accord_rows
        self.season_rows = season_rows
        self.occasion_rows = occasion_rows
        self.step = 0

    def __enter__(self):
        return se
    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, *args, **kwargs):
        self.step += 1

    def fetchone(self):
        if self.step == 1:
            return self.basic_row
        return None

    def fetchall(self):
        if self.step == 2:
            return self.note_rows
        if self.step == 3:
            return self.accord_rows
        if self.step == 4:
            return self.season_rows
        if self.step == 5:
            return self.occasion_rows
        return []


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return self._cursor

    def close(self):
        self.closed = True


def make_client(monkeypatch, cursor):
    from routers import perfumes

    app = FastAPI()
    app.include_router(perfumes.router)
    monkeypatch.setattr(perfumes, "get_perfume_db", lambda: FakeConnection(cursor))
    return TestClient(app)


def test_perfume_detail_success(monkeypatch):
    cursor = FakeCursor(
        basic_row={
            "perfume_id": 123,
            "perfume_name": "Chelsea Flowers",
            "perfume_brand": "Bond No. 9",
            "release_year": 2003,
            "concentration": "Eau de Parfum",
            "perfumer": "Laurent Le Guernec",
            "img_link": "https://example.com/chelsea.jpg",
        },
        note_rows=[
            {"note": "Bergamot", "type": "TOP"},
            {"note": "Rose", "type": "MIDDLE"},
            {"note": "Musk", "type": "BASE"},
        ],
        accord_rows=[
            {"accord": "Floral", "ratio": 0.6},
            {"accord": "Fresh", "ratio": 30},
        ],
        season_rows=[
            {"season": "Spring", "ratio": 0.7},
        ],
        occasion_rows=[
            {"occasion": "Daily", "ratio": 0.4},
        ],
    )
    client = make_client(monkeypatch, cursor)

    response = client.get("/perfumes/detail", params={"perfume_id": 123})
    assert response.status_code == 200
    data = response.json()
    for key in ("perfume_id", "name", "brand", "notes", "accords", "seasons", "occasions"):
        assert key in data
    assert data["notes"]["top"] == ["Bergamot"]
    assert data["notes"]["middle"] == ["Rose"]
    assert data["notes"]["base"] == ["Musk"]


def test_perfume_detail_not_found(monkeypatch):
    cursor = FakeCursor(
        basic_row=None,
        note_rows=[],
        accord_rows=[],
        season_rows=[],
        occasion_rows=[],
    )
    client = make_client(monkeypatch, cursor)

    response = client.get("/perfumes/detail", params={"perfume_id": 999999})
    assert response.status_code == 404


def test_perfume_detail_invalid_param(monkeypatch):
    cursor = FakeCursor(
        basic_row=None,
        note_rows=[],
        accord_rows=[],
        season_rows=[],
        occasion_rows=[],
    )
    client = make_client(monkeypatch, cursor)

    response = client.get("/perfumes/detail", params={"perfume_id": "abc"})
    assert response.status_code == 422
