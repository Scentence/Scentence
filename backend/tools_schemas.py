# tools_schemas.py
from typing import List, Literal, Optional
from pydantic import BaseModel, Field

# ==========================================
# [Schema 1] 노트 검색용 (Vector Search)
# ==========================================
class NoteSearchInput(BaseModel):
    keyword: str = Field(
        description="노트를 찾기 위한 추상적인 키워드 (예: 'Sexy', 'Fresh', 'Jungle', 'Clean')"
    )

# ==========================================
# [Schema 2] 향수 검색용 (Main Search)
# ==========================================
class SearchFilter(BaseModel):
    """개별 검색 조건 정의"""
    column: Literal["brand", "perfume_name", "note", "accord", "season", "gender", "occasion"] = Field(
        description="검색할 DB 컬럼명 (brand, note, accord, season, gender, occasion 중 하나)"
    )
    value: str = Field(
        description="검색할 값 (반드시 영어). 예: 'Summer', 'Rose', 'Chanel'"
    )

class PerfumeSearchInput(BaseModel):
    """
    [전략적 검색 주문서]
    LLM은 사용자 요구사항을 분석하여 '타협할 수 없는 조건'과 '전략적으로 제안할 조건'을 나누어 입력해야 합니다.
    """
    hard_filters: List[SearchFilter] = Field(
        default=[],
        description="[Query 1] 절대 타협할 수 없는 필수 조건 (예: 사용자 성별, 특정 브랜드 선호 등)"
    )
    strategy_filters: List[SearchFilter] = Field(
        default=[],
        description="[Query 2] AI가 제안하는 전략적 조건 (우선순위 높은 순서대로 배열). 검색 실패 시 뒤에서부터 하나씩 제거됨."
    )