# main.py
import json
import traceback  # 👈 추가
from typing import Any, Generator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from schemas import ChatRequest
from graph import build_graph

app = FastAPI(title="Perfume Chat Workflow")

origins = ["http://localhost:3000", "http://127.0.0.1:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

workflow = build_graph()

@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok"}

def stream_generator(user_query: str, history: list) -> Generator[str, None, None]:
    """LangGraph 실행 결과를 SSE 포맷으로 실시간 전송"""
    
    payload = {
        "user_query": user_query,
        "messages": history,
        "interview_context": ""
    }

    try:
        for event in workflow.stream(payload):
            for node_name, state_update in event.items():

                # 1. Researcher 로그 전송
                if node_name == "researcher" and "search_logs" in state_update:
                    logs = state_update["search_logs"]
                    if logs:
                        log_content = logs[-1]
                        log_data = json.dumps(
                            {
                                "type": "log",
                                "content": f"🔎 {log_content[:40]}...",
                            },
                            ensure_ascii=False,
                        )
                        yield f"data: {log_data}\n\n"

                # 2. Writer 또는 Interviewer의 최종 텍스트 전송
                if node_name in ["writer", "interviewer"] and "final_response" in state_update:
                    final_res = state_update["final_response"]
                    data = json.dumps(
                        {"type": "answer", "content": final_res}, ensure_ascii=False
                    )
                    yield f"data: {data}\n\n"

    except Exception as e:
        # 👇 [수정됨] 에러 발생 시 Docker 로그에 상세 내용 출력
        print(f"\n🚨 [Main Stream Error] 🚨")
        traceback.print_exc()
        
        error_msg = json.dumps({"type": "error", "content": str(e)}, ensure_ascii=False)
        yield f"data: {error_msg}\n\n"


@app.post("/chat")
async def chat_stream(request: ChatRequest):
    return StreamingResponse(
        stream_generator(request.user_query, request.history), 
        media_type="text/event-stream"
    )