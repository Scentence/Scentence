# backend/agent/graph.py
import os
import json
import asyncio
import itertools
import random
from typing import Literal, List, Dict, Any, Optional

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

# [Import] 로컬 모듈
from .schemas import (
    AgentState,
    UserPreferences,
    InterviewResult,
    RoutingDecision,
    ResearchActionPlan,
    SearchStrategyPlan,
    ResearcherOutput,
    StrategyResult,
    PerfumeDetail,
    PerfumeNotes,
)

# [Import] Expression Loader for dynamic dictionary injection
from .expression_loader import ExpressionLoader

from .tools import (
    advanced_perfume_search_tool,
    lookup_note_by_string_tool,
    lookup_note_by_vector_tool,
)

from .prompts import (
    SUPERVISOR_PROMPT,
    INTERVIEWER_PROMPT,
    RESEARCHER_SYSTEM_PROMPT,
    WRITER_FAILURE_PROMPT,
    WRITER_CHAT_PROMPT,
    WRITER_RECOMMENDATION_PROMPT,
    WRITER_RECOMMENDATION_PROMPT_EXPERT,
    WRITER_RECOMMENDATION_PROMPT_SINGLE,
    WRITER_RECOMMENDATION_PROMPT_EXPERT_SINGLE,
    NOTE_SELECTION_PROMPT,
)
from .database import save_recommendation_log, fetch_meta_data
from .denylist import has_forbidden_words, UserFriendlyStrategyLabels

# [정보 검색 전용 서브 그래프 임포트]
from .graph_info import info_graph

load_dotenv()

import logging

logger = logging.getLogger(__name__)

# ==========================================
# 1. 모델 설정
# ==========================================
FAST_LLM = ChatOpenAI(model="gpt-4.1-mini", temperature=0, streaming=True)
SMART_LLM = ChatOpenAI(model="gpt-4.1", temperature=0, streaming=True)
SUPER_SMART_LLM = ChatOpenAI(model="gpt-5.2", temperature=0, streaming=True)
# Non-streaming version for parallel_reco to prevent token interleaving
SUPER_SMART_LLM_NO_STREAM = ChatOpenAI(model="gpt-5.2", temperature=0, streaming=False)


# ==========================================
# 2. 유틸리티
# ==========================================
def log_filters(h_filters: dict, s_filters: dict):
    pass


def sanitize_filters(h_filters: dict, s_filters: dict) -> tuple:
    """
    Sanitize filters by dropping unknown keys and invalid values.
    
    Args:
        h_filters: Hard filters (gender, etc.)
        s_filters: Strategy filters (accord, occasion, note, season)
    
    Returns:
        Tuple of (sanitized_hard_filters, sanitized_strategy_filters, dropped_items)
    """
    meta = fetch_meta_data()
    
    allowed_genders = {g.strip() for g in meta.get("genders", "").split(",") if g.strip()}
    allowed_seasons = {s.strip() for s in meta.get("seasons", "").split(",") if s.strip()}
    allowed_occasions = {o.strip() for o in meta.get("occasions", "").split(",") if o.strip()}
    allowed_accords = {a.strip() for a in meta.get("accords", "").split(",") if a.strip()}
    
    allowed_strategy_keys = {"accord", "occasion", "note", "season"}
    
    dropped_items = {
        "hard_filters": {},
        "strategy_filters": {}
    }
    
    sanitized_hard = {}
    for key, value in h_filters.items():
        if key == "gender":
            if isinstance(value, list):
                valid_values = [v for v in value if v in allowed_genders]
                invalid_values = [v for v in value if v not in allowed_genders]
                if invalid_values:
                    dropped_items["hard_filters"][key] = invalid_values
                if valid_values:
                    sanitized_hard[key] = valid_values
            elif value in allowed_genders:
                sanitized_hard[key] = value
            else:
                dropped_items["hard_filters"][key] = value
        else:
            sanitized_hard[key] = value
    
    sanitized_strategy = {}
    for key, value in s_filters.items():
        if key not in allowed_strategy_keys:
            dropped_items["strategy_filters"][key] = value
            continue
        
        if key == "note":
            sanitized_strategy[key] = value
        elif key == "season":
            if isinstance(value, list):
                valid_values = [v for v in value if v in allowed_seasons]
                invalid_values = [v for v in value if v not in allowed_seasons]
                if invalid_values:
                    dropped_items["strategy_filters"][f"{key}_invalid_values"] = invalid_values
                if valid_values:
                    sanitized_strategy[key] = valid_values
            elif value in allowed_seasons:
                sanitized_strategy[key] = value
            else:
                dropped_items["strategy_filters"][key] = value
        elif key == "occasion":
            if isinstance(value, list):
                valid_values = [v for v in value if v in allowed_occasions]
                invalid_values = [v for v in value if v not in allowed_occasions]
                if invalid_values:
                    dropped_items["strategy_filters"][f"{key}_invalid_values"] = invalid_values
                if valid_values:
                    sanitized_strategy[key] = valid_values
            elif value in allowed_occasions:
                sanitized_strategy[key] = value
            else:
                dropped_items["strategy_filters"][key] = value
        elif key == "accord":
            if isinstance(value, list):
                valid_values = [v for v in value if v in allowed_accords]
                invalid_values = [v for v in value if v not in allowed_accords]
                if invalid_values:
                    dropped_items["strategy_filters"][f"{key}_invalid_values"] = invalid_values
                if valid_values:
                    sanitized_strategy[key] = valid_values
            elif value in allowed_accords:
                sanitized_strategy[key] = value
            else:
                dropped_items["strategy_filters"][key] = value
    
    if dropped_items["hard_filters"] or dropped_items["strategy_filters"]:
        logger.warning(f"Dropped filters: {dropped_items}")
    
    return sanitized_hard, sanitized_strategy, dropped_items


async def smart_search_with_retry_async(
    h_filters: dict, s_filters: dict, exclude_ids: list = None, query_text: str = ""
):
    sanitized_hard, sanitized_strategy, dropped_items = sanitize_filters(h_filters, s_filters)
    
    priority_order = ["note", "accord", "occasion"]
    active_keys = [k for k in priority_order if k in sanitized_strategy and sanitized_strategy[k]]

    results = await advanced_perfume_search_tool.ainvoke(
        {
            "hard_filters": sanitized_hard,
            "strategy_filters": sanitized_strategy,
            "exclude_ids": exclude_ids,
            "query_text": query_text,
        }
    )
    if results:
        return results, "Perfect Match"

    for r in range(len(active_keys) - 1, 0, -1):
        for combo_keys in itertools.combinations(active_keys, r):
            temp_filters = {k: sanitized_strategy[k] for k in combo_keys}
            results = await advanced_perfume_search_tool.ainvoke(
                {
                    "hard_filters": sanitized_hard,
                    "strategy_filters": temp_filters,
                    "exclude_ids": exclude_ids,
                    "query_text": query_text,
                }
            )
            if results:
                return results, f"Relaxed (Level {len(active_keys)-r})"
    return [], "No Results"


async def call_info_graph_wrapper(state: AgentState):
    """Sub-Graph Wrapper"""
    current_query = state.get("user_query", "")

    if not current_query and state.get("messages"):
        last_msg = state["messages"][-1]
        if isinstance(last_msg, HumanMessage):
            current_query = last_msg.content

    subgraph_input = {
        "user_query": current_query,
        "messages": state.get("messages", []),
        "user_mode": state.get("user_mode", "BEGINNER"),
    }

    try:
        result = await info_graph.ainvoke(subgraph_input)
        return {"messages": result.get("messages", [])}

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"messages": [AIMessage(content="정보 검색 중 오류가 발생했습니다.")]}


# ==========================================
# 3. Node Functions
# ==========================================


def supervisor_node(state: AgentState):
    """[Main Router]"""
    print("\n" + "=" * 60, flush=True)
    print("👀 [Supervisor] 사용자 의도 분류 중...", flush=True)

    if state.get("active_mode") == "interviewer":
        print("   👉 인터뷰 진행 중 -> Interviewer로 이동", flush=True)
        return {"next_step": "interviewer"}

    messages = [SystemMessage(content=SUPERVISOR_PROMPT)] + state["messages"]

    try:
        decision = SMART_LLM.with_structured_output(RoutingDecision).invoke(messages)
        next_step = decision.next_step
        print(f"   👉 분류 결과: {next_step}", flush=True)
        return {"next_step": next_step}

    except Exception as e:
        print(f"   ⚠️ 분류 실패(Error): {e} -> 기본값 Writer로 이동", flush=True)
        return {"next_step": "writer"}


def interviewer_node(state: AgentState):
    """[Interviewer]"""
    current_prefs = state.get("user_preferences", {})
    question_count = state.get("question_count", 0)
    
    # 질문 횟수 증가
    question_count += 1
    
    # 거부 키워드 감지
    rejection_keywords = ["몰라", "아무거나", "그냥 추천", "빨리", "모르겠", "상관없"]
    user_message = state["messages"][-1].content.lower() if state["messages"] else ""
    is_rejection = any(keyword in user_message for keyword in rejection_keywords)
    
    # 질문 상한 또는 거부 감지 시 폴백 트리거
    should_fallback = (question_count >= 3) or (question_count >= 2 and is_rejection)
    
    if should_fallback:
        # 폴백: 기본값으로 채우기
        fallback_prefs = {
            **current_prefs,
            "gender": current_prefs.get("gender", "Unisex"),
            "season": current_prefs.get("season", "All"),
            "style": current_prefs.get("style", "Daily"),
            "target": current_prefs.get("target", "일반"),
        }
        
        print(
            f"      ⚠️ [Fallback] 질문 상한 도달 또는 거부 감지. 기본값으로 추천 진행: {json.dumps(fallback_prefs, ensure_ascii=False)}",
            flush=True,
        )
        
        return {
            "next_step": "researcher",
            "user_preferences": fallback_prefs,
            "status": "정보를 바탕으로 추천을 준비합니다...",
            "active_mode": None,
            "question_count": question_count,
            "fallback_triggered": True,
        }

    # 현재 정보를 문자열로 변환
    current_context_str = json.dumps(current_prefs, ensure_ascii=False)

    # [★수정] 여기서 CURRENT_CONTEXT만 채워주면 됩니다! (SUFFICIENCY_CRITERIA는 이미 들어있음)
    try:
        formatted_prompt = INTERVIEWER_PROMPT.format(
            CURRENT_CONTEXT=current_context_str
        )
    except Exception as e:
        # 혹시라도 포맷팅 에러가 나면 원본 프롬프트를 사용하여 멈추지 않게 함
        print(f"⚠️ Prompt Formatting Error: {e}")
        formatted_prompt = INTERVIEWER_PROMPT.replace(
            "{{CURRENT_CONTEXT}}", "정보 없음"
        )

    messages = [SystemMessage(content=formatted_prompt)] + state["messages"]

    try:
        result = SMART_LLM.with_structured_output(InterviewResult).invoke(messages)
        new_prefs = result.user_preferences.dict(exclude_unset=True)
        updated_prefs = {
            **current_prefs,
            **{k: v for k, v in new_prefs.items() if v is not None},
        }

        if result.is_sufficient:
            print(
                f"      ✅ [Handover] 정보 확보 완료! Researcher로 전달: {json.dumps(updated_prefs, ensure_ascii=False)}",
                flush=True,
            )
            return {
                "next_step": "researcher",
                "user_preferences": updated_prefs,
                "status": "모든 정보가 확인되었습니다. 추천 전략을 수립합니다...",
                "active_mode": None,
                "question_count": question_count,
                "fallback_triggered": False,
            }

        return {
            "messages": [AIMessage(content=result.response_message)],
            "user_preferences": updated_prefs,
            "active_mode": "interviewer",
            "next_step": "end",
            "question_count": question_count,
            "fallback_triggered": False,
        }
    except Exception as e:
        print(f"Interviewer Error: {e}")
        return {"next_step": "writer", "question_count": question_count, "fallback_triggered": False}


# ==========================================
# [REMOVED] Old researcher_node and writer_node
# These have been replaced by parallel_reco_node which consolidates
# both functionalities with FCFS streaming.
# ==========================================


async def parallel_reco_node(state: AgentState):
    member_id = state.get("member_id", 0)
    user_prefs = state.get("user_preferences", {})
    current_context = json.dumps(user_prefs, ensure_ascii=False)

    plan_llm = SMART_LLM.with_structured_output(SearchStrategyPlan)
    
    # [★추가] 세션 레벨 추천 다양성: 이전 추천 이력 로드
    recommended_history = state.get("recommended_history", [])
    exclude_ids = set(recommended_history)  # 세션 히스토리 제외
    
    seen_ids = set()  # 현재 배치 내 중복 제거
    brand_counts = {}  # 현재 배치 내 브랜드 다양성 추적
    seen_ids_lock = asyncio.Lock()

    def _normalize_section_boundary(previous_text: str, next_text: str) -> str:
        if not previous_text or not next_text:
            return next_text
        if not next_text.lstrip().startswith("##"):
            return next_text
        prev_trimmed = previous_text.rstrip()
        if prev_trimmed.endswith("---") and not previous_text.endswith("\n"):
            if not next_text.startswith("\n"):
                return f"\n{next_text}"
        return next_text

    async def generate_user_label(user_prefs: dict, plan_reason: str, plan_strategy_name: str) -> str:
        """
        Generate user-friendly strategy label using LLM with denylist validation.
        
        Args:
            user_prefs: User preferences dictionary
            plan_reason: Strategy reason/intent
            plan_strategy_name: Internal strategy name (for context only)
        
        Returns:
            User-friendly label string
        """
        user_prefs_str = json.dumps(user_prefs, ensure_ascii=False)
        
        # First attempt: Generate user-friendly label
        label_messages = [
            SystemMessage(content="당신은 향수 추천 전략을 사용자 친화적인 한 문장으로 표현하는 전문가입니다."),
            HumanMessage(
                content=(
                    f"사용자 정보: {user_prefs_str}\n"
                    f"전략 의도: {plan_reason}\n\n"
                    f"위 정보를 바탕으로, 사용자에게 보여줄 전략명을 작성하세요.\n\n"
                    f"요구사항:\n"
                    f"- 한 문장으로 작성 (예: \"강인하고 자신감 있는 첫인상\", \"우아하고 세련된 분위기\")\n"
                    f"- 첫인상/무드 중심 표현 사용\n"
                    f"- 다음 단어는 절대 사용 금지: 전략, 전략적, 이미지 강조, 이미지 보완, 이미지 반전\n\n"
                    f"전략명:"
                )
            ),
        ]
        
        try:
            response = await SMART_LLM.ainvoke(label_messages, config={"tags": ["internal_helper"]})
            user_label = response.content.strip()
            
            # Validate with denylist
            if not has_forbidden_words(user_label):
                return user_label
            
            # First attempt failed validation - retry once with stronger warning
            retry_messages = [
                SystemMessage(content="당신은 향수 추천 전략을 사용자 친화적인 한 문장으로 표현하는 전문가입니다."),
                HumanMessage(
                    content=(
                        f"이전 응답에 금지어가 포함되어 있습니다.\n\n"
                        f"다시 한번 작성하세요. 절대 사용하면 안 되는 단어: 전략, 전략적, 이미지 강조, 이미지 보완, 이미지 반전\n\n"
                        f"사용자 정보: {user_prefs_str}\n"
                        f"전략 의도: {plan_reason}\n\n"
                        f"전략명:"
                    )
                ),
            ]
            
            retry_response = await SMART_LLM.ainvoke(retry_messages, config={"tags": ["internal_helper"]})
            user_label = retry_response.content.strip()
            
            # Check retry result
            if not has_forbidden_words(user_label):
                return user_label
            
        except Exception as e:
            # Log error but continue with fallback
            print(f"[WARNING] User label generation failed: {e}", flush=True)
        
        # Fallback: Use random safe label from predefined list
        return random.choice(UserFriendlyStrategyLabels.SAFE_LABELS)

    async def prepare_strategy(strategy_name: str, priority: int):
        """Phase 1: Strategy planning + search + perfume selection (parallel)"""
        plan_messages = [
            SystemMessage(content=RESEARCHER_SYSTEM_PROMPT),
            HumanMessage(
                content=(
                    f"사용자 요청 데이터: {current_context}\n"
                    f"전략 이름: {strategy_name}\n"
                    f"우선순위: {priority}\n"
                    "위 데이터를 바탕으로 전략을 수립해 주세요."
                )
            ),
        ]

        try:
            plan = await plan_llm.ainvoke(
                plan_messages, config={"tags": ["internal_helper"]}
            )
        except Exception as e:
            return None

        user_label = await generate_user_label(user_prefs, plan.reason, plan.strategy_name)

        try:
            h_filters = plan.hard_filters.model_dump(exclude_none=True)
            s_filters = plan.strategy_filters.model_dump(exclude_none=True)
        except Exception:
            h_filters = {}
            s_filters = {}

        try:
            candidates, _match_type = await smart_search_with_retry_async(
                h_filters, s_filters, exclude_ids=list(exclude_ids), query_text=plan.reason
            )
        except Exception as e:
            return None

        selected_perfume = None
        async with seen_ids_lock:
            for candidate in candidates:
                brand = candidate.get("brand", "")
                # [★추가] 브랜드 다양성: 동일 브랜드 최대 2개 제한
                if brand_counts.get(brand, 0) >= 2:
                    continue
                # 현재 배치 내 중복 확인
                if candidate["id"] not in seen_ids and candidate["id"] not in exclude_ids:
                    selected_perfume = candidate
                    seen_ids.add(candidate["id"])
                    brand_counts[brand] = brand_counts.get(brand, 0) + 1
                    break

        if not selected_perfume:
            return None

        save_recommendation_log(
            member_id=member_id, perfumes=[selected_perfume], reason=plan.reason
        )

        strategy_result = StrategyResult(
            strategy_name=plan.strategy_name,
            strategy_keyword=plan.strategy_keyword,
            strategy_reason=plan.reason,
            perfumes=[
                PerfumeDetail(
                    id=selected_perfume.get("id"),
                    perfume_name=selected_perfume.get("name"),
                    perfume_brand=selected_perfume.get("brand"),
                    accord=f"{selected_perfume.get('accords')}\n[Best Review]: {selected_perfume.get('best_review')}",
                    notes=PerfumeNotes(
                        top=selected_perfume.get("top_notes") or "N/A",
                        middle=selected_perfume.get("middle_notes") or "N/A",
                        base=selected_perfume.get("base_notes") or "N/A",
                    ),
                    image_url=selected_perfume.get("image_url"),
                    gender=selected_perfume.get("gender", "Unisex"),
                    season="All",
                    occasion="Any",
                )
            ],
        )

        section_data = {
            "user_preferences": user_prefs,
            "strategy": {
                "internal_id": plan.strategy_name,
                "user_label": user_label,
                "reason": plan.reason,
                "keywords": plan.strategy_keyword,
                "priority": priority,
            },
            "perfume": strategy_result.perfumes[0].dict(),
        }
        
        return {
            "section_data": section_data,
            "priority": priority,
        }

    async def generate_output(prepared_data: dict):
        """Phase 2: LLM output generation with streaming (sequential)"""
        if not prepared_data:
            return None
            
        section_data = prepared_data["section_data"]
        priority = prepared_data["priority"]
        
        user_mode = state.get("user_mode", "BEGINNER")
        
        # [★ Dynamic Expression Injection]
        # Extract notes and accords from perfume data
        perfume_data = section_data.get("perfume", {})
        perfume_name = perfume_data.get("name", "Unknown")
        brand = perfume_data.get("brand", "Unknown")
        notes_data = perfume_data.get("notes", {})
        accord_str = perfume_data.get("accord", "")
        
        # Collect all notes
        all_notes = []
        for note_type in ["top", "middle", "base"]:
            note_str = notes_data.get(note_type, "")
            if note_str and note_str != "N/A":
                all_notes.extend([n.strip() for n in note_str.split(",")])
        
        # Extract accords (before [Best Review])
        accords = []
        if accord_str:
            accord_part = accord_str.split("[Best Review]")[0].strip()
            accords = [a.strip() for a in accord_part.split(",") if a.strip()]
        
        # Load expression loader
        loader = ExpressionLoader()
        
        # Build expression guide
        expression_guide = []
        injected_count = 0
        
        if all_notes:
            expression_guide.append("### 노트 표현 가이드")
            for note in all_notes[:10]:  # Limit to 10 to avoid prompt bloat
                desc = loader.get_note_desc(note)
                if desc:
                    expression_guide.append(f"- {note}: {desc}")
                    injected_count += 1
        
        if accords:
            expression_guide.append("\n### 어코드 표현 가이드")
            for accord in accords[:10]:
                desc = loader.get_accord_desc(accord)
                if desc:
                    expression_guide.append(f"- {accord}: {desc}")
                    injected_count += 1
        
        expression_text = "\n".join(expression_guide) if expression_guide else ""
        
        data_ctx = json.dumps(section_data, ensure_ascii=False, indent=2)

        if user_mode == "EXPERT":
            section_system = WRITER_RECOMMENDATION_PROMPT_EXPERT_SINGLE
        else:
            section_system = WRITER_RECOMMENDATION_PROMPT_SINGLE

        # Inject expression guide into prompt
        content_parts = [
            f"[섹션 번호]: {priority}",
            f"[도입부 포함]: {'예' if priority == 1 else '아니오'}",
            f"[출력 규칙]: 도입부 포함이 '아니오'이면 첫 줄을 반드시 '## {priority}.'로 시작하고 도입부 문장을 쓰지 마세요.",
        ]
        
        if expression_text:
            content_parts.append(f"\n[감각 표현 참고]:\n{expression_text}")
        
        content_parts.append(f"\n[참고 데이터]:\n{data_ctx}")
        
        messages = [SystemMessage(content=section_system)] + state["messages"] + [
            HumanMessage(content="\n".join(content_parts))
        ]

        try:
            result_text = ""
            async for chunk in SUPER_SMART_LLM.astream(messages):
                if chunk.content:
                    result_text += chunk.content
            
            if result_text:
                header_index = result_text.find("##")
                if priority != 1 and header_index > 0:
                    result_text = result_text[header_index:]
                if result_text.startswith("##"):
                    lines = result_text.splitlines()
                    header_line = lines[0]
                    after = header_line[2:].lstrip()
                    idx = 0
                    while idx < len(after) and after[idx].isdigit():
                        idx += 1
                    if idx < len(after) and after[idx] == ".":
                        idx += 1
                    if idx < len(after) and after[idx] == " ":
                        idx += 1
                    rest = after[idx:]
                    lines[0] = (
                        f"## {priority}. {rest}" if rest else f"## {priority}."
                    )
                    result_text = "\n".join(lines)
            if result_text and not result_text.rstrip().endswith("---"):
                result_text = f"{result_text.rstrip()}\n---"
            return result_text
        except Exception as e:
            return None

    # Phase 1: Parallel preparation (strategy planning + search)
    # All 3 strategies run simultaneously - fast!
    prep_tasks = [
        asyncio.create_task(prepare_strategy("STRAT_1", 1)),
        asyncio.create_task(prepare_strategy("STRAT_2", 2)),
        asyncio.create_task(prepare_strategy("STRAT_3", 3)),
    ]

    # Phase 2: Sequential output generation with streaming
    # Wait for prep in order, then generate output with streaming
    results = []
    prepared_data_list = []  # [★추가] 추천 이력 누적용
    try:
        data1 = await prep_tasks[0]
        prepared_data_list.append(data1)
        result1 = await generate_output(data1) if data1 else None
        results.append(result1)

        data2 = await prep_tasks[1]
        prepared_data_list.append(data2)
        result2 = await generate_output(data2) if data2 else None
        results.append(result2)

        data3 = await prep_tasks[2]
        prepared_data_list.append(data3)
        result3 = await generate_output(data3) if data3 else None
        results.append(result3)
    except (Exception, asyncio.CancelledError) as e:
        return {
            "messages": [AIMessage(content="조건에 맞는 향수를 찾지 못했습니다. 😢")],
            "next_step": "end",
        }

    # Assemble sections in order (1 → 2 → 3)
    full_text = ""
    for idx, result_text in enumerate(results, start=1):
        # Handle exceptions returned by gather(return_exceptions=True)
        if isinstance(result_text, (Exception, asyncio.CancelledError)):
            continue

        if not result_text:
            continue

        if full_text:
            full_text = f"{full_text}\n\n{result_text}"
        else:
            full_text = result_text

    if not full_text:
        full_text = "조건에 맞는 향수를 찾지 못했습니다. 😢 대안을 안내해 드릴게요..."

    # [★추가] 현재 배치에서 추천된 향수 ID 수집 및 세션 히스토리 업데이트
    current_batch_ids = []
    for prepared_data in prepared_data_list:
        if prepared_data and prepared_data.get("section_data"):
            perfume_id = prepared_data["section_data"].get("perfume", {}).get("id")
            if perfume_id:
                current_batch_ids.append(perfume_id)
    
    updated_history = recommended_history + current_batch_ids

    return {
        "messages": [AIMessage(content=full_text)],
        "next_step": "end",
        "recommended_history": updated_history,
    }


# ==========================================
# 4. Graph Build
# ==========================================
workflow = StateGraph(AgentState)

workflow.add_node("supervisor", supervisor_node)
workflow.add_node("interviewer", interviewer_node)
# workflow.add_node("researcher", researcher_node)  # Replaced by parallel_reco
# workflow.add_node("writer", writer_node)  # Replaced by parallel_reco
workflow.add_node("parallel_reco", parallel_reco_node)
workflow.add_node("info_retrieval_subgraph", call_info_graph_wrapper)

workflow.add_edge(START, "supervisor")

workflow.add_conditional_edges(
    "supervisor",
    lambda x: x["next_step"],
    {
        "interviewer": "interviewer",
        "info_retrieval": "info_retrieval_subgraph",
        "writer": "parallel_reco",  # Replaced writer with parallel_reco
    },
)

workflow.add_conditional_edges(
    "interviewer",
    lambda x: x["next_step"],
    {"end": END, "researcher": "parallel_reco", "writer": "parallel_reco"},
)

# workflow.add_edge("researcher", "writer")  # Old flow - replaced
# workflow.add_edge("writer", END)  # Old flow - replaced
workflow.add_edge("parallel_reco", END)
workflow.add_edge("info_retrieval_subgraph", END)

checkpointer = MemorySaver()
app_graph = workflow.compile(checkpointer=checkpointer)