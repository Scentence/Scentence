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
def stream_generator(user_query: str, thread_id: str) -> Generator[str, None, None]:
    
    # [설정] 1. 사용자 입력 로그 저장 (주석 처리됨)
    # save_chat_log(thread_id, "user", user_query)

    config = {"configurable": {"thread_id": thread_id}}
    inputs = {"messages": [HumanMessage(content=user_query)]}

    full_response = ""

    try:
        # LangGraph 실행
        for event in app_graph.stream(inputs, config=config):
            
            for node_name, state_update in event.items():
                
                # [A] Interviewer (질문)
                if node_name == "interviewer":
                    last_msg = state_update["messages"][-1]
                    content = last_msg.content
                    full_response += content
                    # [수정] 타자 효과 적용
                    yield from simulate_streaming(content)

                # [B] Writer (최종 답변)
                elif node_name == "writer":
                    last_msg = state_update["messages"][-1]
                    content = last_msg.content
                    full_response += content
                    # [수정] 타자 효과 적용
                    yield from simulate_streaming(content)

                # [C] Researcher (로그)
                elif node_name == "researcher":
                    last_msg = state_update["messages"][-1]
                    if last_msg.tool_calls:
                        tool_name = last_msg.tool_calls[0]['name']
                        log_msg = f"🔎 [검색 중] {tool_name} 도구를 사용하고 있습니다..."
                        data = json.dumps({"type": "log", "content": log_msg}, ensure_ascii=False)
                        yield f"data: {data}\n\n"

                # [D] Tools (로그)
                elif node_name == "tools":
                    log_msg = "✅ 데이터 조회 완료! 분석 중입니다..."
                    data = json.dumps({"type": "log", "content": log_msg}, ensure_ascii=False)
                    yield f"data: {data}\n\n"

        # [설정] 3. AI 답변 로그 저장 (주석 처리됨)
        # if full_response:
        #     save_chat_log(thread_id, "assistant", full_response)

    # [★핵심 수정] 클라이언트 연결 종료 시 조용히 종료
    except GeneratorExit:
        print(f"👋 Client disconnected (Thread: {thread_id})")
        # 여기서 return하면 제너레이터가 깔끔하게 닫힙니다.
        return 

    # 일반적인 에러 처리
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
        media_type="text/event-stream"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)