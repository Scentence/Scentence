# backend/agent/test/test_agent.py
"""
GPT-5.2 기반 테스트 에이전트
챗봇 응답을 자동으로 평가하고 개선 방안을 제시합니다.
"""
 
import json
import os
from typing import Dict, Any
from openai import AsyncOpenAI
from dotenv import load_dotenv
 
from .test_prompts import EVALUATOR_SYSTEM_PROMPT
 
load_dotenv()
 
 
class TestAgent:
    """챗봇 품질 평가 에이전트"""
 
    def __init__(self, model: str = "gpt-4o"):
        """
        Args:
            model: 사용할 OpenAI 모델 (기본값: gpt-4o, 프로덕션: gpt-5.2)
        """
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model
 
    async def evaluate(
        self,
        user_input: str,
        bot_output: str,
        conversation_turn: int,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        단일 대화 턴을 평가하고 JSON 결과 반환
 
        Args:
            user_input: 사용자 입력
            bot_output: 챗봇 응답
            conversation_turn: 현재 대화 턴 번호
            context: 이전 대화 컨텍스트 (history 포함)
 
        Returns:
            평가 결과 딕셔너리
        """
        history = context.get("history", [])
        history_str = json.dumps(history, ensure_ascii=False, indent=2) if history else "없음"
 
        user_message = f"""
## 평가 대상
 
**[대화 턴]**: {conversation_turn}
 
**[이전 대화 내역]**:
{history_str}
 
**[현재 사용자 입력]**:
{user_input}
 
**[챗봇 응답]**:
{bot_output}
 
---
 
위 대화를 분석하여 JSON 형식으로 평가 결과를 제공해주세요.
"""
 
        messages = [
            {"role": "system", "content": EVALUATOR_SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ]
 
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0,
                response_format={"type": "json_object"}
            )
 
            result = json.loads(response.choices[0].message.content)
 
            # 결과 검증 및 기본값 설정
            return {
                "verdict": result.get("verdict", "ERROR"),
                "issue_type": result.get("issue_type"),
                "severity": result.get("severity"),
                "expected_output": result.get("expected_output", ""),
                "suggestion": result.get("suggestion", ""),
                "target_agent": result.get("target_agent"),
                "affected_file": result.get("affected_file")
            }
 
        except json.JSONDecodeError as e:
            return self._error_response(f"JSON 파싱 오류: {str(e)}")
        except Exception as e:
            return self._error_response(f"평가 중 오류 발생: {str(e)}")
 
    def _error_response(self, message: str) -> Dict[str, Any]:
        """에러 응답 생성"""
        return {
            "verdict": "ERROR",
            "issue_type": None,
            "severity": None,
            "expected_output": "",
            "suggestion": message,
            "target_agent": None,
            "affected_file": None
        }
 
    async def batch_evaluate(
        self,
        conversations: list
    ) -> list:
        """
        여러 대화를 일괄 평가
 
        Args:
            conversations: [{"user_input": str, "bot_output": str, "turn": int, "context": dict}, ...]
 
        Returns:
            평가 결과 리스트
        """
        results = []
        for conv in conversations:
            result = await self.evaluate(
                user_input=conv["user_input"],
                bot_output=conv["bot_output"],
                conversation_turn=conv.get("turn", 1),
                context=conv.get("context", {})
            )
            results.append(result)
        return results