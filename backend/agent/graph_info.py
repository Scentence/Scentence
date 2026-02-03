# backend/agent/graph_info.py
import json
import asyncio
from typing import Literal
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END

# [1] 스키마 임포트
from .schemas_info import InfoState, InfoRoutingDecision
from .tools_schemas_info import IngredientAnalysisResult

# [2] 도구 임포트
from .tools_info import (
    lookup_perfume_info_tool,
    lookup_perfume_by_id_tool,
    lookup_note_info_tool,
    lookup_accord_info_tool,
)
from .tools_similarity import lookup_similar_perfumes_tool

# [3] 프롬프트 임포트
from .prompts_info import (
    INFO_SUPERVISOR_PROMPT,
    PERFUME_DESCRIBER_PROMPT_BEGINNER,
    PERFUME_DESCRIBER_PROMPT_EXPERT,
    SIMILARITY_CURATOR_PROMPT_BEGINNER,
    SIMILARITY_CURATOR_PROMPT_EXPERT,
    INGREDIENT_SPECIALIST_PROMPT,
)

# [4] Expression Loader for dynamic dictionary injection
from .expression_loader import ExpressionLoader

load_dotenv()

# [LLM 이원화]
INFO_LLM = ChatOpenAI(model="gpt-4o", temperature=0, streaming=True)
ROUTER_LLM = ChatOpenAI(model="gpt-4o", temperature=0, streaming=False)


# ==========================================
# 4. Utility Functions for Ordinal/Pronoun Resolution
# ==========================================

import re
from typing import List, Dict, Optional


def extract_save_refs(messages: List) -> List[Dict[str, any]]:
    """
    Extract SAVE tags from most recent AIMessage containing recommendations.
    Returns list of {id: int, name: str} in order of appearance.
    """
    save_pattern = re.compile(r'\[\[SAVE:(\d+):([^\]]+)\]\]')
    
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and msg.content:
            matches = save_pattern.findall(msg.content)
            if matches:
                return [{"id": int(m[0]), "name": m[1]} for m in matches]
    
    return []


def parse_ordinal(user_query: str) -> Optional[int]:
    """
    Parse ordinal numbers from Korean text (supports 1-10).
    Returns 1-based index (1, 2, 3, ...) or None if not found.
    """
    query_lower = user_query.lower()
    
    numeric_match = re.search(r'(\d+)\s*(번째|번)\b', query_lower)
    if numeric_match:
        return int(numeric_match.group(1))
    
    korean_ordinals = {
        '첫': 1, '첫번째': 1, '1번째': 1, '1번': 1,
        '두': 2, '두번째': 2, '둘째': 2, '2번째': 2, '2번': 2,
        '세': 3, '세번째': 3, '셋째': 3, '3번째': 3, '3번': 3,
        '네': 4, '네번째': 4, '넷째': 4, '4번째': 4, '4번': 4,
        '다섯': 5, '다섯번째': 5, '다섯째': 5, '5번째': 5, '5번': 5,
        '여섯': 6, '여섯번째': 6, '여섯째': 6, '6번째': 6, '6번': 6,
        '일곱': 7, '일곱번째': 7, '일곱째': 7, '7번째': 7, '7번': 7,
        '여덟': 8, '여덟번째': 8, '여덟째': 8, '8번째': 8, '8번': 8,
        '아홉': 9, '아홉번째': 9, '아홉째': 9, '9번째': 9, '9번': 9,
        '열': 10, '열번째': 10, '열째': 10, '10번째': 10, '10번': 10,
    }
    
    for pattern, num in korean_ordinals.items():
        if pattern in query_lower:
            return num
    
    return None


def resolve_target_from_ordinal_or_pronoun(
    user_query: str,
    router_target_name: str,
    save_refs: List[Dict[str, any]]
) -> Optional[Dict[str, any]]:
    """
    Resolve target perfume from ordinal numbers or pronouns.
    Returns {id: int, name: str} or None if resolution fails.
    """
    pronouns = ['이거', '그거', '이 향수', '저거']
    generic_terms = ['추천해줘', '비슷한거']
    
    ordinal = parse_ordinal(user_query)
    is_pronoun = any(p in user_query for p in pronouns)
    is_generic = router_target_name in generic_terms or any(g in router_target_name for g in generic_terms)
    
    if ordinal:
        if 1 <= ordinal <= len(save_refs):
            return save_refs[ordinal - 1]
        else:
            return None
    
    if is_pronoun or is_generic:
        if save_refs:
            return save_refs[-1]
    
    return None


# ==========================================
# 5. Streaming Helper for Silent Failure Prevention
# ==========================================

async def stream_fixed_message(text: str) -> AIMessage:
    """
    Stream a fixed message through LLM to ensure output appears in UI.
    Prevents silent failures by guaranteeing on_chat_model_stream events.
    """
    system_prompt = "Output EXACTLY the next user message. Do not add, remove, or change any character. No quotes."
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=text)
    ]
    
    response = await INFO_LLM.ainvoke(messages)
    
    if response.content.strip() != text.strip():
        print(f"      ⚠️ [Stream Mismatch] Expected: '{text}' | Got: '{response.content}'", flush=True)
        
        retry_system = "Your previous output was invalid. Output the next user message EXACTLY, character-for-character."
        retry_messages = [
            SystemMessage(content=retry_system),
            HumanMessage(content=text)
        ]
        response = await INFO_LLM.ainvoke(retry_messages)
        
        if response.content.strip() != text.strip():
            print(f"      ⚠️ [Stream Retry Failed] Using retry output anyway", flush=True)
    
    return response


# ==========================================
# 5-1. Result Status Classification (Wave 1)
# ==========================================

def classify_info_status(result: str) -> Literal['OK', 'NO_RESULTS', 'ERROR']:
    """
    검색 결과 문자열을 분석하여 상태를 분류합니다.
    
    분기 기준:
    - ERROR: 기술적 오류 (DB 에러, 예외 등)
    - NO_RESULTS: 데이터 부재 (빈 결과, 검색 실패)
    - OK: 정상 데이터 존재
    
    Args:
        result: 검색 결과 문자열
        
    Returns:
        'ERROR' | 'NO_RESULTS' | 'OK'
    """
    if any(keyword in result for keyword in ["DB 에러", "Error"]):
        return 'ERROR'
    
    if (
        not result
        or result in ["{}", "[]", ""]
        or any(keyword in result for keyword in ["찾을 수 없습니다", "검색 실패", "결과가 없습니다"])
    ):
        return 'NO_RESULTS'
    
    return 'OK'


# ==========================================
# 6. Node Functions
# ==========================================


def info_supervisor_node(state: InfoState):
    """[Router] 분류 노드"""
    print(f"\n   ▶️ [Info Subgraph] Supervisor 노드 시작", flush=True)
    user_query = state.get("user_query", "")

    chat_history = state.get("messages", [])
    context_str = ""
    if chat_history:
        recent_msgs = chat_history[-3:] if len(chat_history) > 3 else chat_history
        for msg in recent_msgs:
            role = "User" if isinstance(msg, HumanMessage) else "AI"
            if msg.content:
                context_str += f"- {role}: {msg.content}\n"

    final_system_prompt = INFO_SUPERVISOR_PROMPT
    if context_str:
        final_system_prompt += f"\n\n[Recent Chat Context]\n{context_str}"

    final_system_prompt += "\n\n[Instruction]\nResolve the target name from context and classify based on the PRIORITY rules."

    messages = [
        SystemMessage(content=final_system_prompt),
        HumanMessage(content=user_query),
    ]

    try:
        decision = ROUTER_LLM.with_structured_output(InfoRoutingDecision).invoke(
            messages
        )
        final_target = decision.target_name
        
        save_refs = extract_save_refs(chat_history)
        
        resolved = resolve_target_from_ordinal_or_pronoun(
            user_query, final_target, save_refs
        )
        
        if resolved:
            ordinal = parse_ordinal(user_query)
            
            info_type = decision.info_type
            if any(kw in user_query for kw in ['비슷', '추천', '대체', '같은']):
                info_type = "similarity"
            elif resolved:
                info_type = "perfume"
            
            return {
                "info_type": info_type,
                "target_id": resolved['id'],
                "target_name": resolved['name']
            }
        
        if not save_refs and (parse_ordinal(user_query) or any(p in user_query for p in ['이거', '그거', '이 향수', '저거'])):
            fail_msg = "최근에 추천드린 향수 목록을 찾지 못했어요. 향수 이름을 직접 말씀해 주시면 바로 찾아드릴게요."
            return {"info_type": "unknown", "target_name": "unknown", "fail_msg": fail_msg}
        
        ordinal = parse_ordinal(user_query)
        if ordinal and ordinal > len(save_refs):
            fail_msg = f"지금 추천은 1~{len(save_refs)}번째까지 있어요. 원하시는 번호로 다시 말씀해 주세요."
            return {"info_type": "unknown", "target_name": "unknown", "fail_msg": fail_msg}
        
        if not final_target or final_target in [
            "이거",
            "그거",
            "이 향수",
            "추천해줘",
            "비슷한거",
        ]:
            return {"info_type": "unknown", "target_name": "unknown"}

        return {"info_type": decision.info_type, "target_name": final_target}

    except Exception as e:
        print(f"      ❌ Supervisor 에러 발생: {e}", flush=True)
        return {"info_type": "unknown", "target_name": "unknown"}


async def perfume_describer_node(state: InfoState):
    """[Perfume Expert] 상세 정보"""
    target = state["target_name"]
    target_id = state.get("target_id")

    user_mode = state.get("user_mode", "BEGINNER")
    try:
        if target_id:
            search_result_json = await lookup_perfume_by_id_tool.ainvoke({"perfume_id": target_id})
        else:
            search_result_json = await lookup_perfume_info_tool.ainvoke(target)

        # [Wave 2] 검색 결과 상태 분류
        status = classify_info_status(search_result_json)
        
        if status != "OK":
            # Retry with name if we have both ID and name
            if target_id and target:
                search_result_json = await lookup_perfume_info_tool.ainvoke(target)
                status = classify_info_status(search_result_json)
            
            # Still not OK after retry
            if status != "OK":
                return {"info_status": status}

        if user_mode == "EXPERT":
            print("      😎 [Mode] 전문가용 분석 프롬프트 적용")
            selected_prompt = PERFUME_DESCRIBER_PROMPT_EXPERT
        else:
            print("      🐥 [Mode] 비기너용 도슨트 프롬프트 적용")
            selected_prompt = PERFUME_DESCRIBER_PROMPT_BEGINNER

        # [★ Dynamic Expression Injection]
        # Parse perfume data to extract notes and accords
        try:
            perfume_data = json.loads(search_result_json)
            perfume_name = perfume_data.get("name", "Unknown")
            brand = perfume_data.get("brand", "Unknown")
            
            loader = ExpressionLoader()
            expression_guide = []
            injected_count = 0
            
            all_notes = []
            all_accords = []
            
            # Extract notes
            for note_type in ["top_notes", "middle_notes", "base_notes"]:
                note_str = perfume_data.get(note_type, "")
                if note_str and note_str != "N/A":
                    notes = [n.strip() for n in note_str.split(",")]
                    all_notes.extend(notes)
                    for note in notes[:5]:  # Limit per type
                        desc = loader.get_note_desc(note)
                        if desc:
                            expression_guide.append(f"- {note}: {desc}")
                            injected_count += 1
            
            # Extract accords
            accord_str = perfume_data.get("accords", "")
            if accord_str:
                accords = [a.strip() for a in accord_str.split(",")]
                all_accords = accords
                for accord in accords[:5]:
                    desc = loader.get_accord_desc(accord)
                    if desc:
                        expression_guide.append(f"- {accord}: {desc}")
                        injected_count += 1
            
            expression_text = "\n".join(expression_guide) if expression_guide else ""
            
        except Exception as e:
            expression_text = ""

        content_parts = [f"대상 향수: {target}"]
        if expression_text:
            content_parts.append(f"\n[감각 표현 참고]:\n{expression_text}")
        content_parts.append(f"\n[검색된 상세 정보]:\n{search_result_json}")

        messages = [
            SystemMessage(content=selected_prompt),
            HumanMessage(content="\n".join(content_parts)),
        ]
        response = await INFO_LLM.ainvoke(messages)

        return {"messages": [response], "final_answer": response.content, "info_status": "OK"}

    except Exception as e:
        print(f"      ❌ Perfume Describer 에러: {e}", flush=True)
        return {"info_status": "ERROR"}


async def ingredient_specialist_node(state: InfoState):
    """[Ingredient Expert] 성분 분석"""
    try:
        user_query = state.get("user_query", "")
        target_name = state.get("target_name", "")
        print(
            f"\n   ▶️ [Info Subgraph] Ingredient Specialist: '{user_query}'", flush=True
        )

        # 1. 쿼리 분석 로직 (원래 로직 유지)
        analysis_prompt = f"""
        You are a query analyzer. Separate 'Notes' and 'Accords'.
        Query: "{user_query}"
        Context Target: "{target_name}"
        Output JSON: {{ "notes": [], "accords": [], "is_ambiguous": false }}
        """

        try:
            analysis = await ROUTER_LLM.with_structured_output(
                IngredientAnalysisResult
            ).ainvoke(analysis_prompt, config={"tags": ["internal_helper"]})
            print(
                f"      - 분석 결과: Notes={analysis.notes}, Accords={analysis.accords}",
                flush=True,
            )
        except Exception as e:
            print(f"      ⚠️ 분석 실패: {e}", flush=True)
            analysis = IngredientAnalysisResult(notes=[target_name], accords=[])

        # 2. 병렬 도구 호출 (원래 로직 유지)
        tasks = []
        tasks.append(
            lookup_note_info_tool.ainvoke({"keywords": analysis.notes})
            if analysis.notes
            else asyncio.sleep(0, result="")
        )
        tasks.append(
            lookup_accord_info_tool.ainvoke({"keywords": analysis.accords})
            if analysis.accords
            else asyncio.sleep(0, result="")
        )

        results = await asyncio.gather(*tasks)
        note_result, accord_result = results[0], results[1]

        # 3. 상세 로깅 함수 및 실행 (원래 로직 유지)
        def print_result_log(category: str, result_str: str):
            if not result_str:
                return
            try:
                data = json.loads(result_str)
                if not data:
                    print(f"      🔍 [{category}]: 결과 없음 (Empty)", flush=True)
                    return
                for key, val in data.items():
                    if isinstance(val, dict):
                        perfumes = val.get("representative_perfumes", [])
                        perfume_log = ", ".join(perfumes) if perfumes else "없음"
                        print(
                            f"      🔍 [{category}] '{key}': (대표향수: {perfume_log})",
                            flush=True,
                        )
            except:
                pass

        print_result_log("Note DB", note_result)
        print_result_log("Accord DB", accord_result)

        # [Wave 2] 검색 결과 상태 분류
        note_status = classify_info_status(note_result)
        accord_status = classify_info_status(accord_result)
        
        # 둘 다 NO_RESULTS 또는 ERROR면 실패
        if note_status != "OK" and accord_status != "OK":
            # 둘 중 하나라도 ERROR면 ERROR, 아니면 NO_RESULTS
            if note_status == "ERROR" or accord_status == "ERROR":
                return {"info_status": "ERROR"}
            else:
                return {"info_status": "NO_RESULTS"}

        # 4. LLM 기반 답변 생성 (데이터가 있을 때만 실행)
        # [★ Dynamic Expression Injection]
        loader = ExpressionLoader()
        expression_guide = []
        injected_count = 0
        
        # Add note descriptions
        for note in analysis.notes[:10]:
            desc = loader.get_note_desc(note)
            if desc:
                expression_guide.append(f"- {note}: {desc}")
                injected_count += 1
        
        # Add accord descriptions
        for accord in analysis.accords[:10]:
            desc = loader.get_accord_desc(accord)
            if desc:
                expression_guide.append(f"- {accord}: {desc}")
                injected_count += 1
        
        expression_text = "\n".join(expression_guide) if expression_guide else ""
        
        context_parts = [
            f"[User Interest]: Notes: {analysis.notes}, Accords: {analysis.accords}",
        ]
        
        if expression_text:
            context_parts.append(f"\n[감각 표현 참고]:\n{expression_text}")
        
        context_parts.append(f"""
        [Search Results]:
        --- Note Data ---
        {note_result}
        --- Accord Data ---
        {accord_result}
        """)
        
        combined_context = "\n".join(context_parts)

        messages = [
            SystemMessage(content=INGREDIENT_SPECIALIST_PROMPT),
            HumanMessage(content=combined_context),
        ]
        response = await INFO_LLM.ainvoke(messages)

        return {"messages": [response], "final_answer": response.content, "info_status": "OK"}

    except Exception as e:
        print(f"      ❌ Ingredient Specialist 에러: {e}", flush=True)
        return {"info_status": "ERROR"}


async def similarity_curator_node(state: InfoState):
    """[Similarity Expert] 유사 추천"""

    user_mode = state.get("user_mode", "BEGINNER")
    try:
        target = state["target_name"]

        # 1. 도구 호출 (기존 로직 유지)
        search_result_json = await lookup_similar_perfumes_tool.ainvoke(target)

        # [Wave 2] 검색 결과 상태 분류
        status = classify_info_status(search_result_json)
        
        if status != "OK":
            return {"info_status": status}
        if user_mode == "EXPERT":
            print("      😎 [Mode] 전문가용 큐레이터 프롬프트 적용")
            selected_prompt = SIMILARITY_CURATOR_PROMPT_EXPERT
        else:
            print("      🐥 [Mode] 비기너용 도슨트 프롬프트 적용")
            selected_prompt = SIMILARITY_CURATOR_PROMPT_BEGINNER

        messages = [
            SystemMessage(content=selected_prompt),
            HumanMessage(
                content=f"원본 향수: {target}\n\n[추천 후보군 데이터]:\n{search_result_json}"
            ),
        ]
        response = await INFO_LLM.ainvoke(messages)

        return {"messages": [response], "final_answer": response.content, "info_status": "OK"}

    except Exception as e:
        print(f"      ❌ Similarity Curator 에러: {e}", flush=True)
        return {"info_status": "ERROR"}


async def fallback_handler_node(state: InfoState):
    """[Fallback] 안내"""
    print(f"\n   ⚠️ [Info Subgraph] Fallback Handler 실행", flush=True)
    
    fail_msg = state.get("fail_msg")
    if fail_msg:
        response = await stream_fixed_message(fail_msg)
        return {"messages": [response], "final_answer": response.content}
    
    fallback_msg = "죄송합니다. 말씀하신 향수가 무엇인지 정확히 파악하지 못했어요. 😅\n'샤넬 넘버5랑 비슷한 거 추천해줘' 처럼 향수 이름을 콕 집어서 다시 말씀해 주시겠어요?"
    response = await stream_fixed_message(fallback_msg)
    return {"messages": [response], "final_answer": response.content}


# ==========================================
# 6-1. Result Router and Status-Specific Nodes (Wave 2)
# ==========================================

def info_result_router_node(state: InfoState):
    """
    info_status 값에 따라 다음 노드로 라우팅합니다.
    
    Returns:
        다음 노드 이름 ('info_writer' | 'info_no_results' | 'info_error')
    """
    info_status = state.get("info_status", "OK")
    
    print(f"\n   🔀 [Info Router] Status: {info_status}", flush=True)
    
    if info_status == "NO_RESULTS":
        return "info_no_results"
    elif info_status == "ERROR":
        return "info_error"
    else:
        return "info_writer"


async def info_no_results_node(state: InfoState):
    """
    검색 결과가 없을 때 대안을 제시하는 노드입니다.
    """
    print(f"\n   ⚠️ [Info No Results] 검색 결과 없음 처리", flush=True)
    
    target_name = state.get("target_name", "해당 항목")
    info_type = state.get("info_type", "unknown")
    
    if info_type == "perfume":
        msg = f"죄송합니다. '{target_name}'에 대한 상세 정보를 데이터베이스에서 찾을 수 없습니다. 😢\n\n다른 향수 이름으로 다시 검색해 보시거나, '플로랄 향수 추천해줘' 같은 방식으로 물어봐 주세요!"
    elif info_type in ["note", "accord", "ingredient"]:
        msg = f"죄송합니다. '{target_name}' 성분에 대한 상세 정보가 현재 데이터베이스에 등록되어 있지 않습니다. 😢\n\n'우디', '플로랄', '시트러스' 같은 일반적인 노트나 어코드로 다시 물어봐 주세요!"
    elif info_type == "similarity":
        msg = f"현재 저희 데이터베이스에는 '{target_name}'과 결이 비슷한 향수 정보가 충분하지 않네요. 😅\n\n다른 향수로 다시 찾아봐 드릴까요?"
    else:
        msg = f"죄송합니다. '{target_name}'에 대한 정보를 찾을 수 없습니다. 😢\n\n향수 이름을 정확히 말씀해 주시거나, 다른 방식으로 질문해 주세요!"
    
    response = await stream_fixed_message(msg)
    return {"messages": [response], "final_answer": response.content}


async def info_error_node(state: InfoState):
    """
    기술적 오류 발생 시 고정 문구를 출력하는 노드입니다.
    """
    print(f"\n   ❌ [Info Error] 기술적 오류 처리", flush=True)
    
    msg = "죄송합니다. 현재 알 수 없는 오류가 발생하였습니다. 잠시 후 다시 시도해 주세요. 🙏"
    
    response = await stream_fixed_message(msg)
    return {"messages": [response], "final_answer": response.content}


async def info_writer_node(state: InfoState):
    """
    OK 상태일 때 검색 결과를 형식화/요약하는 노드입니다.
    근거 없는 새 사실 생성 금지 (ZERO HALLUCINATION).
    """
    print(f"\n   ✍️ [Info Writer] 결과 형식화", flush=True)
    
    final_answer = state.get("final_answer")
    if final_answer:
        print(f"      ℹ️ [Info Writer] 기존 답변 사용 (이미 처리됨)", flush=True)
        return {"messages": [AIMessage(content=final_answer)]}
    
    print(f"      ⚠️ [Info Writer] final_answer 없음, fallback 처리", flush=True)
    msg = "죄송합니다. 답변을 생성하는 중 문제가 발생했습니다."
    response = await stream_fixed_message(msg)
    return {"messages": [response], "final_answer": response.content}


# ==========================================
# 7. Graph Build (Info Subgraph)
# ==========================================
info_workflow = StateGraph(InfoState)

info_workflow.add_node("info_supervisor", info_supervisor_node)
info_workflow.add_node("perfume_describer", perfume_describer_node)
info_workflow.add_node("ingredient_specialist", ingredient_specialist_node)
info_workflow.add_node("similarity_curator", similarity_curator_node)
info_workflow.add_node("fallback_handler", fallback_handler_node)

info_workflow.add_edge(START, "info_supervisor")

info_workflow.add_conditional_edges(
    "info_supervisor",
    lambda x: x["info_type"],
    {
        "perfume": "perfume_describer",
        "brand": "perfume_describer",
        "note": "ingredient_specialist",
        "accord": "ingredient_specialist",
        "ingredient": "ingredient_specialist",
        "similarity": "similarity_curator",
        "unknown": "fallback_handler",
    },
)

# [Wave 2] 새 노드 추가
info_workflow.add_node("info_result_router", info_result_router_node)
info_workflow.add_node("info_no_results", info_no_results_node)
info_workflow.add_node("info_error", info_error_node)
info_workflow.add_node("info_writer", info_writer_node)

# [Wave 2] 기존 노드들 → router로 연결
info_workflow.add_edge("perfume_describer", "info_result_router")
info_workflow.add_edge("ingredient_specialist", "info_result_router")
info_workflow.add_edge("similarity_curator", "info_result_router")
info_workflow.add_edge("fallback_handler", END)

# [Wave 2] router → 상태별 노드로 분기
info_workflow.add_conditional_edges(
    "info_result_router",
    lambda x: x,
    {
        "info_writer": "info_writer",
        "info_no_results": "info_no_results",
        "info_error": "info_error",
    },
)

# [Wave 2] 상태별 노드 → END
info_workflow.add_edge("info_writer", END)
info_workflow.add_edge("info_no_results", END)
info_workflow.add_edge("info_error", END)

info_graph = info_workflow.compile()
