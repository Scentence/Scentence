# backend/agent/tools.py
import asyncio
from langchain_core.tools import tool
from typing import List, Dict, Any

# [수정] 비동기 처리를 위해 rerank_perfumes_async 임포트
from .database import (
    lookup_note_by_string,
    lookup_note_by_vector,
    search_perfumes,
    rerank_perfumes_async,
)

from .tools_schemas import LookupNoteInput, AdvancedSearchInput


@tool(args_schema=LookupNoteInput)
async def lookup_note_by_string_tool(keyword: str) -> List[str]:
    """
    사용자가 직접 입력한 구체적인 향료 이름의 오탈자를 교정합니다.
    - 명시적 노드를 Hard Filter용 표준 명칭으로 바꿀 때 사용하세요.
    """
    # [최적화] 동기 DB 함수를 별도 스레드에서 실행하여 이벤트 루프 블로킹 방지
    return await asyncio.to_thread(lookup_note_by_string, keyword)


@tool(args_schema=LookupNoteInput)
async def lookup_note_by_vector_tool(keyword: str) -> List[str]:
    """
    추상적인 향기 느낌이나 키워드와 관련된 실제 향료 후보군 10개를 검색합니다.
    - AI가 제안한 키워드를 실제 DB 노드로 변환할 때 사용하세요.
    """
    # [최적화] 동기 함수를 비동기 스레드에서 처리
    return await asyncio.to_thread(lookup_note_by_vector, keyword)


@tool(args_schema=AdvancedSearchInput)
async def advanced_perfume_search_tool(
    hard_filters: Dict[str, Any],
    strategy_filters: Dict[str, List[str]],
    exclude_ids: List[int],
    query_text: str,
    rank_mode: str = "DEFAULT",
) -> List[Dict[str, Any]]:
    """
    [고도화된 비동기 검색 도구]
    1. DB에서 조건에 맞는 향수 20개를 1차로 검색합니다. (병렬 처리 지원)
    2. 비동기 LLM을 이용해 리뷰 데이터와 전략 의도를 매칭하여 재정렬합니다.
    3. 최종 상위 5개를 반환합니다.
    """

    # 1. Broad Retrieval (Thread Pool 사용으로 병렬성 확보)
    candidates = await asyncio.to_thread(
        search_perfumes,
        hard_filters=hard_filters,
        strategy_filters=strategy_filters,
        exclude_ids=exclude_ids,
        limit=20,
    )

    if not candidates:
        return []

    # 2. Semantic Reranking (비동기 LLM 호출)
    # [최적화] rerank_perfumes_async를 호출하여 검색 중 발생하는 지연을 최소화합니다.
    final_results = await rerank_perfumes_async(
        candidates, query_text, top_k=5, rank_mode=rank_mode
    )

    return final_results


# Export tools list
TOOLS = [
    lookup_note_by_string_tool,
    lookup_note_by_vector_tool,
    advanced_perfume_search_tool,
]
