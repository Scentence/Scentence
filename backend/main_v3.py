# -*- coding: utf-8 -*- 
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
    conversation_history: list[dict] | None  # 대화 이력
    clarified_query: str | None
    research_result: str | None
    final_response: str

client = OpenAI()

# Supervisor
def supervisor(state: State) -> State:
    """질문 분석 후 라우트 결정"""
    
    prompt = f"""사용자 질문을 분석하세요:
    "{state['user_query']}"
    
    다음 중 하나만 선택:
    - interviewer: 질문이 애매하거나 추가 정보가 필요한 경우
    - researcher: 질문이 명확하고 조사가 필요한 경우
    - writer: 단순한 사실 질문으로 바로 답변 가능한 경우
    
    반드시 JSON 형식으로만 응답하세요: {{"route": "interviewer"}} 또는 {{"route": "researcher"}} 또는 {{"route": "writer"}}
    """
    
    try:
        message = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
            response_format={"type": "json_object"}
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
        return {"route": "researcher"}

# Interviewer - 사용자와 대화하며 충분한 정보 수집
def interviewer(state: State) -> State:
    """사용자와 대화하며 정보를 수집하고, 충분한 정보가 모이면 researcher로 이동"""
    
    conversation_history = state.get("conversation_history", [])
    max_turns = 3  # 최대 대화 턴 수
    
    print("\n" + "="*60)
    print("[대화형 정보 수집 시작]")
    print("="*60)
    
    for turn in range(max_turns):
        print(f"\n--- 대화 턴 {turn + 1}/{max_turns} ---")
        
        # 1. 현재까지의 정보로 충분한지 판단
        if conversation_history:
            conversation_text = "\n".join([f"Q: {item['question']}\nA: {item['answer']}" for item in conversation_history])
            
            sufficiency_prompt = f"""원래 질문: "{state['user_query']}"

대화 이력:
{conversation_text}

위 정보만으로 사용자에게 향수를 추천하기에 충분한가요?

JSON 형식으로 응답하세요:
{{
    "is_sufficient": true 또는 false,
    "reason": "판단 이유"
}}"""
            try:
                sufficiency_message = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": sufficiency_prompt}],
                    max_tokens=150,
                    response_format={"type": "json_object"}
                )
                
                sufficiency_result = safe_json_parse(
                    sufficiency_message.choices[0].message.content,
                    {"is_sufficient": False}
                )
                
                if sufficiency_result.get("is_sufficient", False):
                    print(f"\n[정보 수집 완료] {sufficiency_result.get('reason', '')}")
                    break
            except Exception as e:
                print(f"충분성 판단 오류: {e}")
        
        # 2. 추가 질문 생성
        conversation_context = ""
        if conversation_history:
            conversation_text = "\n".join([f"Q: {item['question']}\nA: {item['answer']}" for item in conversation_history])
            conversation_context = f"\n기존 대화:\n{conversation_text}\n"
        
        question_prompt = f"""원래 질문: "{state['user_query']}"
{conversation_context}
향수 추천에 필요한 핵심 정보를 얻기 위한 명확화 질문 1개를 생성하세요.

JSON 형식으로 응답하세요:
{{
    "question": "명확화 질문"
}}"""
        
        try:
            question_message = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": question_prompt}],
                max_tokens=150,
                response_format={"type": "json_object"}
            )
            
            question_result = safe_json_parse(
                question_message.choices[0].message.content,
                {"question": "어떤 향을 선호하시나요?"}
            )
            
            question = question_result.get("question", "어떤 향을 선호하시나요?")
            print(f"\n질문: {question}")
            
            #-----------------------------------------------------------------
            # 3. 사용자 응답 받기 (실제 응답 받는걸로 바꾸어야함)
            answer_prompt = f"""사용자 원래 질문: "{state['user_query']}"
            명확화 질문: "{question}"

            위 명확화 질문에 대한 간단하고 자연스러운 답변을 생성하세요. (1-2문장)"""
            
            answer_message = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": answer_prompt}],
                max_tokens=100
            )
            
            answer = answer_message.choices[0].message.content.strip()
            print(f"답변: {answer}")
            #-----------------------------------------------------------------
            
            # 대화 이력에 추가
            conversation_history.append({
                "question": question,
                "answer": answer
            })
            
        except Exception as e:
            print(f"질문 생성/응답 오류: {e}")
            break
    
    # 4. 명확화된 쿼리 생성
    try:
        conversation_text = "\n".join([f"Q: {item['question']}\nA: {item['answer']}" for item in conversation_history])
        
        clarified_prompt = f"""원래 질문: "{state['user_query']}"

대화 내용:
{conversation_text}

위 대화를 바탕으로 구체적이고 명확한 향수 추천 요청문을 작성하세요.

JSON 형식으로 응답하세요:
{{
    "clarified_query": "명확화된 질문"
}}"""
        
        clarified_message = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": clarified_prompt}],
            max_tokens=200,
            response_format={"type": "json_object"}
        )
        
        clarified_result = safe_json_parse(
            clarified_message.choices[0].message.content,
            {"clarified_query": state['user_query']}
        )
        
        clarified_query = clarified_result.get("clarified_query", state['user_query'])
        print(f"\n[명확화된 쿼리] {clarified_query}")
        
    except Exception as e:
        print(f"명확화 쿼리 생성 오류: {e}")
        clarified_query = state['user_query']
    
    print("="*60 + "\n")
    
    return {
        "conversation_history": conversation_history,
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
    """Supervisor 후 라우팅"""
    route = state.get("route", "researcher")
    if route not in ["interviewer", "researcher", "writer"]:
        return "researcher"
    return route

# 그래프 구성
def build_graph():
    """
    간소화된 그래프 구조:
    START → Supervisor → [interviewer | researcher | writer] → researcher → writer → END
    
    - interviewer: 사용자와 대화하며 정보 수집 (내부에서 여러 턴 처리)
    - researcher: 명확한 질문에 대해 조사 수행
    - writer: 단순 질문에 직접 답변 또는 최종 응답 생성
    """
    graph = StateGraph(State)
    
    # 노드 추가
    graph.add_node("supervisor", supervisor)
    graph.add_node("interviewer", interviewer)
    graph.add_node("researcher", researcher)
    graph.add_node("writer", writer)
    
    # 엣지 연결
    graph.add_edge(START, "supervisor")
    
    # Supervisor 후 조건부 분기
    graph.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {
            "interviewer": "interviewer",  # 대화 필요
            "researcher": "researcher",     # 바로 조사
            "writer": "writer"              # 바로 답변
        }
    )
    
    # Interviewer → Researcher (정보 수집 완료 후)
    graph.add_edge("interviewer", "researcher")
    
    # Researcher → Writer (조사 완료 후)
    graph.add_edge("researcher", "writer")
    
    # Writer → END (최종 응답 완료)
    graph.add_edge("writer", END)
    
    return graph.compile()


if __name__ == "__main__":
    workflow = build_graph()
    graph = workflow.get_graph()

    # 그래프 시각화
    mermaid_diagram = graph.draw_mermaid()
    print(mermaid_diagram)
    
    # 시나리오별 테스트 쿼리
    scenario_a_queries = [
        # 시나리오 A: Supervisor → Interviewer → Researcher → Writer
        # (애매하거나 추가 정보가 필요한 질문 - 대화를 통해 정보 수집)
        "향수 추천해줘",
        "좋은 향수 있어?",
    ]
    
    scenario_b_queries = [
        # 시나리오 B: Supervisor → Researcher → Writer
        # (충분한 정보가 있어서 바로 조사 가능한 질문)
        "여름에 시원하게 느껴지는 시트러스 계열 향수 추천해줘",
        "30대 남성용 비즈니스 향수 추천해줘. 가격대는 10만원 이하로",
    ]
    
    scenario_c_queries = [
        # 시나리오 C: Supervisor → Writer
        # (검색이나 조사가 필요 없는 단순 질문)
        "향수는 어떻게 뿌리나요?",
        "EDP와 EDT의 차이가 뭔가요?",
    ]
    
    # 각 시나리오별로 하나씩 테스트
    all_queries = [
        ("시나리오 A (Interviewer 경로)", scenario_a_queries[0]),
        ("시나리오 B (Researcher 경로)", scenario_b_queries[0]),
        ("시나리오 C (Writer 경로)", scenario_c_queries[0]),
    ]
    
    for scenario_name, query in all_queries:
        print(f"\n{'='*80}")
        print(f"[{scenario_name}]")
        print(f"Query: {query}")
        print('='*80)
        
        try:
            result = workflow.invoke({"user_query": query})
            
            print(f"\n{'='*80}")
            print("[최종 응답]")
            print('='*80)
            print(f"{result['final_response']}")
            
            print(f"\n{'='*80}")
            print("[경로 확인]")
            print('='*80)
            if result.get('conversation_history'):
                print(f"- Interviewer 경로 사용됨 (대화 {len(result['conversation_history'])}턴)")
            if result.get('research_result'):
                print(f"- Researcher 경로 사용됨 (조사 수행)")
            print(f"- Writer 경로 사용됨 (최종 응답 생성)")
            
        except Exception as e:
            print(f"\n오류 발생: {e}")
            import traceback
            traceback.print_exc()