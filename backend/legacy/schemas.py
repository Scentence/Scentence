# schemas.py
from typing import Any, List, Optional, Dict
from typing_extensions import TypedDict, Literal
from pydantic import BaseModel, Field


class State(TypedDict):
    # ==========================================
    # [1] 기본 입력 및 히스토리
    # ==========================================
    user_query: str
    messages: List[Any]  # 대화 히스토리 (Supervisor 판단용)

    # ==========================================
    # [2] 라우팅 및 인터뷰 상태
    # ==========================================
    # route에 "end"가 포함되어야 합니다.
    route: Literal["supervisor", "interviewer", "researcher", "writer", "end"]

    # 인터뷰어가 수집한 문맥 ("계절: 여름, 노트: 시트러스...")
    interview_context: Optional[str]

    # [중요] 인터뷰 모드 활성화 여부 (Supervisor 하이패스용)
    active_mode: Optional[str]

    # 부족한 정보 (Supervisor 판단)
    missing_info: Optional[str]

    # ==========================================
    # [3] 검색(Researcher) 관련 필드
    # ==========================================
    clarified_query: Optional[str]  # 질문 구체화
    search_plans: List[dict]  # 수립된 검색 전략들
    search_logs: List[str]  # 검색 과정 로그
    research_result: Optional[str]  # 최종 검색 결과 텍스트
    retry_count: int  # 검색 재시도 횟수 (Re-Act 패턴)

    # ==========================================
    # [4] 출력 및 메타 데이터
    # ==========================================
    final_response: Optional[str]  # (기존 호환성) 최종 완성 텍스트

    # 토큰 사용량 계산
    input_tokens: int
    output_tokens: int

    # 테스트용 메타 정보
    test_info: Optional[dict]

    # ==========================================
    # [5] ★ NEW: 스트리밍 객체 전달용
    # ==========================================
    # Writer 노드가 생성한 'OpenAI Stream' 객체를 Main으로 배달하는 가방
    writer_stream: Any


# API 요청 바디
class ChatRequest(BaseModel):
    user_query: str = Field(..., min_length=1, description="사용자가 입력한 질의")
