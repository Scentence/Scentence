# backend/schemas.py
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage


# =================================================================
# 1. 공통 상태 및 요청 (Common State)
# =================================================================
class ChatRequest(BaseModel):
    user_query: str = Field(description="사용자가 입력한 질문 텍스트")
    thread_id: Optional[str] = Field(None, description="세션 관리를 위한 스레드 ID")


class AgentState(Dict):
    """
    LangGraph의 각 노드가 공유하는 상태(Memory)입니다.
    """

    messages: List[BaseMessage]
    user_query: str
    active_mode: Optional[str]
    next_step: Optional[str]
    user_preferences: Optional[Dict]
    research_results: Optional[List]


# =================================================================
# 2. 인터뷰 및 라우팅 (Interviewer & Router)
# =================================================================
class UserPreferences(BaseModel):
    """
    인터뷰어가 사용자 대화에서 추출한 핵심 정보입니다.
    """

    target: str = Field(description="대상 정보 (예: 20대 여성, 30대 남성 등)")
    gender: str = Field(description="성별 정보 (Women, Men, Unisex)")
    brand: Optional[str] = Field(None, description="특정 브랜드")
    perfume: Optional[str] = Field(None, description="특정 향수")
    situation: Optional[str] = Field(None, description="상황 정보")
    season: Optional[str] = Field(None, description="계절 정보")
    like: Optional[str] = Field(None, description="취향 정보")
    style: Optional[str] = Field(None, description="이미지 정보")


class InterviewResult(BaseModel):
    user_preferences: UserPreferences = Field(description="추출된 사용자 선호 정보")
    is_sufficient: bool = Field(description="필수 정보 충족 여부")
    response_message: str = Field(description="안내 멘트")
    is_off_topic: bool = Field(description="주제 이탈 여부")


class RoutingDecision(BaseModel):
    next_step: Literal["interviewer", "researcher", "writer"] = Field(
        description="다음 단계"
    )


# =================================================================
# 3. 리서처 전략 수립 (Researcher Planning)
# =================================================================
class HardFilters(BaseModel):
    gender: str = Field(description="성별 (Women, Men, Unisex)")
    brand: Optional[str] = Field(None, description="브랜드")
    season: Optional[str] = Field(None, description="계절")
    occasion: Optional[str] = Field(None, description="상황")
    accord: Optional[str] = Field(None, description="어코드")
    note: Optional[str] = Field(None, description="특정 노트")


class StrategyFilters(BaseModel):
    accord: Optional[List[str]] = Field(None, description="향의 분위기")
    occasion: Optional[List[str]] = Field(None, description="상황")
    note: Optional[List[str]] = Field(None, description="구체적 노트")
    style: Optional[List[str]] = Field(None, description="스타일")


class SearchStrategyPlan(BaseModel):
    priority: int = Field(description="전략 우선순위")
    strategy_name: str = Field(description="전략 이름 (한글)")
    reason: str = Field(description="전략 의도 (한글)")
    hard_filters: HardFilters = Field(description="필수 필터")
    strategy_filters: StrategyFilters = Field(description="전략 필터")
    strategy_keyword: List[str] = Field(description="핵심 키워드")


class ResearchActionPlan(BaseModel):
    plans: List[SearchStrategyPlan] = Field(description="3가지 검색 전략")


# =================================================================
# 4. 리서처 결과 및 라이터 전달 (Researcher Output)
# =================================================================
class PerfumeNotes(BaseModel):
    top: str = Field(description="탑 노트")
    middle: str = Field(description="미들 노트")
    base: str = Field(description="베이스 노트")


class PerfumeDetail(BaseModel):
    perfume_name: str = Field(description="향수 이름")
    perfume_brand: str = Field(description="향수 브랜드")
    accord: str = Field(description="주요 어코드")
    season: str = Field(description="추천 계절")
    occasion: str = Field(description="추천 상황")
    gender: str = Field(description="추천 성별")
    notes: PerfumeNotes = Field(description="노트 정보")
    image_url: Optional[str] = Field(None, description="이미지 URL")


class StrategyResult(BaseModel):
    strategy_name: str = Field(description="전략 이름")
    strategy_keyword: List[str] = Field(description="사용된 키워드 리스트")
    strategy_reason: str = Field(description="수립 의도와 이유 (한글)")
    perfumes: List[PerfumeDetail] = Field(description="검색된 향수 리스트")


class ResearcherOutput(BaseModel):
    results: List[StrategyResult] = Field(description="최종 결과 리스트")
