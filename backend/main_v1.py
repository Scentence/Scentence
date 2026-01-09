from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict, Literal
from openai import OpenAI
import json
import re

from dotenv import load_dotenv
load_dotenv()

# 안전한 JSON 파싱 함수 추가
def safe_json_parse(text: str, default=None):
    """JSON 파싱을 안전하게 처리 - 마크다운 코드 블록이나 설명 텍스트 제거"""
    if not text or not text.strip():
        return default
    
    try:
        # 마크다운 코드 블록 제거
        text = re.sub(r'n\s*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'```\s*', '', text)
        text = text.strip()
        
        # JSON 객체 부분만 추출 (중괄호로 시작하고 끝나는 부분)
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        
        # 직접 파싱 시도
        return json.loads(text)
    except (json.JSONDecodeError, AttributeError, ValueError) as e:
        print(f"JSON 파싱 오류: {e}, 원본 텍스트: {text[:100]}")
        return default

# State 정의
class State(TypedDict):
    user_query: str
    route: Literal["interviewer", "researcher", "writer"]
    clarification_questions: list[str] | None
    clarified_query: str | None
    research_result: str | None
    final_response: str

client = OpenAI()

# Supervisor
def supervisor(state: State) -> State:
    """질문 분석 후 라우트 결정"""
    
    prompt = f"""사용자 질문을 분석하세요:
    "{state['user_query']}"
    
    다음 중 하나만 선택: interviewer, researcher, writer
    
    반드시 JSON 형식으로만 응답하세요: {{"route": "interviewer"}} 또는 {{"route": "researcher"}} 또는 {{"route": "writer"}}
    """
    
    try:
        message = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
            response_format={"type": "json_object"}  # JSON 모드 강제
        )
        
        content = message.choices[0].message.content
        result = safe_json_parse(content, {"route": "researcher"})
        
        route = result.get("route", "researcher")
        
        # 유효한 라우트인지 검증
        if route not in ["interviewer", "researcher", "writer"]:
            print(f"경고: 잘못된 라우트 '{route}', 기본값 'researcher' 사용")
            route = "researcher"
        
        return {"route": route}
    except Exception as e:
        print(f"Supervisor 오류: {e}")
        return {"route": "researcher"}  # 기본값

# Interviewer
def interviewer(state: State) -> State:
    """추가 정보 수집"""
    
    prompt = f"""'{state['user_query']}'에 대해 3개 명확화 질문을 생성하세요. 
    
    반드시 다음 JSON 형식으로만 응답하세요:
    {{
        "questions": ["질문1", "질문2", "질문3"],
        "clarified_query": "명확화된 질문"
    }}
    """
    
    try:
        message = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            response_format={"type": "json_object"}  # JSON 모드 강제
        )
        
        content = message.choices[0].message.content
        questions = safe_json_parse(
            content, 
            {
                "questions": [],
                "clarified_query": state['user_query']
            }
        )
        
        return {
            "clarification_questions": questions.get("questions", []),
            "clarified_query": questions.get("clarified_query", state['user_query']),
            "route": "researcher"
        }
    except Exception as e:
        print(f"Interviewer 오류: {e}")
        return {
            "clarification_questions": [],
            "clarified_query": state['user_query'],
            "route": "researcher"
        }

# Researcher
def researcher(state: State) -> State:
    """조사 수행"""
    
    query = state.get("clarified_query") or state["user_query"]
    prompt = f"'{query}'에 대해 조사하고 관련 정보를 수집하세요."
    
    try:
        message = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800
        )
        
        return {
            "research_result": message.choices[0].message.content,
            "route": "writer"
        }
    except Exception as e:
        print(f"Researcher 오류: {e}")
        return {
            "research_result": "조사 중 오류가 발생했습니다.",
            "route": "writer"
        }

# Writer
def writer(state: State) -> State:
    """최종 응답 생성"""
    
    context = f"""
    질문: {state['user_query']}
    {f"명확화: {state.get('clarified_query', '')}" if state.get('clarified_query') else ""}
    {f"조사: {state.get('research_result', '')}" if state.get('research_result') else ""}
    """
    
    prompt = f"다음 정보로 명확하고 도움이 되는 최종 응답을 작성하세요:\n{context}"
    
    try:
        message = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000
        )
        
        return {"final_response": message.choices[0].message.content}
    except Exception as e:
        print(f"Writer 오류: {e}")
        return {"final_response": "응답 생성 중 오류가 발생했습니다."}

# 라우팅 함수
def route_after_supervisor(state: State) -> str:
    route = state.get("route", "researcher")
    # 유효성 검증
    if route not in ["interviewer", "researcher", "writer"]:
        return "researcher"
    return route

def route_after_interviewer(state: State) -> str:
    return state.get("route", "researcher")

def route_after_researcher(state: State) -> str:
    return state.get("route", "writer")

# 그래프 구성
def build_graph():
    graph = StateGraph(State)
    
    graph.add_node("supervisor", supervisor)
    graph.add_node("interviewer", interviewer)
    graph.add_node("researcher", researcher)
    graph.add_node("writer", writer)
    
    graph.add_edge(START, "supervisor")
    
    graph.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {
            "interviewer": "interviewer",
            "researcher": "researcher",
            "writer": "writer"
        }
    )
    
    graph.add_edge("interviewer", "researcher")
    graph.add_edge("researcher", "writer")
    graph.add_edge("writer", END)
    
    return graph.compile()


if __name__ == "__main__":
    workflow = build_graph()
    
    queries = [
        "막 달콤한 건 아닌데, 괜히 마음이 차분해지는 느낌의 향수를 찾고 있어요. 설명이 맞는지는 모르겠어요.",
        "이게 시원한 향인지 포근한 향인지도 잘 모르겠고… 그냥 너무 튀지 않았으면 좋겠는데 그런 게 있나요?",
        "향수는 잘 모르겠어서요. 그냥 무난한 거 하나 추천해주시면 써볼게요."
    ]
    
    for query in queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print('='*60)
        try:
            result = workflow.invoke({"user_query": query})
            print(f"\nResponse:\n{result['final_response']}")
        except Exception as e:
            print(f"\n오류 발생: {e}")