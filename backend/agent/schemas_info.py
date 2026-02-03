# backend/agent/schemas_info.py
from typing import List, Optional, Dict, Literal, Any
from pydantic import BaseModel, Field

# ==========================================
# 1. 정보 검색 전용 상태 (Info State)
# ==========================================
# 메인 그래프의 State와는 별개로, 정보 팀 내부에서만 쓰는 상태입니다.
class InfoState(Dict):
    user_query: str                  # 사용자의 원래 질문
    
    # [★수정] 여기에 "similarity"가 추가되어야 합니다.
    info_type: Literal["perfume", "note", "accord", "brand", "similarity", "unknown"] 
    
    target_name: str                 # 검색할 대상 이름
    target_id: Optional[int]         # 검색할 대상 perfume_id (순번/대명사 해석 시 사용)
    
    # 검색 결과 데이터
    search_result: Optional[Dict]    # DB에서 찾은 Raw Data
    final_answer: Optional[str]      # 사용자에게 나갈 최종 답변 텍스트
    
    # 실패 메시지 (fallback_handler로 전달)
    fail_msg: Optional[str]          # 실패/범위 밖/추천 없음 시 사용자에게 전달할 메시지
    
    # 사용자 모드 (메인 그래프에서 전달)
    user_mode: Optional[str]         # BEGINNER 또는 EXPERT
    
    # [★ Wave 1] 결과 상태 분기용 필드 (NO_RESULTS/ERROR/OK 구분)
    info_status: Optional[Literal['OK', 'NO_RESULTS', 'ERROR']]  # 검색 결과 상태
    
    # 메시지 기록
    messages: List[Any] 


# ==========================================
# 2. 정보 분류 라우팅 (Router Output)
# ==========================================
class InfoRoutingDecision(BaseModel):
    """사용자 질문이 무엇에 관한 것인지 분류"""
    
    # [★수정] 여기가 핵심입니다. "similarity" 옵션 추가!
    info_type: Literal["perfume", "note", "accord", "brand", "similarity"] = Field(
        description="질문의 대상 카테고리 (향수, 노트, 어코드, 브랜드, 유사추천)"
    )
    
    target_name: str = Field(
        description="질문의 핵심 대상 이름 (예: '조말론 블랙베리', '우디', '샤넬')"
    )
    intent: str = Field(
        description="사용자가 궁금해하는 구체적인 내용 (예: '지속력이 궁금해', '비슷한거 추천해줘')"
    )