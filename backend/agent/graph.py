# backend/agent/graph.py
import os
import json
import asyncio
import itertools
import random
import uuid
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
from .brand_exclusion_parser import parse_brand_exclusions, should_clear_brand_fields

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

from .followup_classifier import classify_followup
from .personalization import get_personalization_summary
from .use_case_utils import infer_use_case

# [정보 검색 전용 서브 그래프 임포트]
from .graph_info import info_graph

load_dotenv()

import logging

logger = logging.getLogger(__name__)

# ==========================================
# 0. Helper Functions
# ==========================================
def parse_recommended_count(query: str) -> int | None:
    """Parse 'N개' from user query."""
    if not query:
        return None
    import re
    # Map words to numbers
    word_map = {"한": 1, "두": 2, "세": 3, "네": 4, "다섯": 5}
    match_word = re.search(r"(한|두|세|네|다섯)\s*개", query)
    match_digit = re.search(r"(\d+)\s*개", query)
    
    if match_digit:
        return int(match_digit.group(1))
    elif match_word:
        return word_map.get(match_word.group(1))
    return None

def normalize_recommended_count(count: int) -> int:
    """Normalize recommendation count to be between 1 and 5."""
    if count is None:
        return 3
    return max(1, min(count, 5))

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
    h_filters: dict, s_filters: dict, exclude_ids: list = None, query_text: str = "", rank_mode: str = "DEFAULT"
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
            "rank_mode": rank_mode,
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
                    "rank_mode": rank_mode,
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
        
        # [Wave 2-4] Map info_status to chat_outcome_status
        info_status = result.get("info_status", "OK")
        
        return {
            "messages": result.get("messages", []),
            "chat_outcome_status": info_status,  # OK/NO_RESULTS/ERROR 직접 매핑
            "chat_outcome_reason_code": f"info_{info_status.lower()}",
            "chat_outcome_reason_detail": f"Info graph completed with status: {info_status}",
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        
        # [Wave 2-4] Set ERROR status on exception
        return {
            "messages": [AIMessage(content="정보 검색 중 오류가 발생했습니다.")],
            "chat_outcome_status": "ERROR",
            "chat_outcome_reason_code": "info_exception",
            "chat_outcome_reason_detail": f"Info graph exception: {str(e)[:100]}",
        }


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
    current_prefs = state.get("user_preferences") or {}
    if isinstance(current_prefs, UserPreferences):
        current_prefs = current_prefs.model_dump(exclude_none=True)
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
        fallback_frame_id = state.get("frame_id") or str(uuid.uuid4())
        
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
            "frame_id": fallback_frame_id,
            "recommended_history": state.get("recommended_history", []),
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
        interview_result = SMART_LLM.with_structured_output(InterviewResult).invoke(messages)

        current_query = state.get("user_query", "")
        recent_messages = state.get("messages", [])[-5:]
        if not current_query and state.get("messages"):
            last_msg = state["messages"][-1]
            if isinstance(last_msg, HumanMessage):
                current_query = last_msg.content

        classification = classify_followup(
            current_query=current_query,
            recent_messages=recent_messages,
            current_constraints=current_prefs,
        )

        # [★추가] 브랜드 제외 파싱
        exclude_brands, has_exclusion = parse_brand_exclusions(current_query)
        if has_exclusion:
            print(
                f"🚫 [Exclusion] Detected exclude_brands: {exclude_brands}",
                flush=True,
            )

        current_frame_id = state.get("frame_id")
        if classification.intent in ["NEW_RECO", "RESET"]:
            frame_id = str(uuid.uuid4())
            new_recommended_history = []
            print(
                f"🔄 [Frame] New frame created: {frame_id[:8]}... (intent={classification.intent})",
                flush=True,
            )
            print("🗑️  [History] Recommended history cleared (new frame)", flush=True)
        else:
            frame_id = current_frame_id or str(uuid.uuid4())
            new_recommended_history = None
            print(
                f"✅ [Frame] Frame maintained: {frame_id[:8] if frame_id else 'new'}... (intent={classification.intent})",
                flush=True,
            )

        merged_prefs: Dict[str, Any] = {}
        for slot in classification.keep_slots:
            if current_prefs and slot in current_prefs and current_prefs[slot] is not None:
                merged_prefs[slot] = current_prefs[slot]

        new_prefs = interview_result.user_preferences
        for key, value in new_prefs.model_dump(exclude_none=True).items():
            merged_prefs[key] = value

        # [★추가] 브랜드 제외 처리
        if has_exclusion:
            merged_prefs["exclude_brands"] = exclude_brands
            # 제외 브랜드가 있으면 brand, reference_brand 클리어
            if should_clear_brand_fields(exclude_brands):
                merged_prefs["brand"] = None
                merged_prefs["reference_brand"] = None
                print(
                    f"   → brand/reference_brand cleared due to exclusions",
                    flush=True,
                )

        for slot in classification.drop_slots:
            if slot not in merged_prefs:
                merged_prefs[slot] = None

        print(
            f"📋 [Merge] Keep: {classification.keep_slots}, Drop: {classification.drop_slots}",
            flush=True,
        )
        print(f"📋 [Merge] Result: {list(merged_prefs.keys())}", flush=True)

        state["user_preferences"] = merged_prefs
        # [★추가] recommended_count를 state 최상위로 올림 (parallel_reco_node에서 사용)
        if merged_prefs.get("recommended_count"):
            state["recommended_count"] = merged_prefs["recommended_count"]

        if interview_result.is_sufficient:
            print(
                f"      ✅ [Handover] 정보 확보 완료! Researcher로 전달: {json.dumps(merged_prefs, ensure_ascii=False)}",
                flush=True,
            )
            return {
                "next_step": "researcher",
                "user_preferences": merged_prefs,
                "recommended_count": merged_prefs.get("recommended_count"),  # [★수정] 반환값에 명시적으로 포함
                "status": "모든 정보가 확인되었습니다. 추천 전략을 수립합니다...",
                "active_mode": None,
                "question_count": question_count,
                "fallback_triggered": False,
                "frame_id": frame_id,
                "recommended_history": new_recommended_history if new_recommended_history is not None else state.get("recommended_history", []),
            }

        return {
            "messages": [AIMessage(content=interview_result.response_message)],
            "user_preferences": merged_prefs,
            "recommended_count": merged_prefs.get("recommended_count"),  # [★수정] 반환값에 명시적으로 포함
            "active_mode": "interviewer",
            "next_step": "end",
            "question_count": question_count,
            "fallback_triggered": False,
            "frame_id": frame_id,
            "recommended_history": new_recommended_history if new_recommended_history is not None else state.get("recommended_history", []),
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

    # [★추가] Infer use case (SELF vs GIFT)
    use_case = infer_use_case(user_prefs)
    
    # [★수정] Personalization gate: only apply for SELF use case with logged-in member
    personalization = {}
    if use_case == 'SELF' and member_id > 0:
        personalization = get_personalization_summary(member_id) or {}
        if personalization.get("summary_text"):
            print(f"🎯 [Personalization] {personalization['summary_text']}", flush=True)
    else:
        if use_case == 'GIFT':
            print(f"🎁 [GIFT Mode] Personalization disabled for gift recommendations", flush=True)

    researcher_prompt = RESEARCHER_SYSTEM_PROMPT
    if personalization.get("summary_text"):
        researcher_prompt += (
            "\n\n## 사용자 취향 정보\n"
            f"{personalization['summary_text']}\n\n"
            "이 정보를 참고하되, 현재 요청 조건(브랜드/계절/대상 등)이 최우선입니다."
        )

    plan_llm = SMART_LLM.with_structured_output(SearchStrategyPlan)
    
    # [★추가] 세션 레벨 추천 다양성: 이전 추천 이력 로드
    recommended_history = state.get("recommended_history", [])
    exclude_ids = recommended_history.copy()  # 세션 히스토리 제외 (SELF/GIFT 공통)

    # [★수정] Add disliked perfumes only for SELF use case
    if use_case == 'SELF':
        for disliked in personalization.get("disliked_perfumes", []):
            perfume_id = disliked.get("id")
            if perfume_id:
                exclude_ids.append(perfume_id)

    exclude_id_set = set(exclude_ids)
    
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

    async def prepare_strategy(strategy_name: str, priority: int, rank_mode: str):
        """Phase 1: Strategy planning + search + perfume selection (parallel)"""
        plan_messages = [
            SystemMessage(content=researcher_prompt),
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
            return {
                "error": True,
                "error_type": "llm_error",
                "error_detail": str(e),
                "section_data": None,
                "priority": priority,
            }

        user_label = await generate_user_label(user_prefs, plan.reason, plan.strategy_name)

        try:
            h_filters = plan.hard_filters.model_dump(exclude_none=True)
            s_filters = plan.strategy_filters.model_dump(exclude_none=True)
        except Exception:
            h_filters = {}
            s_filters = {}

        try:
            candidates, _match_type = await smart_search_with_retry_async(
                h_filters, s_filters, exclude_ids=exclude_ids, query_text=plan.reason, rank_mode=rank_mode
            )
        except Exception as e:
            return {
                "error": True,
                "error_type": "tool_error",
                "error_detail": str(e),
                "section_data": None,
                "priority": priority,
            }

        selected_perfume = None
        async with seen_ids_lock:
            # [★수정] 사용자가 특정 브랜드를 명시한 경우 브랜드 다양성 제한 해제
            user_requested_brand = user_prefs.get("brand") or user_prefs.get("reference_brand")
            
            for candidate in candidates:
                brand = candidate.get("brand", "")
                # [★추가] 브랜드 다양성: 사용자가 브랜드를 지정하지 않았을 때만 동일 브랜드 최대 2개 제한
                if not user_requested_brand:
                    if brand_counts.get(brand, 0) >= 2:
                        continue
                # 현재 배치 내 중복 확인
                if candidate["id"] not in seen_ids and candidate["id"] not in exclude_id_set:
                    selected_perfume = candidate
                    seen_ids.add(candidate["id"])
                    brand_counts[brand] = brand_counts.get(brand, 0) + 1
                    break

        if not selected_perfume:
            return {
                "error": True,
                "error_type": "no_candidates",
                "error_detail": "No candidates selected",
                "section_data": None,
                "priority": priority,
            }

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

    async def generate_output(prepared_data: dict, display_priority: int = None):
        """Phase 2: LLM output generation with streaming (sequential)"""
        if not prepared_data:
            return None
            
        section_data = prepared_data["section_data"]
        # Use display_priority if provided (for contiguous numbering), else fallback to original priority
        priority = display_priority if display_priority is not None else prepared_data["priority"]
        
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
    
    # [Task D1] 트렌딩 키워드 감지
    rank_mode = "DEFAULT"
    user_query = state.get("user_query", "")
    trending_keywords = ["유행", "인기", "트렌딩", "요즘", "잘나가는", "베스트", "trending", "popular", "hot"]
    if any(k in user_query for k in trending_keywords):
        rank_mode = "POPULAR"
        print(f"🔥 [Ranking] Mode: {rank_mode}", flush=True)
    
    # [Task C1] Determine target recommended count (Default: 3)
    target_count = state.get("recommended_count")
    if target_count is None:
        # Try to parse from user_query using helper
        parsed = parse_recommended_count(state.get("user_query", ""))
        target_count = parsed if parsed is not None else 3
    
    # Cap target_count reasonably (e.g. 1 to 5)
    target_count = normalize_recommended_count(target_count)
    
    print(f"🔢 [Count] Target recommendations: {target_count}", flush=True)

    # [Task C2] Dynamic Strategy Generation Loop
    prep_tasks = []
    for i in range(1, target_count + 1):
        prep_tasks.append(asyncio.create_task(prepare_strategy(f"STRAT_{i}", i, rank_mode)))

    # Phase 2: Sequential output generation with streaming
    # Wait for prep in order, then generate output with streaming
    # results = []
    # prepared_data_list = []  # [★추가] 추천 이력 누적용
    
    # 1. Gather all preparation tasks (ignoring exceptions during gather, handling them later)
    results = await asyncio.gather(*prep_tasks, return_exceptions=True)
    
    valid_data_list = []
    
    # 2. Filter out failures (None, Exception, or error dict)
    for res in results:
        if isinstance(res, Exception):
            logger.error(f"Strategy preparation failed: {res}")
            continue
        if res is None:
            continue
        if isinstance(res, dict) and res.get("error"):
            continue
        valid_data_list.append(res)
        
    # 3. Generate output for VALID results only, with CONTIGUOUS numbering
    final_output_texts = []
    prepared_data_list = [] # For history tracking
    
    for idx, data in enumerate(valid_data_list, start=1):
        # Pass the new sequential priority (idx) to generate_output
        # This ensures outputs are labeled ## 1., ## 2., etc. regardless of original priority
        output_text = await generate_output(data, display_priority=idx)
        
        if output_text:
            final_output_texts.append(output_text)
            prepared_data_list.append(data)
            
    # 4. Assemble full text
    if final_output_texts:
        full_text = "\n\n".join(final_output_texts)
    else:
        # Dynamic fallback generation
        fallback_messages = [
            SystemMessage(content=WRITER_FAILURE_PROMPT),
            HumanMessage(content=f"사용자 정보: {current_context}")
        ]
        fallback_response = await SUPER_SMART_LLM.ainvoke(fallback_messages)
        full_text = fallback_response.content

    # [★추가] 결과 상태 분류 (Wave 2-2)
    errors_encountered = []
    for res in results:
        if isinstance(res, Exception):
            errors_encountered.append({"type": "exception", "detail": str(res)})
        elif isinstance(res, dict) and res.get("error"):
            errors_encountered.append({
                "type": res.get("error_type"),
                "detail": res.get("error_detail"),
            })

    if len(final_output_texts) >= 1:
        chat_outcome_status = "OK"
        if len(final_output_texts) < target_count:
            chat_outcome_reason_code = "partial_results"
            chat_outcome_reason_detail = (
                f"Generated {len(final_output_texts)}/{target_count} sections"
            )
        else:
            chat_outcome_reason_code = "success"
            chat_outcome_reason_detail = (
                f"Generated {len(final_output_texts)}/{target_count} sections"
            )
    elif errors_encountered:
        chat_outcome_status = "ERROR"
        chat_outcome_reason_code = errors_encountered[0]["type"]
        chat_outcome_reason_detail = (
            f"{len(errors_encountered)} errors: {errors_encountered[0]['detail'][:100]}"
        )
    else:
        chat_outcome_status = "NO_RESULTS"
        chat_outcome_reason_code = "no_candidates"
        chat_outcome_reason_detail = "All strategies failed to find suitable perfumes"

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
        "user_preferences": user_prefs,
        "chat_outcome_status": chat_outcome_status,
        "chat_outcome_reason_code": chat_outcome_reason_code,
        "chat_outcome_reason_detail": chat_outcome_reason_detail,
    }


def parallel_reco_result_router(state: AgentState):
    """
    chat_outcome_status 값에 따라 다음 노드로 라우팅합니다.
    
    Returns:
        다음 노드 이름 ('parallel_reco_ok_writer' | 'parallel_reco_no_results' | 'parallel_reco_error')
    """
    status = state.get("chat_outcome_status", "OK")
    
    print(f"\n🔀 [Reco Router] Status: {status}", flush=True)
    
    if status == "NO_RESULTS":
        return "parallel_reco_no_results"
    elif status == "ERROR":
        return "parallel_reco_error"
    else:
        return "parallel_reco_ok_writer"


async def parallel_reco_ok_writer(state: AgentState):
    """
    OK 상태일 때 - 이미 parallel_reco_node에서 메시지 생성 완료.
    추가 처리 없이 그대로 반환.
    """
    print(f"\n✅ [Reco OK Writer] 정상 추천 완료", flush=True)
    return {}


async def parallel_reco_no_results(state: AgentState):
    """
    NO_RESULTS 상태일 때 - WRITER_FAILURE_PROMPT 사용하여 대안 제시.
    """
    print(f"\n⚠️ [Reco No Results] 검색 결과 없음 처리", flush=True)
    
    user_prefs = state.get("user_preferences", {})
    current_context = json.dumps(user_prefs, ensure_ascii=False)
    
    fallback_messages = [
        SystemMessage(content=WRITER_FAILURE_PROMPT),
        HumanMessage(content=f"사용자 정보: {current_context}")
    ]
    
    fallback_response = await SUPER_SMART_LLM.ainvoke(fallback_messages)
    
    return {"messages": [AIMessage(content=fallback_response.content)]}


async def parallel_reco_error(state: AgentState):
    """
    ERROR 상태일 때 - 고정 문구 출력 (내부 오류 노출 금지).
    """
    print(f"\n❌ [Reco Error] 기술적 오류 처리", flush=True)
    
    error_msg = "죄송합니다. 현재 알 수 없는 오류가 발생하였습니다. 잠시 후 다시 시도해 주세요. 🙏"
    
    return {"messages": [AIMessage(content=error_msg)]}


# ==========================================
# 4. Graph Build
# ==========================================
workflow = StateGraph(AgentState)

workflow.add_node("supervisor", supervisor_node)
workflow.add_node("interviewer", interviewer_node)
# workflow.add_node("researcher", researcher_node)  # Replaced by parallel_reco
# workflow.add_node("writer", writer_node)  # Replaced by parallel_reco
workflow.add_node("parallel_reco", parallel_reco_node)

# [Wave 2-3] Add status-based routing nodes
workflow.add_node("parallel_reco_result_router", parallel_reco_result_router)
workflow.add_node("parallel_reco_ok_writer", parallel_reco_ok_writer)
workflow.add_node("parallel_reco_no_results", parallel_reco_no_results)
workflow.add_node("parallel_reco_error", parallel_reco_error)
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

# [Wave 2-3] Route parallel_reco → router → status-specific nodes
workflow.add_edge("parallel_reco", "parallel_reco_result_router")

workflow.add_conditional_edges(
    "parallel_reco_result_router",
    lambda x: parallel_reco_result_router(x),
    {
        "parallel_reco_ok_writer": "parallel_reco_ok_writer",
        "parallel_reco_no_results": "parallel_reco_no_results",
        "parallel_reco_error": "parallel_reco_error",
    },
)

# [Wave 2-3] All status nodes → END
workflow.add_edge("parallel_reco_ok_writer", END)
workflow.add_edge("parallel_reco_no_results", END)
workflow.add_edge("parallel_reco_error", END)
workflow.add_edge("info_retrieval_subgraph", END)

checkpointer = MemorySaver()
app_graph = workflow.compile(checkpointer=checkpointer)
