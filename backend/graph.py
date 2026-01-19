import os
import json
import traceback
from typing import Literal, List, Dict, Any, Optional

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

# [Import] 로컬 모듈 - schemas.py에서 정의한 모든 클래스를 가져옵니다.
from schemas import (
    AgentState,
    UserPreferences,
    # --- 인터뷰 및 라우팅 관련 추가 ---
    InterviewResult,  # supervisor와 interviewer에서 LLM 응답을 구조화할 때 필요합니다.
    RoutingDecision,  # (선택 사항) 라우팅 로직을 구조화할 때 사용합니다.
    # --- 리서처 전략 및 필터 관련 추가 ---
    ResearchActionPlan,  # 리서처가 3대 전략을 세울 때 사용하는 최상위 스키마입니다.
    SearchStrategyPlan,  # 개별 검색 전략의 상세 구조입니다.
    HardFilters,  # 리서처 노드 내에서 하드 필터 데이터를 다룰 때 필요합니다.
    StrategyFilters,  # 리서처 노드 내에서 전략 필터 데이터를 다룰 때 필요합니다.
    # --- 리서처 결과 및 출력 관련 ---
    ResearcherOutput,
    StrategyResult,
    PerfumeDetail,
    PerfumeNotes,
)

# [수정] database 함수 대신 tools의 도구 객체를 임포트합니다.
from tools import (
    lookup_note_by_string_tool,
    lookup_note_by_vector_tool,
    search_perfumes_tool,
)
from prompts import (
    SUPERVISOR_PROMPT,
    INTERVIEWER_PROMPT,
    RESEARCHER_SYSTEM_PROMPT,
    WRITER_FAILURE_PROMPT,
    WRITER_CHAT_PROMPT,
    WRITER_RECOMMENDATION_PROMPT,
    NOTE_SELECTION_PROMPT,
)

load_dotenv()

# ==========================================
# 1. 모델 설정
# ==========================================
FAST_LLM = ChatOpenAI(model="gpt-4o-mini", temperature=0)
SMART_LLM = ChatOpenAI(model="gpt-4o", temperature=0)
SUPER_SMART_LLM = ChatOpenAI(model="gpt-5.2", temperature=0)


# ==========================================
# 3. Node Functions
# ==========================================
def supervisor_node(state: AgentState):
    print("\n" + "=" * 60, flush=True)
    print("👀 [Supervisor] 대화 분석 및 정보 추출 중...", flush=True)

    # 1. 기존에 수집된 정보 가져오기 (휘발 방지)
    current_prefs = state.get("user_preferences", {})

    # 2. 이미 인터뷰 모드라면 바로 인터뷰어로 토스
    if state.get("active_mode") == "interviewer":
        print("   -> ⏩ Active Mode: Interviewer 유지", flush=True)
        return {"next_step": "interviewer"}

    # 3. 인터뷰어와 동일한 프롬프트 및 스키마를 사용하여 정보 추출
    # Supervisor 단계에서 정보를 추출해야 Researcher가 빈 값을 받지 않습니다.
    messages = [SystemMessage(content=INTERVIEWER_PROMPT)] + state["messages"]

    try:
        # 정밀한 정보 추출을 위해 SMART_LLM(gpt-4o)을 사용합니다.
        result = SMART_LLM.with_structured_output(InterviewResult).invoke(messages)

        # 4. 정보 업데이트 및 병합
        new_prefs = result.user_preferences.dict(exclude_unset=True)
        updated_prefs = {
            **current_prefs,
            **{k: v for k, v in new_prefs.items() if v is not None},
        }

        # 5. 라우팅 판단
        # [Case A] 향수와 관련 없는 잡담인 경우
        if result.is_off_topic:
            print(f"   -> 🎯 결정된 경로: WRITER (Off-topic)", flush=True)
            return {"next_step": "writer", "active_mode": None}

        # [Case B] 필수 정보(Target + Concept)가 충족된 경우 -> 바로 검색
        if result.is_sufficient:
            print(f"   -> 🎯 결정된 경로: RESEARCHER (정보 충족)", flush=True)
            print(
                f"      수집 정보: {json.dumps(updated_prefs, ensure_ascii=False)}",
                flush=True,
            )
            return {
                "next_step": "researcher",
                "user_preferences": updated_prefs,
                "active_mode": None,
            }

        # [Case C] 정보가 더 필요한 경우 -> Interviewer에게 전달
        else:
            print(f"   -> 🎯 결정된 경로: INTERVIEWER (추가 질문 필요)", flush=True)
            return {
                "next_step": "interviewer",
                "user_preferences": updated_prefs,
                "active_mode": "interviewer",
            }

    except Exception as e:
        print(f"   -> ⚠️ Supervisor Error: {e}")
        # 에러 발생 시 안전하게 인터뷰어 단계로 보냅니다.
        return {"next_step": "interviewer"}


# ==========================================
# 4. Interviewer 노드 정의
# ==========================================


def interviewer_node(state: AgentState):
    print(f"\n🎤 [Interviewer] 정보 분석 중...", flush=True)
    current_prefs = state.get("user_preferences", {})
    current_prefs_str = (
        json.dumps(current_prefs, ensure_ascii=False, indent=2)
        if current_prefs
        else "없음"
    )

    augmented_prompt = f"""
    {INTERVIEWER_PROMPT}
    [★Context★] 이전 수집 정보: {current_prefs_str}
    """
    messages = [SystemMessage(content=augmented_prompt)] + state["messages"]

    try:
        result = SMART_LLM.with_structured_output(InterviewResult).invoke(messages)
        print(
            f"   -> 📊 판단: 충족({result.is_sufficient}), 잡담({result.is_off_topic})",
            flush=True,
        )

        if result.is_off_topic:
            return {"active_mode": None, "next_step": "writer"}

        if result.is_sufficient:
            print("   -> 🚀 정보 충족! Researcher 호출", flush=True)
            return {
                "messages": [AIMessage(content=result.response_message)],
                "user_preferences": result.user_preferences.dict(),
                "active_mode": None,
                "next_step": "researcher",
            }
        else:
            print("   -> ❓ 정보 부족", flush=True)
            print("현재 수집된 사용자 정보 :", result.user_preferences.dict())
            return {
                "messages": [AIMessage(content=result.response_message)],
                "user_preferences": result.user_preferences.dict(),
                "active_mode": "interviewer",
                "next_step": "end",
            }
    except Exception as e:
        print(f"   -> ⚠️ Error: {e}")
        return {"active_mode": None, "next_step": "writer"}


# ==========================================
# 5. Researcher에 사용될 기능함수 정의
# ==========================================
def log_filters(h_filters: dict, s_filters: dict):
    # [수정] Hard Filters에 담긴 모든 요소를 동적으로 출력합니다.
    hard_items = []
    for k, v in h_filters.items():
        if v:
            hard_items.append(f"{k.capitalize()}: {v}")

    hard_str = f"🔒 [Hard] " + (" | ".join(hard_items) if hard_items else "None")

    # Soft Filter 포매팅 (기존 유지)
    soft_items = []
    for k, v in s_filters.items():
        if v:
            soft_items.append(f"{k.capitalize()}: {v}")

    soft_str = f"✨ [Soft] " + (" | ".join(soft_items) if soft_items else "None")

    print(f"      {hard_str}", flush=True)
    print(f"      {soft_str}", flush=True)


def smart_search_with_retry(h_filters: dict, s_filters: dict, exclude_ids: list = None):
    import copy

    # 원본 보존을 위해 딥카피 사용 (기존 유지)
    current_filters = copy.deepcopy(s_filters)

    # 1. Full Condition 시도
    print(f"\n      📍 [Attempt 1] Full Conditions", flush=True)
    log_filters(h_filters, current_filters)

    # [수정] search_perfumes_tool.invoke()를 사용하여 검색 수행
    results = search_perfumes_tool.invoke(
        {
            "hard_filters": h_filters,
            "strategy_filters": current_filters,
            "exclude_ids": exclude_ids,
        }
    )

    if results:
        # [추가] 검색 결과 개수 로그
        print(f"      ✅ Found {len(results)} perfumes (Perfect Match)", flush=True)
        return results, "Perfect Match"

    # 2. Waterfall (단계적 조건 완화)
    drop_priority = ["occasion", "style", "accord", "note"]

    for i, key in enumerate(drop_priority):
        if key in current_filters and current_filters[key]:
            dropped_val = current_filters[key]
            del current_filters[key]

            print(
                f"\n      📍 [Attempt {i+2}] Relaxing... (Drop {key.upper()}: {dropped_val})",
                flush=True,
            )
            log_filters(h_filters, current_filters)

            # [수정] 도구 호출 방식 적용
            results = search_perfumes_tool.invoke(
                {
                    "hard_filters": h_filters,
                    "strategy_filters": current_filters,
                    "exclude_ids": exclude_ids,
                }
            )

            if results:
                match_type = f"Relaxed (Dropped {key})"
                # [추가] 검색 결과 개수 로그
                print(
                    f"      ✅ Found {len(results)} perfumes ({match_type})", flush=True
                )
                return results, match_type

    return [], "No Results"


# ==========================================
# 6. Researcher노드 정의
# ==========================================
def researcher_node(state: AgentState):
    print(f"\n🧠 [Researcher] 전략 수립 및 DB 검색...", flush=True)

    user_prefs = state.get("user_preferences", {})
    current_context = json.dumps(user_prefs, ensure_ascii=False)
    print(f"   👤 User Context: {current_context}", flush=True)

    # [1] Hard Filter용 노트 전처리 (기존 로직 유지)
    user_note = user_prefs.get("note")
    refined_hard_note = None
    if user_note:
        matched_notes = lookup_note_by_string_tool.invoke({"keyword": user_note})
        if matched_notes:
            refined_hard_note = matched_notes[0]
            print(
                f"   🎯 User Note Refined: '{user_note}' -> '{refined_hard_note}'",
                flush=True,
            )

    # [2] 전략 수립 메시지 생성
    messages = [
        SystemMessage(content=RESEARCHER_SYSTEM_PROMPT),
        HumanMessage(
            content=f"사용자 요청 데이터: {current_context}\n위 데이터를 바탕으로 '이미지 강조, 보완, 반전'의 3가지 검색 전략을 세워주세요."
        ),
    ]

    try:
        plan_result = SMART_LLM.with_structured_output(ResearchActionPlan).invoke(
            messages
        )
        final_results = []
        collected_ids = []

        for plan in plan_result.plans:
            print(f"\n   " + "-" * 50, flush=True)
            print(f"   👉 [Strategy {plan.priority}] {plan.strategy_name}", flush=True)

            current_reason = plan.reason
            h_filters = (
                plan.hard_filters.model_dump(exclude_none=True)
                if hasattr(plan.hard_filters, "model_dump")
                else plan.hard_filters.dict(exclude_none=True)
            )

            # [안전장치] 계절/성별 한글 값 매핑
            if h_filters.get("season") == "봄":
                h_filters["season"] = "Spring"
            if h_filters.get("gender") == "남성":
                h_filters["gender"] = "Men"
            if refined_hard_note:
                h_filters["note"] = refined_hard_note

            s_filters = (
                plan.strategy_filters.model_dump(exclude_none=True)
                if hasattr(plan.strategy_filters, "model_dump")
                else plan.strategy_filters.dict(exclude_none=True)
            )

            # [3] ★ Strategy Filter용 노트 후보군 추출 및 LLM 정밀 선택
            strategy_note_input = s_filters.get("note")
            if strategy_note_input:
                # [수정] strategy_note_keyword -> strategy_note_input 오타 교정 완료
                raw_keyword = (
                    strategy_note_input[0]
                    if isinstance(strategy_note_input, list) and strategy_note_input
                    else strategy_note_input
                )

                if raw_keyword:
                    print(
                        f"      🔍 '{raw_keyword}' 기반 노트 후보군 추출 중...",
                        flush=True,
                    )
                    # [수정] 도구 호출 방식 적용 (.invoke)
                    candidates = lookup_note_by_vector_tool.invoke(
                        {"keyword": raw_keyword}
                    )

                    if candidates:
                        print(f"      ➡️ 추출된 후보군: {candidates}", flush=True)
                        selection_messages = [
                            SystemMessage(
                                content=NOTE_SELECTION_PROMPT.format(
                                    candidates=candidates
                                )
                            ),
                            HumanMessage(
                                content=f"현재 전략: {plan.strategy_name}\n의도: {current_reason}"
                            ),
                        ]
                        selected_response = SMART_LLM.invoke(selection_messages).content
                        final_selected = [
                            c
                            for c in candidates
                            if c.lower() in selected_response.lower()
                        ]

                        s_filters["note"] = (
                            final_selected if final_selected else candidates[:1]
                        )
                        print(
                            f"      🎯 LLM 최종 선택 노트: {s_filters['note']}",
                            flush=True,
                        )

            # [4] 1차 검색 시도 (검색 개수 로그 포함)
            db_perfumes, match_type = smart_search_with_retry(
                h_filters, s_filters, exclude_ids=collected_ids
            )

            # [5] 검색 실패 시 Re-Act
            if not db_perfumes:
                print(
                    f"      ⚠️ '{plan.strategy_name}' 결과 없음. 재수립 시도...",
                    flush=True,
                )
                retry_messages = [
                    SystemMessage(content=RESEARCHER_SYSTEM_PROMPT),
                    HumanMessage(
                        content=f"사용자 정보: {current_context}\n실패한 필터: {json.dumps(s_filters)}\n전략에 부합하는 새로운 키워드와 사유(Reason)를 제안해줘."
                    ),
                ]
                new_plan = SMART_LLM.with_structured_output(SearchStrategyPlan).invoke(
                    retry_messages
                )
                s_filters = (
                    new_plan.strategy_filters.model_dump(exclude_none=True)
                    if hasattr(new_plan.strategy_filters, "model_dump")
                    else new_plan.strategy_filters.dict(exclude_none=True)
                )
                current_reason = new_plan.reason

                if s_filters.get("note"):
                    retry_keyword = (
                        s_filters["note"][0]
                        if isinstance(s_filters["note"], list) and s_filters["note"]
                        else s_filters["note"]
                    )
                    # [수정] 재시도 시에도 도구 호출 방식 적용
                    retry_candidates = lookup_note_by_vector_tool.invoke(
                        {"keyword": retry_keyword}
                    )
                    if retry_candidates:
                        s_filters["note"] = retry_candidates[:2]

                db_perfumes, match_type = smart_search_with_retry(
                    h_filters, s_filters, exclude_ids=collected_ids
                )

            # [6] 결과 정리
            perfume_details = []
            if db_perfumes:
                p = db_perfumes[0]
                collected_ids.append(p["id"])
                print(
                    f"      ✅ 최종 선정: {p.get('brand')} - {p.get('name')} ({match_type})",
                    flush=True,
                )

                p_notes = PerfumeNotes(
                    top=p.get("top_notes") or "정보 없음",
                    middle=p.get("middle_notes") or "정보 없음",
                    base=p.get("base_notes") or "정보 없음",
                )
                detail = PerfumeDetail(
                    perfume_name=p.get("name", "Unknown"),
                    perfume_brand=p.get("brand", "Unknown"),
                    accord=p.get("accords") or "정보 없음",
                    season="All Seasons",
                    occasion="Any",
                    gender=p.get("gender", "Unisex"),
                    notes=p_notes,
                    image_url=p.get("image_url"),
                )
                perfume_details.append(detail)

            final_results.append(
                StrategyResult(
                    strategy_name=plan.strategy_name,
                    strategy_keyword=plan.strategy_keyword,
                    strategy_reason=current_reason,
                    perfumes=perfume_details,
                )
            )

        return {
            "research_results": (
                ResearcherOutput(results=final_results).model_dump()
                if hasattr(ResearcherOutput, "model_dump")
                else ResearcherOutput(results=final_results).dict()
            ),
            "messages": [AIMessage(content="[RESEARCH_DONE]")],
            "next_step": "writer",
        }

    except Exception as e:
        print(f"   -> 🚨 Researcher Node Error: {e}")
        import traceback

        traceback.print_exc()
        return {"research_results": {"results": []}, "next_step": "writer"}


# ==========================================
# 7. Writer노드 정의 (비동기 처리 적용)
# ==========================================


async def writer_node(state: AgentState):
    print(f"\n✍️ [Writer] 최종 답변 작성 중...", flush=True)
    last_message = state["messages"][-1]
    research_data = state.get("research_results", {})
    results_list = research_data.get("results", [])

    if isinstance(last_message, HumanMessage):
        selected_prompt = WRITER_CHAT_PROMPT
        data_context = ""
    elif not results_list or all(len(r["perfumes"]) == 0 for r in results_list):
        selected_prompt = WRITER_FAILURE_PROMPT
        data_context = ""
    else:
        selected_prompt = WRITER_RECOMMENDATION_PROMPT
        data_context = json.dumps(research_data, ensure_ascii=False, indent=2)

    full_content = f"{selected_prompt}\n\n[참고 데이터]:\n{data_context}"
    messages = [SystemMessage(content=full_content)] + state["messages"]

    try:
        # ainvoke를 사용하여 비동기로 호출합니다.
        # astream_events가 이 내부의 스트림을 자동으로 감지합니다.
        response = await SUPER_SMART_LLM.ainvoke(messages)
        return {"messages": [response], "next_step": "end"}
    except Exception:
        return {"next_step": "end"}


# 4. Graph Build
workflow = StateGraph(AgentState)
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("interviewer", interviewer_node)
workflow.add_node("researcher", researcher_node)
workflow.add_node("writer", writer_node)

workflow.add_edge(START, "supervisor")
workflow.add_conditional_edges(
    "supervisor",
    lambda x: x["next_step"],
    {"interviewer": "interviewer", "researcher": "researcher", "writer": "writer"},
)
workflow.add_conditional_edges(
    "interviewer",
    lambda x: x["next_step"],
    {"end": END, "researcher": "researcher", "writer": "writer"},
)
workflow.add_edge("researcher", "writer")
workflow.add_edge("writer", END)

checkpointer = MemorySaver()
app_graph = workflow.compile(checkpointer=checkpointer)
