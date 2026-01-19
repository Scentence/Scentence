# tools_schemas.py
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class LookupNoteInput(BaseModel):
    """노트(향료) 명칭 조회를 위한 입력 스키마"""

    keyword: str = Field(
        description="조회하거나 교정할 향기 키워드 (예: 'Rose', '숲의 향')"
    )


class SearchPerfumesInput(BaseModel):
    """향수 검색을 위한 입력 스키마"""

    hard_filters: Dict[str, Any] = Field(
        description="타협 불가능한 필수 조건 (gender, brand, refined_note 등)"
    )
    strategy_filters: Dict[str, List[str]] = Field(
        description="이미지 전략에 따른 유연 조건 (season, accord, selected_note, occasion 등)"
    )
    exclude_ids: Optional[List[int]] = Field(
        default=None, description="이미 추천되어 결과에서 제외할 향수 ID 리스트"
    )
