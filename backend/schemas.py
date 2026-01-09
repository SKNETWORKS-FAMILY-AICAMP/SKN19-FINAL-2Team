# schemas.py
from typing_extensions import TypedDict, Literal
from pydantic import BaseModel, Field


# main_v3.py의 State
class State(TypedDict):
    user_query: str
    route: Literal["interviewer", "researcher", "writer"]
    clarified_query: str | None
    research_result: str | None
    final_response: str


# main.py의 Request Body
class ChatRequest(BaseModel):
    user_query: str = Field(..., min_length=1, description="사용자가 입력한 질의")
