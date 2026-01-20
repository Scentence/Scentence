# backend/main.py

import json
import time
from typing import Generator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage

from schemas import ChatRequest
from graph import app_graph

app = FastAPI(title="Perfume Re-Act Chatbot")

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


async def stream_generator(
    user_query: str, thread_id: str
) -> Generator[str, None, None]:
    config = {"configurable": {"thread_id": thread_id}}
    inputs = {"messages": [HumanMessage(content=user_query)]}

    try:
        async for event in app_graph.astream_events(
            inputs, config=config, version="v2"
        ):
            kind = event["event"]
            metadata = event.get("metadata", {})
            node_name = metadata.get("langgraph_node", "")

            # ---------------------------------------------------------
            # [A] Writer: 실시간 스트리밍 (Writer는 일반 텍스트이므로 OK)
            # ---------------------------------------------------------
            if kind == "on_chat_model_stream":
                # [★수정] interviewer를 여기서 제외! (JSON 노출 방지)
                if node_name == "writer":
                    content = event["data"]["chunk"].content
                    if content:
                        data = json.dumps(
                            {"type": "answer", "content": content}, ensure_ascii=False
                        )
                        yield f"data: {data}\n\n"

            # ---------------------------------------------------------
            # [B] Interviewer: 생각(JSON)이 끝나면 결과 메시지만 전송
            # ---------------------------------------------------------
            elif kind == "on_chain_end" and node_name == "interviewer":
                # Interviewer 노드 실행이 완료된 시점의 출력을 잡습니다.
                output = event["data"].get("output")

                # 메시지가 존재한다면 (추가 질문이 있는 경우)
                if output and isinstance(output, dict):
                    messages = output.get("messages")
                    if messages and len(messages) > 0:
                        last_msg = messages[-1]
                        # 최종 질문 내용만 깔끔하게 전송
                        if hasattr(last_msg, "content") and last_msg.content:
                            data = json.dumps(
                                {"type": "answer", "content": last_msg.content},
                                ensure_ascii=False,
                            )
                            yield f"data: {data}\n\n"

            # ---------------------------------------------------------
            # [C] Researcher (로그): 도구 사용 알림
            # ---------------------------------------------------------
            elif kind == "on_chat_model_end" and node_name == "researcher":
                output = event["data"].get("output")
                if output and hasattr(output, "tool_calls") and output.tool_calls:
                    tool_name = output.tool_calls[0]["name"]
                    log_msg = f"🔎 [검색 중] {tool_name} 도구를 사용하고 있습니다..."
                    data = json.dumps(
                        {"type": "log", "content": log_msg}, ensure_ascii=False
                    )
                    yield f"data: {data}\n\n"

            # ---------------------------------------------------------
            # [D] Tools (로그): 데이터 조회 완료
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
