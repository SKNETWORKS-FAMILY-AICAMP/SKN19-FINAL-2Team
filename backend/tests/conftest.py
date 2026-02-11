import sys
import os
from unittest.mock import MagicMock
from dotenv import load_dotenv

# Load env vars from .env
load_dotenv()

# Mock backend.agent.database to prevent DB connection at import time
mock_db = MagicMock()
mock_db.save_recommendation_log = MagicMock()
mock_db.fetch_meta_data = MagicMock(return_value={
    "genders": "Male,Female,Unisex",
    "seasons": "Spring,Summer,Fall,Winter",
    "occasions": "Daily,Special",
    "accords": "Citrus,Woody"
})
sys.modules["backend.agent.database"] = mock_db

# Also mock tools if they use DB
mock_tools = MagicMock()
sys.modules["backend.agent.tools"] = mock_tools
