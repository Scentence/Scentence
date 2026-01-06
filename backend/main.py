import os
from typing import Any

import psycopg2
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from main_v3 import build_graph


class ChatRequest(BaseModel):
    user_query: str = Field(..., min_length=1, description="사용자가 입력한 질의")


class ChatResponse(BaseModel):
    final_response: str
    clarified_query: str | None = None
    research_result: str | None = None
    conversation_history: list[dict[str, str]] | None = None


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


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    payload = {"user_query": request.user_query}

    try:
        result = workflow.invoke(payload)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail="챗 처리 중 오류가 발생했습니다.")

    if not result.get("final_response"):
        raise HTTPException(status_code=500, detail="응답을 생성할 수 없습니다.")

    return ChatResponse(
        final_response=result["final_response"],
        clarified_query=result.get("clarified_query"),
        research_result=result.get("research_result"),
        conversation_history=result.get("conversation_history"),
    )