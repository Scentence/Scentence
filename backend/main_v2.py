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
        text = re.sub(r'```json\s*', '', text, flags=re.IGNORECASE)
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
    user_responses: list[str] | None  # 사용자 응답 저장
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
    """명확화 질문 생성"""
    
    prompt = f"""'{state['user_query']}'에 대해 3개 명확화 질문을 생성하세요. 
    
    반드시 다음 JSON 형식으로만 응답하세요:
    {{
        "questions": ["질문1", "질문2", "질문3"]
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
                "questions": []
            }
        )
        
        return {
            "clarification_questions": questions.get("questions", []),
            "route": "user_input"  # 사용자 입력을 받기 위해 라우팅 변경
        }
    except Exception as e:
        print(f"Interviewer 오류: {e}")
        return {
            "clarification_questions": [],
            "route": "researcher"  # 오류 시 바로 researcher로
        }

# User Input Collector
def user_input_collector(state: State) -> State:
    """사용자에게 질문을 보여주고 응답을 받음"""
    
    questions = state.get("clarification_questions", [])
    
    if not questions:
        # 질문이 없으면 바로 researcher로
        return {
            "user_responses": [],
            "clarified_query": state['user_query'],
            "route": "researcher"
        }
    
    print("\n[명확화 질문]")
    print("-" * 60)
    user_responses = []
    
    for i, question in enumerate(questions, 1):
        print(f"\n질문 {i}: {question}")
        # 실제 환경에서는 input()을 사용하지만, 테스트를 위해 자동 응답 생성
        # 사용자 응답을 시뮬레이션하기 위해 LLM을 사용
        try:
            response_prompt = f"""사용자 질문: "{state['user_query']}"
            명확화 질문: "{question}"

            위 명확화 질문에 대한 간단한 답변을 생성하세요. (한 문장 이내)"""
            
            response_message = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": response_prompt}],
                max_tokens=100
            )
            
            response = response_message.choices[0].message.content.strip()
            user_responses.append(response)
            print(f"답변: {response}")
        except Exception as e:
            print(f"응답 생성 오류: {e}")
            user_responses.append("")
    
    print("-" * 60)
    
    # 사용자 응답을 기반으로 clarified_query 생성
    try:
        clarification_prompt = f"""원래 질문: "{state['user_query']}"

        사용자 응답:
        {chr(10).join([f"- {q}: {r}" for q, r in zip(questions, user_responses)])}

        위 정보를 바탕으로 명확화된 질문을 생성하세요. JSON 형식으로 응답하세요:
        {{"clarified_query": "명확화된 질문"}}"""
        
        clarification_message = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": clarification_prompt}],
            max_tokens=200,
            response_format={"type": "json_object"}
        )
        
        clarification_content = clarification_message.choices[0].message.content
        clarification_result = safe_json_parse(
            clarification_content,
            {"clarified_query": state['user_query']}
        )
        
        clarified_query = clarification_result.get("clarified_query", state['user_query'])
    except Exception as e:
        print(f"명확화 쿼리 생성 오류: {e}")
        clarified_query = state['user_query']
    
    return {
        "user_responses": user_responses,
        "clarified_query": clarified_query,
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
    route = state.get("route", "researcher")
    if route == "user_input":
        return "user_input"
    return "researcher"

def route_after_user_input(state: State) -> str:
    return state.get("route", "researcher")

def route_after_researcher(state: State) -> str:
    return state.get("route", "writer")

# 그래프 구성
def build_graph():
    graph = StateGraph(State)
    
    graph.add_node("supervisor", supervisor)
    graph.add_node("interviewer", interviewer)
    graph.add_node("user_input", user_input_collector)
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
    
    graph.add_conditional_edges(
        "interviewer",
        route_after_interviewer,
        {
            "user_input": "user_input",
            "researcher": "researcher"
        }
    )
    
    graph.add_conditional_edges(
        "user_input",
        route_after_user_input,
        {
            "researcher": "researcher"
        }
    )
    
    graph.add_edge("researcher", "writer")
    graph.add_edge("writer", END)
    
    return graph.compile()


if __name__ == "__main__":
    workflow = build_graph()
    graph = workflow.get_graph()

    # 그래프 시각화할때 이코드
    # mermaid_diagram = graph.draw_mermaid()
    # print(mermaid_diagram)
    
    # 시나리오별 테스트 쿼리
    scenario_a_queries = [
        # 시나리오 A: Supervision → Interviewer → User Input → Researcher → Writer
        # (애매하거나 추가 정보가 필요한 질문)
        "향수 추천해줘",
        "좋은 향수 있어?",
        "막 달콤한 건 아닌데, 괜히 마음이 차분해지는 느낌의 향수를 찾고 있어요. 설명이 맞는지는 모르겠어요.",
        "이게 시원한 향인지 포근한 향인지도 잘 모르겠고… 그냥 너무 튀지 않았으면 좋겠는데 그런 게 있나요?"
    ]
    
    scenario_b_queries = [
        # 시나리오 B: Supervision → Researcher → Writer
        # (충분한 정보가 있어서 바로 조사 가능한 질문)
        "여름에 시원하게 느껴지는 시트러스 계열 향수 추천해줘",
        "30대 남성용 비즈니스 향수 추천해줘. 가격대는 10만원 이하로",
        "우디 계열 향수 중에서 지속력이 좋은 것 추천해줘",
        "데이트용으로 사용할 달콤한 플로럴 향수 추천해줘"
    ]
    
    scenario_c_queries = [
        # 시나리오 C: Supervision → Writer
        # (검색이나 조사가 필요 없는 단순 질문)
        "향수는 어떻게 뿌리나요?",
        "향수의 노트가 뭔가요?",
        "EDP와 EDT의 차이가 뭔가요?",
        "향수를 오래 지속시키는 방법은?",
        "향수를 어디에 뿌리면 좋나요?"
    ]
    
    all_queries = [
        ("시나리오 A (Interviewer 경로)", scenario_a_queries[0]),
        ("시나리오 B (Researcher 경로)", scenario_b_queries[0]),
        ("시나리오 C (Writer 경로)", scenario_c_queries[0]),
    ]
    
    for scenario_name, query in all_queries:
        print(f"\n{'='*60}")
        print(f"[{scenario_name}]")
        print(f"Query: {query}")
        print('='*60)
        try:
            result = workflow.invoke({"user_query": query})
            print(f"\n[최종 응답]")
            print(f"{result['final_response']}")

            print(f"\n[경로 확인]")
            if result.get('clarification_questions'):
                print(f"- Interviewer 경로 사용됨 (명확화 질문 생성)")
            if result.get('research_result'):
                print(f"- Researcher 경로 사용됨 (조사 수행)")
            print(f"- Writer 경로 사용됨 (최종 응답 생성)")
            
        except Exception as e:
            print(f"\n오류 발생: {e}")
            import traceback
            traceback.print_exc()