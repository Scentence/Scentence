# backend/agent/test/test_schemas.py
from pydantic import BaseModel, Field
from typing import Optional, Dict, List
 
 
class TestChatRequest(BaseModel):
    """테스트 채팅 요청 스키마"""
    user_query: str = Field(..., description="테스트 입력")
    session_id: str = Field(..., description="테스트 세션 ID")
    thread_id: str = Field(default="test_thread", description="챗봇 스레드 ID")
    turn_count: int = Field(default=1, description="현재 대화 턴 번호")
    member_id: Optional[int] = Field(default=0, description="회원 ID")
    user_mode: Optional[str] = Field(default="BEGINNER", description="사용자 모드")
    context: Optional[Dict] = Field(default={}, description="이전 대화 컨텍스트")
 
 
class TestEvaluation(BaseModel):
    """AI 평가 결과 스키마"""
    verdict: str = Field(..., description="판정 결과 (PASS, FAIL, WARNING)")
    issue_type: Optional[str] = Field(None, description="문제 유형 코드")
    severity: Optional[str] = Field(None, description="심각도 (HIGH, MEDIUM, LOW)")
    expected_output: str = Field(default="", description="이상적인 응답 설명")
    suggestion: str = Field(default="", description="수정 방안 제안")
    target_agent: Optional[str] = Field(None, description="문제의 원인 에이전트")
    affected_file: Optional[str] = Field(None, description="영향받는 파일:라인번호")
 
 
class TestLogEntry(BaseModel):
    """테스트 로그 항목"""
    TC_ID: str
    타임스탬프: str
    대화_턴수: int
    실제입력: str
    실제출력: str
    기대_출력: str
    판정: str
    문제_유형: Optional[str]
    심각도: Optional[str]
    수정_방안_제안: str
    수정_대상_에이전트: Optional[str]
    영향_파일: Optional[str]
 
 
class TestSession(BaseModel):
    """테스트 세션"""
    session_id: str
    results: List[TestLogEntry] = []
 
 
class TestChatResponse(BaseModel):
    """테스트 채팅 응답"""
    response: str = Field(..., description="챗봇 응답")
    evaluation: TestEvaluation = Field(..., description="AI 평가 결과")
 
 
class ExportRequest(BaseModel):
    """내보내기 요청"""
    format: str = Field(default="csv", description="출력 형식 (csv, xlsx, md)")