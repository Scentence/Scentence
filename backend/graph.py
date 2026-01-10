import json
import traceback
import re
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver 
from schemas import State
from database import METADATA
from tools import (
    client, 
    safe_json_parse, 
    execute_precise_search, 
    search_notes_vector, 
    search_exact_entity
)

# ==========================================
# ⚙️ 모델 설정
# ==========================================
FAST_MODEL = "gpt-4o"
HIGH_PERFORMANCE_MODEL = "gpt-5.2" 

# ==========================================
# 1. Supervisor (라우터)
# ==========================================


# graph.py 의 supervisor 함수 교체

def supervisor(state: State) -> State:
    try:
        query = state["user_query"]
        
        print(f"\n📡 [Supervisor] 입력: '{query}'", flush=True)
        
        prompt = f"""
        당신은 대화 흐름을 제어하는 관리자입니다.
        
        [입력]
        - 사용자 발화: "{query}"
        
        [판단 기준]
        1. **researcher (즉시 검색)**:
           - **[주의]** 문맥 없이도 검색 가능한 **완벽한 요청**일 때만 선택하세요.
           - 예: "조말론의 우디한 향수 추천해줘", "20대 여자가 쓸 장미향 향수"
           
        2. **interviewer (문맥 업데이트 및 질문)**:
           - **대부분의 경우는 이곳입니다.**
           - **짧은 답변/속성**: "귀여운 편이야", "시크해", "우디한 거", "20대" 등 사용자의 취향이나 특성을 나타내는 단어가 있으면 무조건 선택하세요.
           - **불완전한 요청**: "조말론 추천해줘" (어떤 향?)
           - **이유**: 이전 대화의 문맥(Brand 등)과 합치기 위해서입니다.
           
        3. **writer (잡담/종료)**:
           - 향수와 전혀 상관없는 인사("안녕"), 시스템 불만, 종료 요청.
           - **[중요] 애매하면 무조건 'interviewer'로 보내세요.**
        
        응답(JSON): {{"route": "interviewer" | "researcher" | "writer"}}
        """
        
        msg = client.chat.completions.create(
            model=FAST_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        route = safe_json_parse(msg.choices[0].message.content).get("route", "writer")
        
        print(f"   🚦 결정된 경로: {route}", flush=True)
        return {"route": route}
        
    except Exception:
        print("\n🚨 [Supervisor Error]", flush=True)
        traceback.print_exc()
        return {"route": "writer"}
    
    
def interviewer(state: State) -> State:
    try:
        query = state["user_query"]
        current_context = state.get("interview_context", "") or ""
        
        print(f"\n🎤 [Interviewer] 답변 분석 및 문맥 업데이트", flush=True)
        
        # 1. 정보 추출 (이미지/분위기 강조)
        extraction_prompt = f"""
        사용자 답변에서 향수 추천 정보를 있는 그대로 요약하세요.
        
        [핵심 지침]
        1. **이미지/분위기 포착**: 사용자가 '향'을 몰라도 '이미지(시크, 차가움, 러블리 등)'를 말했으면 반드시 기록하세요.
        2. **팩트 체크**: 사용자의 입력에 없는 내용은 절대 추측해서 적지 마세요.
        3. **형식**: "브랜드: OOO, 이미지: OOO, 취향: 정보 없음, 대상: OOO"
        
        - 기존 정보: {current_context}
        - 사용자 답변: {query}
        """
        msg = client.chat.completions.create(
            model=FAST_MODEL,
            messages=[{"role": "user", "content": extraction_prompt}]
        )
        updated_context = msg.choices[0].message.content
        print(f"   👉 업데이트된 정보: {updated_context}", flush=True)
        
        # 2. 판단 및 질문 생성 (유연한 판단 & 논리적 질문)
        judge_prompt = f"""
        현재 수집된 정보가 추천 검색을 시작하기에 충분한지 판단하세요.
        
        [판단 기준 - 유연함]
        1. **충분함(true)**: 
           - 구체적인 '향(Note)'을 몰라도, **명확한 '이미지/분위기'(예: 시크, 차가움, 도도함)**가 있다면 **충분**하다고 판단하세요. (Researcher가 이미지로 검색 가능함)
           - 브랜드와 대상만 있고 아무런 힌트가 없을 때만 '불충분'입니다.
           
        2. **부족함(false)**: 
           - 정말 아무런 단서(향도 모르고 이미지도 말 안 함)가 없을 때.
        
        [★질문 작성 가이드 - 문맥 유지 (Context Awareness)★]
        만약 질문이 필요하다면, **사용자가 방금 한 말**을 반영해서 물어보세요. (동문서답 금지)
        
        **Case A. 사용자가 '차가운/시크한' 이미지를 언급했는데 모호할 때:**
        - (나쁜 예): "따뜻한 커피 향은 어떠세요?" (사용자 말 무시)
        - (좋은 예): "**차가운 이미지**라고 하셨군요! 구체적으로 **도시적이고 날카로운 차가움(모던)**인가요, 아니면 **새벽 숲속 같은 서늘한 차가움(우디)**인가요?"
        
        **Case B. 전혀 정보가 없을 때:**
        - "평소 그분의 패션 스타일이나 분위기가 어떤가요? (예: 귀여운 편, 시크한 편)"
        
        정보: {updated_context}
        
        응답(JSON): 
        {{
            "is_sufficient": true/false, 
            "next_question": "생성된 질문 내용"
        }}
        """
        judge_msg = client.chat.completions.create(
            model=FAST_MODEL,
            messages=[{"role": "user", "content": judge_prompt}],
            response_format={"type": "json_object"}
        )
        judge_result = safe_json_parse(judge_msg.choices[0].message.content)
        
        if judge_result.get("is_sufficient"):
            print("   ✅ 정보 충분(이미지/취향 포함됨) -> Researcher로 전달", flush=True)
            return {
                "route": "researcher", 
                "interview_context": updated_context,
                "user_query": f"{updated_context} (사용자 의도 반영)" 
            }
        else:
            print("   ❓ 정보 부족 -> 사용자에게 재질문", flush=True)
            return {
                "route": "end",
                "interview_context": updated_context,
                "final_response": judge_result.get("next_question")
            }
            
    except Exception:
        print("\n🚨 [Interviewer Error]", flush=True)
        traceback.print_exc()
        return {"route": "writer", "final_response": "잠시 문제가 생겼습니다. 다시 말씀해 주시겠어요?"}

# ==========================================
# 3. Researcher (전략 수립) - 의도 중심 전략명 생성
# ==========================================
def researcher(state: State) -> State:
    try:
        query = state["user_query"]
        print(f"\n🕵️ [Researcher] 명시적 조건 추출 및 다차원 전략 수립: {query}", flush=True)

        meta_summary = {k: v[:20] for k, v in METADATA.items()}

        prompt = f"""
        당신은 '퍼퓸 디렉터'입니다. 사용자 요청("{query}")을 분석해 3가지 검색 전략을 수립하세요.
        
        === [★불변의 제 1원칙: 고유명사 영어 변환★] ===
        1. 브랜드(예: "샤넬") -> `filters`에 `{{'column': 'brand', 'value': 'Chanel'}}` 필수.
        2. 성별 -> `filters`에 `Feminine` / `Masculine` 필수.
        3. 키워드 -> `note_keywords`에 넣을 때는 반드시 **영어(English)**로 변환.

        === [★검색 안정성 규칙 (Search Safety) - 필독★] ===
        **문제 상황**: 추상적인 요청에 대해 임의의 노트를 `filters`에 넣으면 결과가 0개가 됩니다.
        
        **[절대 금지]**: 
        - 사용자가 **직접 언급하지 않은 재료(노트)**를 상상해서 `filters`의 `note` 컬럼에 넣지 마세요.
        - 예: 사용자가 "우아한 향"이라고만 했는데 `filters`에 `['Rose', 'Peony']`를 넣으면 **검색 실패**로 이어집니다.
        
        **[올바른 방법]**:
        - **이미지/분위기 요청 시** (예: "우아한", "시크한"):
          - `filters`에는 **브랜드**와 **성별**만 넣으세요.
          - 분위기를 나타내는 단어(예: "Elegant", "Floral", "Clean")는 **`note_keywords`**에 넣고 `use_vector_search: true`를 켜세요. (벡터 검색이 알아서 찾아줍니다.)
          
        - **구체적 재료 언급 시** (예: "장미 향", "비누 향"):
          - 이때만 `note_keywords`나 `filters`에 "Rose", "Soap" 등을 명시적으로 넣으세요.

        === [★다양성 전략 & 네이밍 규칙 (쉬운 한국어)★] ===
        **1. 네이밍 스타일 가이드**
        - **[금지]**: '플로럴', '우디', '머스크' 등 전문 용어 금지. '정석', '끝판왕' 등 과한 수식어 금지.
        - **[권장]**: **"꽃향기"**, **"나무 향"**, **"살냄새"**, **"과일 향"** 등 쉬운 우리말 사용.
        
        **2. 전략 수립 예시**
        - Plan 1: "**차분한 꽃향기에 더해진 비누 향**" (직관)
        - Plan 2: "**화려함 뒤에 숨겨진 차분한 반전**" (반전)
        - Plan 3: "**과일 향을 더해 산뜻하게 마무리**" (보완)

        === [작성 규칙] ===
        1. 3개의 Plan을 작성하세요.
        2. `strategy_name`은 위 규칙을 지켜 **쉬운 한국어**로 작성하세요.
        3. **[중요]**: "우아한 조말론" 같은 요청에는 `filters`에 노트를 넣지 말고, `note_keywords`를 활용하세요.
        
        응답(JSON) 예시:
        {{
            "scenario_type": "Type A (Abstract Image)",
            "plans": [
                {{
                    "priority": 1,
                    "strategy_name": "차분하고 우아한 꽃향기",
                    "filters": [
                        {{"column": "brand", "value": "Jo Malone London"}},
                        {{"column": "gender", "value": "Feminine"}}
                        // 노트 필터 없음! (벡터 검색에 맡김)
                    ],
                    "note_keywords": ["Elegant", "Floral", "Clean"],
                    "use_vector_search": true
                }}
            ]
        }}
        """
        
        msg = client.chat.completions.create(
            model=HIGH_PERFORMANCE_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        parsed = safe_json_parse(msg.choices[0].message.content)
        plans = parsed.get("plans", []) if parsed else []
        scenario_type = parsed.get("scenario_type", "Unknown")
        
        print(f"   💡 선택된 시나리오: {scenario_type}", flush=True)
        
        search_logs = []
        final_result_text = ""
        
        for plan in plans:
            priority = plan.get('priority', '?')
            strategy = plan.get('strategy_name', f"Strategy-{priority}")
            
            print(f"   👉 [Priority {priority}] 실행: {strategy}", flush=True)
            
            current_filters = []
            
            for f in plan.get("filters", []):
                if not isinstance(f, dict):
                    print(f"   ⚠️ [Warning] 잘못된 필터 형식 무시됨: {f}", flush=True)
                    continue
                    
                col = f.get('column')
                val = f.get('value')
                if not col or not val: continue
                
                # 브랜드/향수명 오타 교정
                if col in ['brand', 'perfume_name']:
                    corrected = search_exact_entity(val, col)
                    if corrected: 
                        if val != corrected:
                            print(f"      🔧 [자동 보정] {val} -> {corrected}")
                        f['value'] = corrected
                
                current_filters.append(f)
            
            notes = []
            if plan.get("use_vector_search"):
                notes.extend(search_notes_vector(query, top_k=3))
            
            for k in plan.get("note_keywords", []):
                notes.extend(search_notes_vector(k, top_k=2))
                
            if notes:
                current_filters.append({"column": "note", "value": list(set(notes))})
            
            # 검색 실행
            result_text = execute_precise_search(current_filters)
            
            if result_text:
                print(f"     ✅ 결과 확보", flush=True)
                search_logs.append(f"전략 [{strategy}] 성공")
                final_result_text += f"\n=== [전략: {strategy}] ===\n{result_text}\n"
            else:
                print(f"     ❌ 결과 없음", flush=True)
                search_logs.append(f"전략 [{strategy}] 결과 없음")
        
        if not final_result_text:
            final_result_text = "검색 결과가 없습니다."

        return {
            "search_plans": plans,
            "search_logs": search_logs,
            "research_result": final_result_text,
            "route": "writer"
        }
        
    except Exception:
        print("\n🚨 [Researcher Error]", flush=True)
        traceback.print_exc()
        return {"research_result": "오류 발생", "route": "writer"}


# ==========================================
# 4. Writer (글쓰기) - 1전략 1향수 & 의도 설명
# ==========================================
def writer(state: State) -> State:
    try:
        print("✍️ [Writer] 답변 작성", flush=True)
        query = state["user_query"]
        result = state.get("research_result", "")
        
        prompt = f"""
        당신은 향수를 잘 모르는 초보자를 위한 세상에서 가장 친절한 향수 컨설턴트입니다.
        
        [사용자 요청]: "{query}"
        
        [검색된 향수 데이터]: 
        {result}
        
        [작성 규칙 - 필독]
        0. **검색결과에 따른 출력**:
           - 검색 결과가 없다면 반드시 검색된 결과가 없음을 알리고 다른 검색용 쿼리로 만들수 있을만한 질문을 던질 것.
           - 절대로 임의의 향수를 추천하지 않을 것.

        1. **[★1전략 1향수 원칙★]**: 
           - 검색 결과에 여러 향수가 있더라도, **각 전략(Strategy) 당 가장 적합한 향수 딱 1개만** 선정하세요.
           - 결과적으로 총 3개의 향수만 추천되어야 합니다. (중복 추천 금지)
        
        2. **목차 스타일 (전략 의도 강조)**: 
           - 형식: **`## 번호. [전략이름] 브랜드 - 향수명`**
           - **[전략이름]**에는 Researcher가 정한 전략명(예: "겉차속따 반전 매력")을 그대로 넣으세요.
           - 예시: `## 1. [차가운 첫인상 속 따뜻한 반전] Chanel - Coco Noir`
        
        3. **이미지 필수**: `![향수명](이미지링크)`
        
        4. **[★매우 중요★] 서식 및 강조 규칙**:
           - **항목 제목(Label)**: 반드시 **`_` (언더바)**로 감싸세요. (파란색 제목)
             - 예: `_어떤 향인가요?_`, `_추천 이유_`, `_정보_`
           - **내용 강조(Highlight)**: 핵심 단어는 **`**` (별표 2개)**로 감싸세요. (핑크색 강조)
             - 예: `처음엔 **상큼한 귤 향**이 나요.`
        
        5. **구분선**: 향수 추천 사이에 `---` 삽입.
        
        6. **정보 표기**: 브랜드, 이름, 출시년도만 기재.
        
        7. **[★필수★] 향 설명 방식 (용어 절대 금지)**:
           - **[절대 금지]**: '탑', '미들', '베이스', '노트', '어코드'라는 단어나 `(탑)`, `(미들)` 같은 괄호 표기를 **절대** 쓰지 마세요.
           - **[작성법]**: 시간의 흐름을 자연스러운 문장으로만 표현하세요.
           - **[예외상황]**:탑/미들/베이스의 노트가 모두 동일할 경우 전체적으로 ~~ 향이 지속된다는 식으로 설명하세요
           - *Bad*: "처음에는 레몬 향이 나요(탑)."
           - *Good*: "처음에는 **막 짠 레몬즙**처럼 상큼하게 시작해요. 시간이 지나면..."
           
        8. **[핵심] 추천 논리 연결 (Why?)**:
           - `_추천 이유_`를 작성할 때, **"왜 이 전략(반전/직관 등)으로 이 향수를 뽑았는지"** 설명하세요.
           - 과한 마케팅 문구(예: "정석", "끝판왕", "감히 추천") 대신 **담백하고 논리적으로** 설득하세요.
           - *Bad*: "시크함의 정석이라 감히 추천드려요."
           - *Good*: "고객님이 **시크한 이미지**를 원하셨죠? 이 향은 **단맛 없이 건조한 나무 향**이라 깔끔하고 도시적인 느낌을 주기에 가장 적합해요."

        9. **[매우 중요] 묘사 및 강조 규칙**:
            - **전문 용어 금지**: 노트, 어코드, 탑/미들/베이스 등은 쓰지 마세요.
            - **쉬운 우리말 번역**: "비에 젖은 나무", "포근한 이불 냄새"처럼 오감이 느껴지게 쓰세요.
            - **★핵심 강조(필수)★**:
            - 향을 묘사하는 **핵심 키워드**나 **비유 표현**은 반드시 **굵게(`**...**`)** 처리하세요.
            - 예: "처음엔 **상큼한 귤껍질 향**이 나다가, 곧 **따뜻한 향신료 차**처럼 변해요."
        [출력 형식 예시]
        
        안녕하세요! 요청하신 시크한 느낌을 3가지 무드로 해석해봤어요.
        
        ## 1. [날카롭고 정돈된 시크] **Chanel - Sycomore**
        ![Sycomore](링크)
        
        - _어떤 향인가요?_: 처음엔 **비 온 뒤의 숲**처럼 차갑고 상쾌해요. 시간이 지나면 **마른 장작** 같은 나무 향이 진해지면서 단정하게 마무리돼요.
        - _추천 이유_: 군더더기 없이 **깔끔하고 드라이한 향**이에요. **차가운 도시 이미지**를 가장 직관적으로 표현하고 싶을 때 완벽한 선택이에요.
        - _정보_: Chanel / Sycomore / 2008년 출시
        
        ---
        
        ## 2. [겉차속따 반전 매력] **Chanel - Coco Noir**
        ...
        """
        
        msg = client.chat.completions.create(
            model=HIGH_PERFORMANCE_MODEL, 
            messages=[{"role": "user", "content": prompt}]
        )
        
        raw_content = msg.choices[0].message.content
        
        # [후처리] 강조 공백 제거
        fixed_content = re.sub(r'\*\*\s*(.*?)\s*\*\*', r'**\1**', raw_content)
        
        return {"final_response": fixed_content}
    except Exception:
        print("\n🚨 [Writer Error]", flush=True)
        traceback.print_exc()
        return {"final_response": "답변 생성 중 오류가 발생했습니다."}


# ==========================================
# Graph Build
# ==========================================
def build_graph():
    graph = StateGraph(State)
    
    graph.add_node("supervisor", supervisor)
    graph.add_node("interviewer", interviewer)
    graph.add_node("researcher", researcher)
    graph.add_node("writer", writer)
    
    graph.add_edge(START, "supervisor")
    
    def route_decision(state: State):
        return state["route"]
    
    graph.add_conditional_edges(
        "supervisor",
        route_decision,
        {"interviewer": "interviewer", "researcher": "researcher", "writer": "writer"}
    )
    
    graph.add_conditional_edges(
        "interviewer",
        route_decision,
        {"researcher": "researcher", "end": END}
    )
    
    graph.add_edge("researcher", "writer")
    graph.add_edge("writer", END)
    
    # 메모리 저장소(Checkpointer) 적용
    memory = MemorySaver()
    
    return graph.compile(checkpointer=memory)