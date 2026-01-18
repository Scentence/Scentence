# backend/schemas.py
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage

# =================================================================
# 1. 공통 상태 (Agent State)
# =================================================================
class ChatRequest(BaseModel):
    user_query: str = Field(description="사용자가 입력한 질문 텍스트")
    thread_id: Optional[str] = Field(None, description="세션 관리를 위한 스레드 ID")
    
class AgentState(Dict):
    """
    LangGraph의 각 노드가 공유하는 상태(Memory)입니다.
    """
    messages: List[BaseMessage]      # 대화 기록 (필수)
    user_query: str                  # 사용자의 최초 입력 또는 현재 처리 중인 쿼리
    active_mode: Optional[str]       # 현재 활성화된 모드 (interviewer 등)
    next_step: Optional[str]         # 다음 실행할 노드 이름
    
    # [New] 노드 간 데이터 전달용 슬롯
    user_preferences: Optional[Dict] # Interviewer -> Researcher 전달 데이터 (JSON)
    research_results: Optional[List] # Researcher -> Writer 전달 데이터 (List[JSON])


# =================================================================
# 2. 인터뷰어 -> 리서쳐 (UserPreferences)
# =================================================================
class UserPreferences(BaseModel):
    """
    인터뷰어가 사용자 대화에서 추출한 핵심 정보입니다.
    """
    target: str = Field(
        description="대상 정보 (예: 20대 여성, 30대 남성, 회사 상사, 여자친구 등)"
    )
    gender: str = Field(
        description="성별 정보 (남성, 여성, 중성). *'중성적'이라는 표현이 있거나 성별이 모호하면 '중성'으로 기재"
    )
    brand: Optional[str] = Field(
        None, 
        description="특정 브랜드를 언급한 경우 (없으면 null)"
    )
    perfume: Optional[str] = Field(
        None, 
        description="특정 향수를 언급하며 비슷한 걸 찾아달라고 한 경우 (없으면 null)"
    )
    situation: Optional[str] = Field(
        None, 
        description="상황 정보 (예: 비즈니스 미팅, 결혼식, 데이트 등)"
    )
    season: Optional[str] = Field(
        None, 
        description="계절 정보 (봄, 여름, 가을, 겨울)"
    )
    like: Optional[str] = Field(
        None, 
        description="취향 정보 (대상이 좋아하는 향이나 느낌)"
    )
    style: Optional[str] = Field(
        None, 
        description="이미지 정보 (시크한, 귀여운, 차가운 등 주변에서 인식하는 분위기)"
    )


# =================================================================
# 3. 리서쳐 -> 라이터 (ResearcherOutput)
# =================================================================

# 3-1. 향수 노트 상세 (하위 구조)
class PerfumeNotes(BaseModel):
    top: str = Field(description="탑 노트 (없으면 '정보 없음')")
    middle: str = Field(description="미들 노트 (없으면 '정보 없음')")
    base: str = Field(description="베이스 노트 (없으면 '정보 없음')")

# 3-2. 개별 향수 정보 (하위 구조)
class PerfumeDetail(BaseModel):
    perfume_name: str = Field(description="향수 이름")
    perfume_brand: str = Field(description="향수 브랜드")
    accord: str = Field(description="주요 어코드 (예: Citrus, Woody)")
    season: str = Field(description="추천 계절")
    occasion: str = Field(description="추천 상황")
    gender: str = Field(description="추천 성별")
    notes: PerfumeNotes = Field(description="노트 정보 객체 (Top/Middle/Base)")
    image_url: Optional[str] = Field(None, description="향수 이미지 URL (DB에 있는 경우)")

# 3-3. 전략별 결과 (중간 구조)
class StrategyResult(BaseModel):
    strategy_name: str = Field(
        description="전략 이름 (예: '차가운 이미지에 어울리는 반전 향수')"
    )
    strategy_keyword: List[str] = Field(
        description="이 전략을 위해 리서쳐가 사용한 검색 키워드 리스트"
    )
    perfumes: List[PerfumeDetail] = Field(
        description="해당 전략으로 검색된 향수 리스트 (최대 1~2개 권장)"
    )

# 3-4. 최종 리서쳐 출력 (최상위 구조)
class ResearcherOutput(BaseModel):
    """
    리서쳐가 라이터에게 전달하는 최종 결과물입니다.
    """
    results: List[StrategyResult] = Field(
        description="3가지 전략에 대한 최종 결과 리스트"
    )