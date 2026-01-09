import json
import asyncio
from typing import Any, Generator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

# main_v3.py에서 그래프 가져오기
from main_v3 import build_graph

class ChatRequest(BaseModel):
    user_query: str = Field(..., min_length=1, description="사용자가 입력한 질의")

app = FastAPI(title="Perfume Chat Workflow")

origins = ["http://localhost:3000", "http://127.0.0.1:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 그래프 빌드
workflow = build_graph()

@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok"}

def stream_generator(user_query: str) -> Generator[str, None, None]:
    """LangGraph 실행 결과를 실시간 SSE 포맷으로 전송"""
    payload = {"user_query": user_query}
    
    try:
        # workflow.stream은 노드(단계)가 끝날 때마다 상태를 반환합니다.
        for event in workflow.stream(payload):
            for node_name, state_update in event.items():
                
                # 1. Researcher 단계: 조사 결과가 있으면 로그 전송
                if node_name == "researcher" and "research_result" in state_update:
                    log_data = json.dumps({
                        "type": "log",
                        "content": f"🔎 조사 완료: {state_update['research_result'][:30]}..."
                    }, ensure_ascii=False)
                    yield f"data: {log_data}\n\n"

                # 2. Writer 단계: 최종 답변이 있으면 전송
                # (LangGraph 특성상 Writer 노드가 완료되어야 텍스트가 나옵니다)
                if node_name == "writer" and "final_response" in state_update:
                    final_res = state_update["final_response"]
                    
                    # 프론트엔드에서 '타자 치는 효과'를 위해 전체 텍스트를 보냄
                    data = json.dumps({
                        "type": "answer",
                        "content": final_res
                    }, ensure_ascii=False)
                    yield f"data: {data}\n\n"

    except Exception as e:
        error_msg = json.dumps({"type": "error", "content": str(e)}, ensure_ascii=False)
        yield f"data: {error_msg}\n\n"

@app.post("/chat")
async def chat_stream(request: ChatRequest):
    """스트리밍 엔드포인트"""
    return StreamingResponse(
        stream_generator(request.user_query),
        media_type="text/event-stream"
    )