# main.py
import json
import time  # [추가] 딜레이를 위해 필요
from typing import Generator, Any
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from schemas import ChatRequest
from graph import build_graph
from database import get_recent_messages, save_chat_log

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


# [헬퍼 함수] 텍스트를 한 글자씩 쪼개서 스트리밍 흉내내기
def simulate_streaming(text: str, delay: float = 0.05) -> Generator[str, None, None]:
    for char in text:
        data = json.dumps({"type": "answer", "content": char}, ensure_ascii=False)
        yield f"data: {data}\n\n"
        time.sleep(delay)  # 약간의 딜레이로 타자 효과 연출


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok"}


def stream_generator(user_query: str) -> Generator[str, None, None]:

    # 1. Memory Load & Init
    history = get_recent_messages(limit=6)
    payload = {
        "user_query": user_query,
        "messages": history,
        "route": "supervisor",
        "interview_context": "",
        "active_mode": None,
        "missing_info": None,
        "clarified_query": None,
        "search_plans": [],
        "search_logs": [],
        "research_result": None,
        "retry_count": 0,
        "final_response": None,
        "input_tokens": 0,
        "output_tokens": 0,
        "test_info": {},
        "writer_stream": None,
    }

    save_chat_log(role="user", content=user_query)

    full_ai_response = ""

    try:
        for event in workflow.stream(payload):
            for node_name, state_update in event.items():

                # A. Researcher 로그
                if node_name == "researcher" and "research_result" in state_update:
                    res_text = state_update.get("research_result") or ""
                    preview = (
                        res_text[:30].replace("\n", " ") + "..."
                        if res_text
                        else "결과 없음"
                    )
                    log_data = json.dumps(
                        {
                            "type": "log",
                            "content": f"🔎 조사 완료: {preview}",
                        },
                        ensure_ascii=False,
                    )
                    yield f"data: {log_data}\n\n"

                # B. Writer (진짜 스트리밍)
                if node_name == "writer" and "writer_stream" in state_update:
                    stream_obj = state_update["writer_stream"]
                    if stream_obj:
                        try:
                            for chunk in stream_obj:
                                if chunk.choices[0].delta.content:
                                    token = chunk.choices[0].delta.content
                                    full_ai_response += token
                                    data = json.dumps(
                                        {"type": "answer", "content": token},
                                        ensure_ascii=False,
                                    )
                                    yield f"data: {data}\n\n"
                        except Exception as e:
                            yield f"data: {json.dumps({'type': 'error', 'content': str(e)}, ensure_ascii=False)}\n\n"

                # C. [수정] Interviewer & Fallback (가짜 스트리밍)
                # Interviewer가 질문을 던지거나, Writer가 에러로 인해 텍스트만 반환했을 때
                elif (
                    "final_response" in state_update and state_update["final_response"]
                ):
                    final_res = state_update["final_response"]
                    full_ai_response += final_res  # 저장용 누적

                    # [핵심] 한 번에 보내지 않고 쪼개서 보냄 (Simulated Streaming)
                    # node_name이 'interviewer' 이거나, Writer의 에러 Fallback일 때 작동
                    for chunk in simulate_streaming(final_res):
                        yield chunk

        # 4. Save Log
        if full_ai_response:
            save_chat_log(role="assistant", content=full_ai_response)

    except Exception as e:
        error_msg = json.dumps({"type": "error", "content": str(e)}, ensure_ascii=False)
        yield f"data: {error_msg}\n\n"


@app.post("/chat")
async def chat_stream(request: ChatRequest):
    return StreamingResponse(
        stream_generator(request.user_query), media_type="text/event-stream"
    )
