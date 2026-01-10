import json
import traceback
from typing import Any, AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel # 👈 Pydantic 모델 직접 정의를 위해 추가

# graph.py에서 빌드된 그래프 가져오기
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

# 1. 그래프 빌드 (MemorySaver가 graph.py에 포함되어 있어야 함)
workflow = build_graph()

# 2. 요청 데이터 모델 정의 (thread_id 필수)
# schemas.py를 안 쓰고 여기서 바로 정의해도 됩니다.
class ChatRequest(BaseModel):
    user_query: str
    thread_id: str

@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok"}

# 3. 스트리밍 제너레이터 수정 (비동기 async 적용)
async def stream_generator(user_query: str, thread_id: str) -> AsyncGenerator[str, None]:
    """LangGraph 실행 결과를 SSE 포맷으로 실시간 전송"""
    
    # LangGraph에 전달할 입력값
    inputs = {
        "user_query": user_query,
        # 'messages'나 'history'는 MemorySaver가 알아서 관리하므로 넣지 않아도 됩니다.
    }
    
    # 👇 [핵심] 스레드 ID를 설정에 넣어줘야 기억을 찾습니다.
    config = {"configurable": {"thread_id": thread_id}}

    try:
        # workflow.stream 대신 .astream 사용 (비동기)
        async for event in workflow.astream(inputs, config=config):
            for node_name, state_update in event.items():

                # 1. Researcher 로그 전송 (기존 로직 유지)
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
                if node_name in ["writer", "interviewer", "supervisor"]:
                    # final_response가 있으면 정답으로 전송
                    if "final_response" in state_update:
                        final_res = state_update["final_response"]
                        data = json.dumps(
                            {"type": "answer", "content": final_res}, ensure_ascii=False
                        )
                        yield f"data: {data}\n\n"
                    
                    # Supervisor가 질문이 부족해서 바로 끝내는 경우 등 처리
                    elif "final_response" not in state_update and node_name == "interviewer":
                         pass 

    except Exception as e:
        print(f"\n🚨 [Main Stream Error] 🚨")
        traceback.print_exc()
        
        error_msg = json.dumps({"type": "error", "content": str(e)}, ensure_ascii=False)
        yield f"data: {error_msg}\n\n"


@app.post("/chat")
async def chat_stream(request: ChatRequest):
    # stream_generator에 thread_id 전달
    return StreamingResponse(
        stream_generator(request.user_query, request.thread_id), 
        media_type="text/event-stream"
    )