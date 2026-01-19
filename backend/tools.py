# tools.py
from langchain_core.tools import tool
from typing import List, Dict, Any

# database.py에서 분리된 핵심 함수들을 임포트합니다.
from database import lookup_note_by_string, lookup_note_by_vector, search_perfumes

# 정의한 스키마를 임포트합니다.
from tools_schemas import LookupNoteInput, SearchPerfumesInput


@tool(args_schema=LookupNoteInput)
def lookup_note_by_string_tool(keyword: str) -> List[str]:
    """
    사용자가 직접 입력한 구체적인 향료 이름의 오탈자를 교정합니다.
    - 사용자가 직접 언급한 '명시적 노트'를 Hard Filter용 표준 명칭으로 바꿀 때 사용하세요.
    """
    return lookup_note_by_string(keyword)


@tool(args_schema=LookupNoteInput)
def lookup_note_by_vector_tool(keyword: str) -> List[str]:
    """
    추상적인 향기 느낌이나 키워드와 관련된 실제 향료 후보군 10개를 검색합니다.
    - AI가 제안한 '이미지 키워드'를 실제 DB 노드로 변환하여 선택지를 확보할 때 사용하세요.
    """
    return lookup_note_by_vector(keyword)


@tool(args_schema=SearchPerfumesInput)
def search_perfumes_tool(
    hard_filters: Dict[str, Any],
    strategy_filters: Dict[str, List[str]],
    exclude_ids: List[int] = None,
) -> List[Dict[str, Any]]:
    """
    확정된 필터들을 바탕으로 향수 데이터베이스에서 조건에 맞는 제품을 검색합니다.
    """
    return search_perfumes(hard_filters, strategy_filters, exclude_ids=exclude_ids)


# Researcher 노드 등에서 사용할 도구 리스트
TOOLS = [lookup_note_by_string_tool, lookup_note_by_vector_tool, search_perfumes_tool]
