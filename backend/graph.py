import os
import json
from typing import Literal, List, Dict, Any, Optional

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from pydantic import BaseModel, Field

# [Import] 로컬 모듈
from schemas import (
    AgentState, 
    UserPreferences, 
    ResearcherOutput, 
    StrategyResult, 
    PerfumeDetail, 
    PerfumeNotes
)
from database import search_perfumes
from prompts import (
    SUPERVISOR_PROMPT, 
    INTERVIEWER_PROMPT, 
    RESEARCHER_SYSTEM_PROMPT, 
    WRITER_FAILURE_PROMPT,
    WRITER_CHAT_PROMPT,
    WRITER_RECOMMENDATION_PROMPT
)

load_dotenv()

# ==========================================
# 1. 모델 설정
# ==========================================
FAST_LLM = ChatOpenAI(model="gpt-4o-mini", temperature=0)
SMART_LLM = ChatOpenAI(model="gpt-4o", temperature=0)

# ==========================================
# 2. 내부 로직용 구조체
# ==========================================
class InterviewResult(BaseModel):
    user_preferences: UserPreferences = Field(description="추출된 사용자 선호 정보")
    is_sufficient: bool = Field(description="필수 정보(Target+Concept)가 충족되었는지 여부")
    response_message: str = Field(description="사용자에게 건넬 질문 또는 안내 멘트")
    is_off_topic: bool = Field(description="주제가 향수와 관련 없는지 여부")

class HardFilters(BaseModel):
    # LLM이 자유롭게 Women, Female, Men 등을 뱉어도 DB에서 처리하도록 함
    gender: str = Field(description="성별 (Women, Men, Unisex)")
    brand: Optional[str] = Field(None, description="특정 브랜드 (없으면 null)")

class StrategyFilters(BaseModel):
    accord: Optional[List[str]] = Field(None, description="향의 분위기")
    season: Optional[List[str]] = Field(None, description="계절")
    occasion: Optional[List[str]] = Field(None, description="상황")
    note: Optional[List[str]] = Field(None, description="구체적 노트")
    style: Optional[List[str]] = Field(None, description="스타일 (Modern, Classic 등)")

class SearchStrategyPlan(BaseModel):
    priority: int = Field(description="전략 우선순위 (1, 2, 3)")
    
    # [★수정] description에 '반드시 한글' 명시
    strategy_name: str = Field(description="전략 이름 (예: '상큼한 데일리 무드', 반드시 한글로 작성)")
    reason: str = Field(description="전략 의도 (이 전략을 선택한 이유, 반드시 한글로 작성)")
    
    hard_filters: HardFilters = Field(description="DB 검색용 필수 필터 객체")
    strategy_filters: StrategyFilters = Field(description="DB 검색용 전략 필터 객체")
    
    strategy_keyword: List[str] = Field(description="이 전략을 표현하는 핵심 키워드들")

class ResearchActionPlan(BaseModel):
    plans: List[SearchStrategyPlan] = Field(description="3가지 검색 전략")

class RoutingDecision(BaseModel):
    next_step: Literal["interviewer", "researcher", "writer"] = Field(description="다음 단계")


# ==========================================
# 3. Node Functions
# ==========================================
def supervisor_node(state: AgentState):
    print("\n" + "="*60, flush=True)
    print("👀 [Supervisor] 대화 의도 분석 중...", flush=True)
    if state.get("active_mode") == "interviewer":
        print("   -> ⏩ Active Mode: Interviewer 유지", flush=True)
        return {"next_step": "interviewer"}
    messages = [SystemMessage(content=SUPERVISOR_PROMPT)] + state["messages"]
    try:
        response = FAST_LLM.with_structured_output(RoutingDecision).invoke(messages)
        decision = response.next_step
        print(f"   -> 🎯 결정된 경로: {decision.upper()}", flush=True)
    except Exception:
        decision = "interviewer"
    return {"next_step": decision}

def interviewer_node(state: AgentState):
    print(f"\n🎤 [Interviewer] 정보 분석 중...", flush=True)
    current_prefs = state.get("user_preferences", {})
    current_prefs_str = json.dumps(current_prefs, ensure_ascii=False, indent=2) if current_prefs else "없음"

    augmented_prompt = f"""
    {INTERVIEWER_PROMPT}
    [★Context★] 이전 수집 정보: {current_prefs_str}
    """
    messages = [SystemMessage(content=augmented_prompt)] + state["messages"]
    
    try:
        result = FAST_LLM.with_structured_output(InterviewResult).invoke(messages)
        print(f"   -> 📊 판단: 충족({result.is_sufficient}), 잡담({result.is_off_topic})", flush=True)
        
        if result.is_off_topic:
            return {"active_mode": None, "next_step": "writer"}

        if result.is_sufficient:
            print("   -> 🚀 정보 충족! Researcher 호출", flush=True)
            return {
                "messages": [AIMessage(content=result.response_message)],
                "user_preferences": result.user_preferences.dict(),
                "active_mode": None,
                "next_step": "researcher"
            }
        else:
            print("   -> ❓ 정보 부족", flush=True)
            return {
                "messages": [AIMessage(content=result.response_message)],
                "user_preferences": result.user_preferences.dict(),
                "active_mode": "interviewer",
                "next_step": "end"
            }
    except Exception as e:
        print(f"   -> ⚠️ Error: {e}")
        return {"active_mode": None, "next_step": "writer"}

# [★수정] 로그 출력용 헬퍼 함수 추가
def log_filters(h_filters: dict, s_filters: dict):
    # Hard Filter 포매팅
    gender = h_filters.get('gender', 'Unisex (Default)')
    brand = h_filters.get('brand') or "All Brands"
    hard_str = f"🔒 [Hard] Gender: {gender} | Brand: {brand}"
    
    # Soft Filter 포매팅 (값이 있는 것만 출력)
    soft_items = []
    for k, v in s_filters.items():
        if v: soft_items.append(f"{k.capitalize()}: {v}")
    
    soft_str = f"✨ [Soft] " + (" | ".join(soft_items) if soft_items else "None")
    
    # [★수정 완료] hard_filters -> h_filters로 변경
    print(f"      {h_filters.get('gender', 'Unisex')} 타겟 / {brand} 검색", flush=True) 
    print(f"      {hard_str}", flush=True)
    print(f"      {soft_str}", flush=True)


def smart_search_with_retry(h_filters: dict, s_filters: dict, exclude_ids: list = None):
    import copy
    
    current_filters = copy.deepcopy(s_filters)
    
    # 1. Full Condition
    print(f"\n      📍 [Attempt 1] Full Conditions", flush=True)
    log_filters(h_filters, current_filters)
    
    # [★수정] exclude_ids 전달
    results = search_perfumes(h_filters, current_filters, exclude_ids=exclude_ids)
    if results: return results, "Perfect Match"

    # 2. Waterfall
    drop_priority = ['occasion', 'season', 'style', 'note']
    
    for i, key in enumerate(drop_priority):
        if key in current_filters:
            dropped_val = current_filters[key]
            del current_filters[key]
            current_filters = {k: v for k, v in current_filters.items() if v}
            
            print(f"\n      📍 [Attempt {i+2}] Relaxing... (Drop {key.upper()}: {dropped_val})", flush=True)
            log_filters(h_filters, current_filters)
            
            # [★수정] exclude_ids 전달
            results = search_perfumes(h_filters, current_filters, exclude_ids=exclude_ids)
            if results: return results, f"Relaxed (Dropped {key})"
            
    return [], "No Results"


def researcher_node(state: AgentState):
    print(f"\n🧠 [Researcher] 전략 수립 및 DB 검색...", flush=True)
    
    user_prefs = state.get("user_preferences", {})
    print(f"   👤 User Context: {json.dumps(user_prefs, ensure_ascii=False)}", flush=True)
    
    messages = [
        SystemMessage(content=RESEARCHER_SYSTEM_PROMPT),
        HumanMessage(content=f"User Preferences: {json.dumps(user_prefs, ensure_ascii=False)}")
    ]
    
    try:
        plan_result = SMART_LLM.with_structured_output(ResearchActionPlan).invoke(messages)
        final_results = []
        
        # [★New] 중복 방지를 위한 ID 저장소
        collected_ids = []
        
        for plan in plan_result.plans:
            print(f"\n   " + "-"*50, flush=True)
            print(f"   👉 [Strategy {plan.priority}] {plan.strategy_name}", flush=True)
            print(f"      (의도: {plan.reason})", flush=True)
            print(f"   " + "-"*50, flush=True)
            
            h_filters = plan.hard_filters.dict(exclude_none=True)
            s_filters = plan.strategy_filters.dict(exclude_none=True)
            
            # [★수정] collected_ids를 exclude_ids로 전달
            db_perfumes, match_type = smart_search_with_retry(h_filters, s_filters, exclude_ids=collected_ids)
            
            perfume_details = []
            if db_perfumes:
                print(f"      ✅ Found {len(db_perfumes)} perfumes ({match_type})", flush=True)
                for p in db_perfumes:
                    # [★New] 찾은 향수 ID를 수집하여 다음 전략에서 제외
                    collected_ids.append(p['id'])

                    p_notes = PerfumeNotes(
                        top=p.get('top_notes') or "정보 없음",
                        middle=p.get('middle_notes') or "정보 없음",
                        base=p.get('base_notes') or "정보 없음"
                    )

                    detail = PerfumeDetail(
                        perfume_name=p.get('name', 'Unknown'),
                        perfume_brand=p.get('brand', 'Unknown'),
                        accord=p.get('accords') if p.get('accords') else "정보 없음", 
                        season="All Seasons", 
                        occasion="Any",
                        gender=p.get('gender', 'Unisex'),
                        notes=p_notes,
                        image_url=p.get('image_url')
                    )
                    perfume_details.append(detail)
            else:
                print(f"      ❌ No results found after all retries.", flush=True)

            final_results.append(StrategyResult(
                strategy_name=plan.strategy_name,
                strategy_keyword=plan.strategy_keyword,
                perfumes=perfume_details
            ))

        return {
            "research_results": ResearcherOutput(results=final_results).dict(),
            "messages": [AIMessage(content="[RESEARCH_DONE]")],
            "next_step": "writer"
        }

    except Exception as e:
        print(f"   -> 🚨 Error: {e}")
        import traceback; traceback.print_exc()
        return {
            "research_results": {"results": []}, 
            "messages": [AIMessage(content="[RESEARCH_ERROR]")],
            "next_step": "writer"
        }


def writer_node(state: AgentState):
    print(f"\n✍️ [Writer] 최종 답변 작성 중...", flush=True)
    last_message = state["messages"][-1]
    research_data = state.get("research_results", {})
    results_list = research_data.get("results", [])
    
    if isinstance(last_message, HumanMessage):
        selected_prompt = WRITER_CHAT_PROMPT
        data_context = ""
    elif not results_list or all(len(r['perfumes']) == 0 for r in results_list):
        selected_prompt = WRITER_FAILURE_PROMPT
        data_context = ""
    else:
        selected_prompt = WRITER_RECOMMENDATION_PROMPT
        data_context = json.dumps(research_data, ensure_ascii=False, indent=2)

    full_content = f"{selected_prompt}\n\n[참고 데이터]:\n{data_context}"
    messages = [SystemMessage(content=full_content)] + state["messages"]
    
    try:
        response = SMART_LLM.invoke(messages)
        print("   -> ✅ 답변 작성 완료\n" + "="*60, flush=True)
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
workflow.add_conditional_edges("supervisor", lambda x: x["next_step"], 
                               {"interviewer": "interviewer", "researcher": "researcher", "writer": "writer"})
workflow.add_conditional_edges("interviewer", lambda x: x["next_step"],
                               {"end": END, "researcher": "researcher", "writer": "writer"})
workflow.add_edge("researcher", "writer")
workflow.add_edge("writer", END)

checkpointer = MemorySaver()
app_graph = workflow.compile(checkpointer=checkpointer)