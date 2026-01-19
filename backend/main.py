# backend/main.py

import json
import time

# import asyncio # 안 쓰면 생략 가능
from typing import Generator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage

# 모듈 임포트
from schemas import ChatRequest
from graph import app_graph

# from database import get_db_connection  # <-- 로깅 안 할 거면 DB 연결 함수도 당장 필요 없음

app = FastAPI(title="Perfume Re-Act Chatbot")

# CORS 설정
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =================================================================
# 1. 헬퍼 함수: 채팅 로그 저장 (지금은 사용 안 함 - 주석 처리)
# =================================================================
# def save_chat_log(thread_id: str, role: str, content: str):
#     conn = None
#     try:
#         conn = get_db_connection()
#         cur = conn.cursor()
#         sql = """
#             INSERT INTO tb_chat_logs (session_id, role, content, created_at)
#             VALUES (%s, %s, %s, NOW())
#         """
#         cur.execute(sql, (thread_id, role, content))
#         conn.commit()
#     except Exception as e:
#         print(f"⚠️ 채팅 로그 저장 실패: {e}")
#     finally:
#         if conn: conn.close()


# =================================================================
# 2. 헬퍼 함수: 가짜 스트리밍
# =================================================================
def simulate_streaming(text: str, delay: float = 0.03) -> Generator[str, None, None]:
    for char in text:
        data = json.dumps({"type": "answer", "content": char}, ensure_ascii=False)
        yield f"data: {data}\n\n"
        time.sleep(delay)


# =================================================================
# 3. 핵심 로직: 스트림 제너레이터
# =================================================================
# backend/main.py


async def stream_generator(
    user_query: str, thread_id: str
) -> Generator[str, None, None]:
    config = {"configurable": {"thread_id": thread_id}}
    inputs = {"messages": [HumanMessage(content=user_query)]}

    full_response = ""

    try:
        # [수정] astream_events를 사용하여 실시간 이벤트를 추적합니다.
        # version="v2" 사용을 권장합니다.
        async for event in app_graph.astream_events(
            inputs, config=config, version="v2"
        ):
            kind = event["event"]
            node_name = event["metadata"].get("langgraph_node", "")

            # ---------------------------------------------------------
            # [A & B] Interviewer & Writer: 실시간 토큰 스트리밍
            # ---------------------------------------------------------
            if kind == "on_chat_model_stream":
                # Writer 혹은 Interviewer 노드에서 생성되는 토큰만 필터링
                if node_name in ["interviewer", "writer"]:

                    # [주의] Interviewer가 Researcher로 넘어가기 전의 메시지는 출력하지 않기로 한 로직 반영
                    # astream_events에서는 실행 중 'next_step'을 알 수 없으므로,
                    # 노드 출력(on_chain_end) 시점에 제어하거나 노드 설계 단에서 필터링이 필요할 수 있습니다.
                    # 여기서는 일단 모든 토큰을 실시간으로 보냅니다.

                    content = event["data"]["chunk"].content
                    if content:
                        full_response += content
                        data = json.dumps(
                            {"type": "answer", "content": content}, ensure_ascii=False
                        )
                        yield f"data: {data}\n\n"

            # ---------------------------------------------------------
            # [C] Researcher (로그): 도구 호출 감지
            # ---------------------------------------------------------
            elif kind == "on_chat_model_end" and node_name == "researcher":
                # Researcher가 도구를 호출하려고 할 때 로그 전송
                output = event["data"]["output"]
                if hasattr(output, "tool_calls") and output.tool_calls:
                    tool_name = output.tool_calls[0]["name"]
                    log_msg = f"🔎 [검색 중] {tool_name} 도구를 사용하고 있습니다..."
                    data = json.dumps(
                        {"type": "log", "content": log_msg}, ensure_ascii=False
                    )
                    yield f"data: {data}\n\n"

            # ---------------------------------------------------------
            # [D] Tools (로그): 도구 실행 완료 감지
            # ---------------------------------------------------------
            elif kind == "on_chain_end" and node_name == "tools":
                log_msg = "✅ 데이터 조회 완료! 분석 중입니다..."
                data = json.dumps(
                    {"type": "log", "content": log_msg}, ensure_ascii=False
                )
                yield f"data: {data}\n\n"

    except GeneratorExit:
        print(f"👋 Client disconnected (Thread: {thread_id})")
        return
    except Exception as e:
        print(f"🚨 Server Error: {e}")
        error_msg = json.dumps({"type": "error", "content": str(e)}, ensure_ascii=False)
        yield f"data: {error_msg}\n\n"


# =================================================================
# 4. API 엔드포인트
# =================================================================
@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat")
async def chat_stream(request: ChatRequest):
    return StreamingResponse(
        stream_generator(request.user_query, request.thread_id),
        media_type="text/event-stream",
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
