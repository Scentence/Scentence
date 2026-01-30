# backend/agent/test/test_router.py
"""
테스트 전용 API 라우터 (Streaming Version)
기존 챗봇을 호출하고, 실시간 토큰과 내부 로그를 SSE로 스트리밍합니다.
응답 완료 후 비동기로 AI 평가를 수행하여 마지막 이벤트로 전송합니다.
"""
 
import os
import json
import asyncio
from datetime import datetime
from typing import Dict, List, AsyncGenerator
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from langchain_core.messages import HumanMessage
 
# 기존 그래프 import (수정 없이 사용)
# 기존 그래프 import (수정 없이 사용)
from ..graph import app_graph
# import agent.user_mode -> relative import
try:
    from ..user_mode import normalize_user_mode
except ImportError:
    # 혹시 모를 경로 문제 대비
    from agent.user_mode import normalize_user_mode
 
# 테스트 모듈
from .test_agent import TestAgent
from .test_exporter import TestExporter
from .test_schemas import TestChatRequest, TestChatResponse
 
router = APIRouter(prefix="/admin/test", tags=["admin-test"])
 
# 세션별 로그 저장 (메모리)
test_sessions: Dict[str, List[Dict]] = {}
 
async def test_stream_generator(request: TestChatRequest) -> AsyncGenerator[str, None]:
    """
    테스트용 스트림 생성기
    - token: 챗봇 응답 토큰 (실시간)
    - log: 내부 실행 로그 (실시간)
    - evaluation: 최종 평가 결과 (완료 후)
    """
    
    # 1. 입력 구성
    input_data = {
        "messages": [HumanMessage(content=request.user_query)],
        "user_query": request.user_query,
        "member_id": request.member_id or 0,
        "user_mode": request.user_mode or "BEGINNER",
    }
    # [BUG FIX] 프론트엔드에서 보낸 session_id를 LangGraph의 thread_id로 사용해야
    # 세션별로 상태(Memory)가 분리됩니다.
    # 기존 코드: request.thread_id (보통 None이라서 상태 공유 문제 발생 가능)
    thread_id = request.session_id or request.thread_id or "default_test_thread"
    config = {"configurable": {"thread_id": thread_id}}
    
    # 2. 로그: 테스트 시작
    start_log = json.dumps({
        "type": "log",
        "content": f"🚀 테스트 시작: {request.user_query}"
    }, ensure_ascii=False)
    yield f"data: {start_log}\n\n"

    full_response = ""
    
    try:
        # 3. 그래프 실행 및 이벤트 스트리밍
        async for event in app_graph.astream_events(input_data, config=config, version="v2"):
            kind = event["event"]
            node_name = event.get("metadata", {}).get("langgraph_node", "unknown")
            
            # [LOG] 노드 진입/완료 등 상태 변화
            if kind == "on_chain_start" and node_name != "unknown":
                 # 너무 잡다한 로그는 제외하고 주요 노드만
                 if node_name in ["supervisor", "interviewer", "parallel_reco", "writer"]:
                    log_content = f"🔄 노드 실행: {node_name}"
                    yield f"data: {json.dumps({'type': 'log', 'content': log_content}, ensure_ascii=False)}\n\n"

            # [TOKEN] 채팅 모델 스트리밍 (Writer, Parallel Reco 등)
            if kind == "on_chat_model_stream":
                # 내부 헬퍼 태그 무시
                if "internal_helper" in event.get("tags", []):
                    continue
                
                # [BUG FIX] Supervisor, Interviewer 등 구조화된 출력(JSON)을 생성하는 노드의 스트림이
                # 채팅창에 노출되지 않도록 필터링합니다. 오직 최종 응답 노드만 허용.
                if node_name in ["supervisor", "interviewer"]:
                    continue

                chunk_content = event["data"]["chunk"].content
                if chunk_content:
                    full_response += chunk_content
                    # 토큰 전송
                    token_data = json.dumps({
                        "type": "token",
                        "content": chunk_content
                    }, ensure_ascii=False)
                    yield f"data: {token_data}\n\n"

            # [LOG] Supervisor의 결정 등 특정 출력 캡처 (Optional)
            if kind == "on_chain_end" and node_name == "supervisor":
                output = event["data"].get("output")
                if output and "next_step" in output:
                     next_step = output["next_step"]
                     msg = f"👀 Supervisor 결정: {next_step}"
                     yield f"data: {json.dumps({'type': 'log', 'content': msg}, ensure_ascii=False)}\n\n"

            # [BUG FIX] Interviewer는 토큰 스트리밍 대신 최종 결과(JSON)에서 메시지를 추출하여 전송해야 함
            if kind == "on_chain_end" and node_name == "interviewer":
                output = event["data"].get("output")
                # Interviewer output: {"messages": [AIMessage(...)], ...}
                if output and "messages" in output:
                    messages = output["messages"]
                    if messages and len(messages) > 0:
                        last_msg = messages[-1]
                        if hasattr(last_msg, "content") and last_msg.content:
                            # 한 번에 전송 (스트리밍 효과는 없지만 텍스트는 보임)
                            token_data = json.dumps({
                                "type": "token",
                                "content": last_msg.content
                            }, ensure_ascii=False)
                            yield f"data: {token_data}\n\n"

    except Exception as e:
        error_log = json.dumps({
            "type": "log",
            "content": f"❌ 에러 발생: {str(e)}"
        }, ensure_ascii=False)
        yield f"data: {error_log}\n\n"
        # 스트림 종료하지 않고 평가 단계로 넘어갈지 결정 (여기서는 에러 로그만 남김)

    # 4. 로그: 응답 완료
    yield f"data: {json.dumps({'type': 'log', 'content': '✅ 응답 생성 완료. AI 평가를 시작합니다...'}, ensure_ascii=False)}\n\n"
    
    # 5. 비동기 평가 수행
    try:
        test_agent = TestAgent(model="gpt-4o")
        evaluation = await test_agent.evaluate(
            user_input=request.user_query,
            bot_output=full_response,
            conversation_turn=request.turn_count,
            context=request.context or {}
        )
        
        # 6. 세션 저장
        if request.session_id not in test_sessions:
            test_sessions[request.session_id] = []
            
        log_entry = {
            "TC_ID": f"TC_{request.turn_count:03d}",
            "타임스탬프": datetime.now().isoformat(),
            "대화_턴수": request.turn_count,
            "실제입력": request.user_query,
            "실제출력": full_response,
            "기대_출력": evaluation.get("expected_output", ""),
            "판정": evaluation.get("verdict", ""),
            "문제_유형": evaluation.get("issue_type"),
            "심각도": evaluation.get("severity"),
            "수정_방안_제안": evaluation.get("suggestion", ""),
            "수정_대상_에이전트": evaluation.get("target_agent"),
            "영향_파일": evaluation.get("affected_file")
        }
        test_sessions[request.session_id].append(log_entry)
        
        # 7. 평가 결과 전송
        yield f"data: {json.dumps({'type': 'evaluation', 'content': evaluation}, ensure_ascii=False)}\n\n"
        
    except Exception as e:
        yield f"data: {json.dumps({'type': 'log', 'content': f'⚠️ 평가 실패: {str(e)}'}, ensure_ascii=False)}\n\n"


@router.post("/chat")
async def test_chat(request: TestChatRequest):
    """
    테스트용 채팅 (Streaming)
    """
    return StreamingResponse(
        test_stream_generator(request),
        media_type="text/event-stream"
    )

# --- 이하 기존 코드 유지 (Export, Delete, List 등) ---

@router.get("/export/{session_id}")
async def export_test_report(session_id: str, format: str = "csv"):
    if session_id not in test_sessions:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")
 
    if not test_sessions[session_id]:
        raise HTTPException(status_code=400, detail="테스트 결과가 없습니다")
 
    results = test_sessions[session_id]
    exporter = TestExporter(results)
 
    try:
        if format == "csv":
            filepath = exporter.to_csv()
            media_type = "text/csv"
        elif format == "xlsx":
            filepath = exporter.to_excel()
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        elif format == "md":
            filepath = exporter.to_markdown()
            media_type = "text/markdown"
        else:
            raise HTTPException(status_code=400, detail=f"지원하지 않는 형식입니다: {format}")
 
        filename = os.path.basename(filepath)
        return FileResponse(
            filepath,
            filename=filename,
            media_type=media_type
        )
 
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파일 생성 오류: {str(e)}")
 
@router.delete("/session/{session_id}")
async def delete_test_session(session_id: str):
    if session_id in test_sessions:
        del test_sessions[session_id]
        return {"status": "deleted", "session_id": session_id}
    else:
        return {"status": "not_found", "session_id": session_id}
 
@router.get("/sessions")
async def list_test_sessions():
    return {
        "sessions": [
            {
                "id": session_id,
                "count": len(results),
                "summary": {
                    "pass": sum(1 for r in results if r.get("판정") == "PASS"),
                    "warning": sum(1 for r in results if r.get("판정") == "WARNING"),
                    "fail": sum(1 for r in results if r.get("판정") == "FAIL"),
                }
            }
            for session_id, results in test_sessions.items()
        ]
    }
 
@router.get("/session/{session_id}")
async def get_test_session(session_id: str):
    if session_id not in test_sessions:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")
 
    results = test_sessions[session_id]
    summary = {
        "total": len(results),
        "pass": sum(1 for r in results if r.get("판정") == "PASS"),
        "warning": sum(1 for r in results if r.get("판정") == "WARNING"),
        "fail": sum(1 for r in results if r.get("판정") == "FAIL"),
    }
 
    return {
        "session_id": session_id,
        "summary": summary,
        "results": results
    }
 
@router.post("/clear-all")
async def clear_all_sessions():
    count = len(test_sessions)
    test_sessions.clear()
    return {"status": "cleared", "deleted_count": count}