# tools_schemas.py
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class LookupNoteInput(BaseModel):
    """노트(향료) 명칭 조회를 위한 입력 스키마"""

    keyword: str = Field(
        description="조회하거나 교정할 향기 키워드 (예: 'Rose', '숲의 향')"
    )


# ==========================================
# [Schema 2] 고도화된 향수 검색용 (Advanced Search) - [신규]
# ==========================================
class AdvancedSearchInput(BaseModel):
    """
    [고도화된 향수 검색]
    1차로 메타 데이터 필터를 통해 후보군을 넓게 확보한 뒤,
    'query_text'(전략 의도)와 리뷰 데이터를 비교해 정밀하게 리랭킹(Reranking)합니다.
    """

    hard_filters: Dict[str, Any] = Field(
        description="타협 불가능한 필수 조건 (gender, brand 등). DB 컬럼과 일치해야 함."
    )
    strategy_filters: Dict[str, List[str]] = Field(
        description="이미지 전략에 따른 유연 조건 (season, accord, note, occasion 등)"
    )
    exclude_ids: Optional[List[int]] = Field(
        default=None, description="이미 추천되어 결과에서 제외할 향수 ID 리스트"
    )
    query_text: str = Field(
        description="리랭킹을 위한 전략 의도(Reason) 또는 검색 키워드. (예: '비 오는 날 숲속의 차분한 느낌')"
    )
    rank_mode: str = Field(
        default="DEFAULT",
        description="랭킹 모드: 'DEFAULT' (의미 기반) 또는 'POPULAR' (인기순)",
    )
