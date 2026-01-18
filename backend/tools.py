# tools.py
from langchain_core.tools import tool
from typing import List, Dict, Any

# [수정 포인트] 바뀐 함수 이름(lookup_notes, search_perfumes)을 import 합니다.
from database import lookup_notes, search_perfumes 

@tool
def lookup_notes_tool(keyword: str) -> List[str]:
    """
    사용자가 말한 추상적인 향 느낌(예: '섹시한', '숲 냄새')이나 오타를 
    데이터베이스에 존재하는 정확한 노트 명칭(예: 'Musk', 'Pine')으로 변환합니다.
    """
    return lookup_notes(keyword)

@tool
def search_perfumes_tool(hard_filters: Dict[str, str], strategy_filters: Dict[str, List[str]]) -> List[Dict[str, Any]]:
    """
    조건에 맞는 향수를 검색합니다.
    - hard_filters: 타협 불가능한 조건 (brand, gender)
    - strategy_filters: season(Spring..), accord(Citrus..), style(Modern..), note, occasion 등
    """
    return search_perfumes(hard_filters, strategy_filters)

# Export tools list
TOOLS = [lookup_notes_tool, search_perfumes_tool]