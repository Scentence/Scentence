import json
import time
from typing import Generator, List
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
import os
from agent.user_mode import normalize_user_mode
from langchain_core.messages import HumanMessage, AIMessage

# 모듈 임포트
from agent.schemas import ChatRequest
from agent.graph import app_graph
from agent.utils import parse_recommended_count, normalize_recommended_count
from agent.database import (
    save_chat_message,
    get_chat_history,
    get_user_chat_list,
    get_recommended_history,
)
from routers import users, perfumes, archive # <--- ksu 추가

app = FastAPI(title="Perfume Re-Act Chatbot")

uploads_dir = os.path.join(os.getcwd(), "uploads")
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

app.include_router(users.router)
app.include_router(perfumes.router) # <--- ksu 추가
app.include_router(archive.router) # <--- ksu 추가

# CORS origins from environment variable
cors_origins_env = os.getenv("BACKEND_CORS_ORIGINS", "")
if cors_origins_env:
    origins = [origin.strip() for origin in cors_origins_env.split(",") if origin.strip() and origin.strip() != "*"]
else:
    # Default for local development
    origins = ["http://localhost:3000", "http://127.0.0.1:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def resolve_recommended_count(user_query: str, explicit_count: int | None) -> int:
    normalized_explicit = normalize_recommended_count(explicit_count)
    if normalized_explicit is not None:
        return normalized_explicit
    parsed_count = parse_recommended_count(user_query)
    return parsed_count or 3

async def stream_generator(
    user_query: str,
    thread_id: str,
    member_id: int = 0,
    user_mode: str = "BEGINNER",
    recommended_count: int = 3,
) -> Generator[str, None, None]:

    save_chat_message(thread_id, member_id, "user", user_query)
    config = {"configurable": {"thread_id": thread_id}}

    # [★ 수정] 히스토리 중복 방지 로직
    # checkpointer에 state가 있는지 확인
    try:
        current_state = app_graph.get_state(config)
        has_checkpointed_state = (
            current_state
            and current_state.values
            and current_state.values.get("messages")
        )
    except Exception:
        has_checkpointed_state = False

    # checkpointer가 비어있으면 (서버 재시작 등) DB에서 복원
    if not has_checkpointed_state:
        print(f"   🔄 [History] Checkpointer empty, restoring from DB (thread_id: {thread_id})")
        db_history = get_chat_history(thread_id)
        restored_messages = []

        for msg in db_history:
            if msg["role"] == "user" and msg["text"] == user_query:
                continue
            if msg["role"] == "user":
                restored_messages.append(HumanMessage(content=msg["text"]))
            else:
                restored_messages.append(AIMessage(content=msg["text"]))

        # [★추가] DB에서 recommended_history 복원
        db_recommended_history = get_recommended_history(thread_id)

        # 첫 요청: DB 복원 메시지 + 새 메시지
        input_messages = restored_messages + [HumanMessage(content=user_query)]
        print(f"   📊 [History] Restored {len(restored_messages)} messages from DB")
    else:
        # checkpointer에 state 있음: 새 메시지만 전달
        input_messages = [HumanMessage(content=user_query)]
        existing_count = len(current_state.values.get("messages", []))
        print(f"   ✅ [History] Using checkpointer ({existing_count} existing messages)")

        # [★추가] Checkpointer에 이미 recommended_history가 있으면 그것을 사용
        db_recommended_history = current_state.values.get("recommended_history", [])

    normalized_mode = normalize_user_mode(user_mode)

    inputs = {
        "messages": input_messages,
        "member_id": member_id,
        "user_mode": normalized_mode,
        "user_query": user_query,
        "recommended_count": recommended_count,
        "thread_id": thread_id,  # [★추가] DB 백업을 위한 thread_id
        "recommended_history": db_recommended_history,  # [★추가] DB에서 복원한 히스토리
    }

    full_ai_response = ""
    did_stream_parallel_reco = False
    pending_parallel_reco_separator = False

    try:
        async for event in app_graph.astream_events(
            inputs, config=config, version="v2"
        ):
            kind = event["event"]
            metadata = event.get("metadata", {})
            node_name = metadata.get("langgraph_node", "")

            # [1] 노드 종료 시 status 메시지 처리 (Supervisor -> Researcher 전환 시 등)
            if kind == "on_chain_end":
                output = event["data"].get("output")
                if output and isinstance(output, dict) and "status" in output:
                    status_msg = output["status"]
                    data = json.dumps(
                        {"type": "log", "content": status_msg}, ensure_ascii=False
                    )
                    yield f"data: {data}\n\n"

            # [A] Writer & Info Agents: 실시간 답변 스트리밍
            if kind == "on_chat_model_stream":

                # [★추가] 내부용 헬퍼(번역기 등)의 출력은 화면에 보내지 않고 무시(Skip)
                tags = event.get("tags", [])
                if "internal_helper" in tags:
                    continue

                target_nodes = [
                    # Recommendation graph
                    "parallel_reco",
                    # Legacy / other graphs
                    "writer",
                    "perfume_describer",
                    "ingredient_specialist",
                    "similarity_curator",
                    # [Wave 2] Info graph status-specific nodes (only streaming ones)
                    "info_writer",
                ]
                # NOTE: LangGraph's node name comes from workflow.add_node("<name>", ...).
                # We include a prefix fallback in case the runtime metadata differs.
                if node_name in target_nodes or node_name.startswith("parallel_reco"):
                    content = event["data"]["chunk"].content
                    if content:
                        if node_name == "parallel_reco" or node_name.startswith(
                            "parallel_reco"
                        ):
                            if pending_parallel_reco_separator and content.lstrip().startswith(
                                "##"
                            ):
                                content = f"\n\n{content.lstrip()}"
                                pending_parallel_reco_separator = False
                            content = content.replace("---##", "---\n\n##").replace(
                                "--- ##", "---\n\n##"
                            )
                        if node_name == "parallel_reco" or node_name.startswith(
                            "parallel_reco"
                        ):
                            did_stream_parallel_reco = True
                            if content.strip().endswith("---"):
                                pending_parallel_reco_separator = True
                        full_ai_response += content
                        data = json.dumps(
                            {"type": "answer", "content": content}, ensure_ascii=False
                        )
                        yield f"data: {data}\n\n"

            # [B] Interviewer & Fixed Message Nodes: 결과 전송 (non-streaming)
            elif kind == "on_chain_end" and node_name in [
                "interviewer",
                # Info graph fixed message nodes
                "fallback_handler",
                "info_no_results",
                "info_error",
                # Main graph fixed message nodes
                "out_of_scope_handler",
                "unsupported_request_handler",
                # Reco graph fixed message nodes
                "parallel_reco_no_results",
                "parallel_reco_error",
            ]:
                output = event["data"].get("output")
                if output and isinstance(output, dict):
                    messages = output.get("messages")
                    if messages and len(messages) > 0:
                        last_msg = messages[-1]
                        if hasattr(last_msg, "content") and last_msg.content:
                            full_ai_response += last_msg.content
                            data = json.dumps(
                                {"type": "answer", "content": last_msg.content},
                                ensure_ascii=False,
                            )
                            yield f"data: {data}\n\n"

            # [B-2] parallel_reco: 완성된 결과 전송 (non-streaming)
            elif kind == "on_chain_end" and node_name == "parallel_reco":
                output = event["data"].get("output")
                if output and isinstance(output, dict):
                    messages = output.get("messages")
                    if messages and len(messages) > 0:
                        last_msg = messages[-1]
                        if hasattr(last_msg, "content") and last_msg.content:
                            if did_stream_parallel_reco:
                                continue
                            full_ai_response += last_msg.content
                            data = json.dumps(
                                {"type": "answer", "content": last_msg.content},
                                ensure_ascii=False,
                            )
                            yield f"data: {data}\n\n"

            # [C] ★Researcher 내부 단계 전환 (전략 수립 완료 -> 검색 시작)★
            elif kind == "on_chat_model_end" and node_name == "researcher":
                # 리서처 노드 내에서 전략 수립 LLM이 끝나면 즉시 검색 문구로 교체합니다.
                log_msg = "전략에 맞는 향수를 검색중 입니다..."
                data = json.dumps(
                    {"type": "log", "content": log_msg}, ensure_ascii=False
                )
                yield f"data: {data}\n\n"

            # [D] Tools (로그): 데이터 조회 완료
            elif kind == "on_chain_end" and node_name == "tools":
                log_msg = (
                    "✅ 검색된 정보를 분석하여 최적의 추천 리스트를 만드는 중입니다..."
                )
                data = json.dumps(
                    {"type": "log", "content": log_msg}, ensure_ascii=False
                )
                yield f"data: {data}\n\n"

        if full_ai_response:
            save_chat_message(thread_id, member_id, "assistant", full_ai_response)

    except GeneratorExit:
        return
    except Exception as e:
        error_msg = json.dumps({"type": "error", "content": str(e)}, ensure_ascii=False)
        yield f"data: {error_msg}\n\n"


@app.post("/chat")
async def chat_stream(request: ChatRequest):
    recommended_count = resolve_recommended_count(
        request.user_query, request.recommended_count
    )
    return StreamingResponse(
        stream_generator(
            request.user_query,
            request.thread_id,
            request.member_id,
            request.user_mode,
            recommended_count,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/chat/rooms/{member_id}")
async def get_rooms(member_id: int):
    rooms = get_user_chat_list(member_id)
    return {"rooms": rooms}


@app.get("/chat/history/{thread_id}")
async def get_history(thread_id: str):
    messages = get_chat_history(thread_id)
    return {"messages": messages}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
