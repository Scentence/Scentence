# ====== [ksu] 테스터 ==========
import os
import time  # [추가] time 모듈 임포트
from datetime import datetime

# ============================

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
    search_exact_entity,
)

# ==========================================
# ⚙️ 모델 설정
# ==========================================
FAST_MODEL = "gpt-4o-mini"
HIGH_PERFORMANCE_MODEL = "gpt-4o"

# ==========================================
# 1. Supervisor (라우터)
# ==========================================


# graph.py 의 supervisor 함수 교체


# ==========================================
# 1. Supervisor (라우터) - 하이패스 적용
# ==========================================
def supervisor(state: State) -> State:
    try:
        # [★핵심] 하이패스 로직: 인터뷰어가 마이크를 잡고 있다면 판단 없이 직행!
        active_mode = state.get("active_mode")
        if active_mode == "interviewer":
            print(
                "\n🚀 [Supervisor] 인터뷰 진행 중 -> 판단 생략하고 Interviewer로 직행",
                flush=True,
            )
            return {"route": "interviewer"}

        query = state["user_query"]
        # 문맥 정보 가져오기
        current_context = state.get("interview_context", "정보 없음") or "정보 없음"

        # ============================== [ksu] 테스터 =============================
        test_info = None
        if query.startswith("/t"):
            try:
                matches = re.findall(r"\[(.*?)\]", query)
                if len(matches) >= 3:
                    test_info = {
                        "purpose": matches[0].strip(),
                        "scenario": matches[1].strip(),
                        "expected": matches[2].strip(),
                        "start_time": time.time(),
                    }
                    last_bracket_idx = query.rfind("]")
                    if last_bracket_idx != -1:
                        query = query[last_bracket_idx + 1 :].strip()
                    print(f"🧪 [Test Mode] {test_info}", flush=True)
            except Exception:
                print("⚠️ 파싱 에러 발생", flush=True)
        # ============================== [ksu] 테스터 =============================

        print(f"\n📡 [Supervisor] 입력: '{query}'", flush=True)

        prompt = f"""
        당신은 대화 흐름을 제어하는 관리자입니다.
        
        [현재까지 수집된 정보]
        {current_context}
        
        [현재 입력]
        - 사용자 발화: "{query}"
        
        [판단 기준]
        1. **researcher (즉시 검색)**:
           - **Case A (완벽한 요청)**: "샤넬 장미 향수 추천해줘"처럼 문맥 없이도 검색 가능한 경우.
           - **Case B (승인)**: 위 [수집된 정보]에 이미 (브랜드, 이미지, 향) 중 하나 이상의 정보가 있고, 사용자가 "이제 찾아줘", "응 좋아"라며 동의했을 때.
           
        2. **interviewer (문맥 업데이트 및 질문)**:
           - **[대부분의 경우]**: 새로운 정보(취향, 이미지, 나이 등)를 추가하거나 답변할 때.
           - **정보 누적**: 사용자가 "귀여운 편이야"라고 하면, 기존 정보에 합쳐야 하므로 무조건 Interviewer로 보냅니다.
           - **불완전함**: 정보가 부족하여 더 물어봐야 할 때.
           
        3. **writer (잡담/종료)**:
           - 향수와 전혀 상관없는 인사("안녕"), 시스템 불만, 종료 요청.
           - **[주의]** 애매하면 'interviewer'로 보내세요.
        
        응답(JSON): {{"route": "interviewer" | "researcher" | "writer"}}
        """

        msg = client.chat.completions.create(
            model=FAST_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )

        in_tok = msg.usage.prompt_tokens
        out_tok = msg.usage.completion_tokens
        current_in = state.get("input_tokens", 0) + in_tok
        current_out = state.get("output_tokens", 0) + out_tok

        route = safe_json_parse(msg.choices[0].message.content).get("route", "writer")

        print(f"   🚦 결정된 경로: {route}", flush=True)

        return {
            "route": route,
            "input_tokens": current_in,
            "output_tokens": current_out,
            "user_query": query,
            "test_info": test_info,
        }

    except Exception:
        print("\n🚨 [Supervisor Error]", flush=True)
        traceback.print_exc()
        return {"route": "writer"}


# ==========================================
# 2. Interviewer (문맥 관리 & 모드 제어)
# ==========================================
def interviewer(state: State) -> State:
    try:
        query = state["user_query"]
        current_context = state.get("interview_context", "") or ""

        print(f"\n🎤 [Interviewer] 답변 분석 및 문맥 업데이트", flush=True)

        # 1. 정보 추출 (이미지/분위기 강조)
        extraction_prompt = f"""
        사용자 답변에서 향수 추천 정보를 요약하세요.
        
        [핵심 지침]
        1. **병합(Merge)**: [현재 정보]와 [사용자 입력]을 합쳐서 기록하세요.
        2. **이미지/분위기 포착**: 사용자가 언급한 분위기 키워드만 기록하세요. 
        - **주의**: 지침에 적힌 예시 단어(시크, 러블리 등)를 사용자가 직접 말하지 않았다면 절대로 기록하지 마세요.
        3. **형식**: "브랜드: OOO, 이미지: OOO, 취향: OOO, 대상: OOO"
        
        - 기존 정보: {current_context}
        - 사용자 답변: {query}
        """
        msg = client.chat.completions.create(
            model=FAST_MODEL, messages=[{"role": "user", "content": extraction_prompt}]
        )

        in_tok1 = msg.usage.prompt_tokens
        out_tok1 = msg.usage.completion_tokens
        updated_context = msg.choices[0].message.content
        print(f"   👉 업데이트된 정보: {updated_context}", flush=True)

        # 2. 판단 및 질문 생성
        judge_prompt = f"""
        현재 수집된 정보가 추천 검색을 시작하기에 충분한지 판단하고, 부족하다면 질문을 생성하세요.
        
        [판단 기준]
        1. **충분함(true)**: 
           - 사용자가 구체적인 이미지/분위기를 제시했을 때.
           - **[★동의 확인]**: AI가 "그럼 베스트셀러로 추천할까요?"라고 제안했을 때, 사용자가 **"응", "좋아", "그렇게 해줘"**라고 동의했다면 충분함.
           
        2. **부족함(false)**: 
           - 정보가 부족하거나, 사용자가 "모르겠다"고 했을 때.
        
        [★질문 작성 가이드 - 센스 있는 제안★]
        **Case A. 사용자가 '모르겠다'고 했을 때 (가장 중요)**:
        - 절대 방금 한 질문을 반복하지 마세요.
        - **대안을 제시하고 동의를 구하세요.**
        - 예시: "그럼 호불호 없이 가장 인기 많은 **베스트셀러** 위주로 골라드릴까요?", "선물용으로 가장 무난한 **비누향**이나 **플로럴 계열**은 어떠세요?"
        
        **Case B. 정보가 정말 없을 때**:
        - 평소 스타일이나 이미지를 물어보세요.
        
        **Case C. 사용자가 질문에 답했을 때**:
        - 추가로 필요한 정보(계절, 가격대 등)가 있다면 물어보세요.
        
        정보: {updated_context}
        
        응답(JSON): {{"is_sufficient": true/false, "next_question": "..."}}
        """
        judge_msg = client.chat.completions.create(
            model=FAST_MODEL,
            messages=[{"role": "user", "content": judge_prompt}],
            response_format={"type": "json_object"},
        )

        in_tok2 = judge_msg.usage.prompt_tokens
        out_tok2 = judge_msg.usage.completion_tokens
        total_in = state.get("input_tokens", 0) + in_tok1 + in_tok2
        total_out = state.get("output_tokens", 0) + out_tok1 + out_tok2

        judge_result = safe_json_parse(judge_msg.choices[0].message.content)

        if judge_result.get("is_sufficient"):
            print("   ✅ 정보 충분 -> Researcher로 전달 (마이크 반납)", flush=True)
            return {
                "route": "researcher",
                "interview_context": updated_context,
                "user_query": f"{updated_context} (사용자 의도 반영)",
                "input_tokens": total_in,
                "output_tokens": total_out,
                # [★OFF] 검색하러 가니까 인터뷰 모드 종료!
                "active_mode": None,
            }
        else:
            print("   ❓ 정보 부족 -> 재질문 (마이크 유지)", flush=True)
            return {
                "route": "end",
                "interview_context": updated_context,
                "final_response": judge_result.get("next_question"),
                "input_tokens": total_in,
                "output_tokens": total_out,
                # [★ON] 질문했으니 다음 답변은 내가 바로 받아야 함!
                "active_mode": "interviewer",
            }

    except Exception:
        print("\n🚨 [Interviewer Error]", flush=True)
        traceback.print_exc()
        return {
            "route": "writer",
            "final_response": "잠시 문제가 생겼습니다. 다시 말씀해 주시겠어요?",
            "active_mode": None,
        }


# ==========================================
# 3. Researcher (전략 수립) - 의도 중심 전략명 생성
# ==========================================
from database import get_db_connection


# [2] 메타 데이터(유효 필터 값) 가져오는 헬퍼 함수 추가
def fetch_meta_filters():
    """
    DB에서 현재 존재하는 Season, Occasion, Accord의 유효한 값 목록을 가져옵니다.
    [수정] 테이블 이름 실제 DB(줄임말)에 맞게 변경
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # 1. Season (계절) -> tb_perfume_season_m (이건 줄임말 아님)
        cur.execute(
            "SELECT DISTINCT season FROM tb_perfume_season_m WHERE season IS NOT NULL"
        )
        seasons = [r[0] for r in cur.fetchall()]

        # 2. Occasion (상황) -> [수정] tb_perfume_oca_m (줄임말 적용!)
        cur.execute(
            "SELECT DISTINCT occasion FROM tb_perfume_oca_m WHERE occasion IS NOT NULL"
        )
        occasions = [r[0] for r in cur.fetchall()]

        # 3. Accord (향조) -> tb_perfume_accord_m
        cur.execute(
            "SELECT DISTINCT accord FROM tb_perfume_accord_m WHERE accord IS NOT NULL"
        )
        accords = [r[0] for r in cur.fetchall()]

        conn.close()

        return (
            ", ".join([f"'{s}'" for s in seasons]),
            ", ".join([f"'{o}'" for o in occasions]),
            ", ".join([f"'{a}'" for a in accords]),
        )
    except Exception as e:
        print(f"⚠️ Meta Filter Load Error: {e}")
        # DB 에러 시 기본값 리턴 (봇이 죽지 않도록)
        return (
            "'Spring', 'Summer', 'Fall', 'Winter'",
            "'Daily', 'Formal', 'Date', 'Party'",
            "'Citrus', 'Woody', 'Floral', 'Musk'",
        )


# [3] researcher 함수 교체
def researcher(state: State) -> State:
    try:
        query = state["user_query"]

        # [Re-Act] 현재 재시도 횟수 가져오기 (없으면 0)
        retries = state.get("retry_count", 0)

        # [Re-Act] 재시도 상황에 따른 지침 추가
        retry_instruction = ""
        if retries > 0:
            retry_instruction = f"""
            **[🚨 비상 모드 발동: {retries}번째 재시도 중]**
            이전 전략으로 검색했을 때 **결과가 '0건'**이었습니다.
            이번에는 반드시 결과를 찾기 위해 아래 조치를 취하세요:
            1. **브랜드 제약 삭제**: 특정 브랜드(Chanel 등)를 고집했다면, `filters`에서 브랜드를 과감히 빼세요.
            2. **키워드 확장**: `note_keywords`에 더 일반적인 영어 단어(예: 'Soap', 'Musk')를 추가하세요.
            3. **Type B(특정 조건) -> Type A(이미지)**로 전략 타입을 변경하세요.
            """

        print(f"\n🕵️ [Researcher] DB 전략 수립 (시도: {retries + 1})", flush=True)

        # ★ DB에서 유효한 필터 값 실시간 로딩
        valid_seasons, valid_occasions, valid_accords = fetch_meta_filters()

        prompt = f"""
        당신은 보유한 데이터베이스를 완벽하게 활용하는 '퍼퓸 디렉터'입니다.
        {retry_instruction}
        사용자 요청("{query}")을 분석해 **가장 매력적인 3가지 스타일링 전략**을 수립하세요.
        
        === [1. 보유 데이터 매핑 (Data Mapping)] - ★핵심★ ===
        사용자의 말에서 아래 **[허용된 값 목록]**에 해당하는 정보가 나오면 **반드시 `filters`에 포함**시키세요.
        
        1. **Brand**: 브랜드명 (예: 'Chanel', 'Dior') -> `filters`
        2. **Gender**: 성별 (예: 'Feminine', 'Masculine') -> `filters`
        
        3. **Season (계절)**: 
           - **[허용된 값]**: [{valid_seasons}]
           - 사용자가 "여름"이라고 하면 위 목록 중 'Summer'를 찾아 `{{'column': 'season', 'value': 'Summer'}}`로 설정.
           
        4. **Occasion (상황)**: 
           - **[허용된 값]**: [{valid_occasions}]
           - 사용자가 "데일리"라고 하면 위 목록 중 매칭되는 값을 찾아 `filters`에 설정.
           
        5. **Accord (향조)**: 
           - **[허용된 값]**: [{valid_accords}]
           - 사용자가 "상큼한 시트러스"라고 하면 위 목록 중 'Citrus'를 찾아 `filters`에 설정.

        === [2. 시나리오별 행동 지침] ===
        **Type A. [이미지/분위기]** (예: "시크한", "포근한")
        - 전략: DB 허용 값에 없는 추상적 표현은 `note_keywords`에 넣어 벡터 검색.
        
        **Type B. [특정 조건]** (예: "여름에 뿌릴 시트러스")
        - 전략: **DB 필터링 우선!** (위 허용된 값 목록에 존재한다면 `filters` 사용)
        
        **Type D. [선물/입문]** (예: "여친 선물")
        - 전략: `note_keywords`에 "Soap", "Clean", "Light Floral" 등 호불호 없는 키워드 자동 추가.

        === [3. 전략 수립 프레임워크 (3-Step Styling)] ===
        **Plan 1. [동조 (Harmony)]**: "이미지 직관적 반영"
        **Plan 2. [반전 (Gap)]**: "의외의 매력 포인트"
        **Plan 3. [변화 (Shift)]**: "입체적 밸런스"

        === [4. 작성 규칙] ===
        1. `strategy_name`은 **"꽃향기", "비누 냄새", "살냄새"** 등 쉬운 한국어로 지으세요.
        2. 모든 필터 값(`value`)은 위 **[허용된 값]** 중에서만 골라야 하며, 반드시 **영어(English)**여야 합니다.
        
        응답(JSON) 예시:
        {{
            "scenario_type": "Type B (Specific)",
            "plans": [
                {{
                    "priority": 1,
                    "strategy_name": "여름 햇살 같은 상큼한 시트러스",
                    "filters": [
                        {{"column": "season", "value": "Summer"}},  // [허용된 값] 중 선택
                        {{"column": "accord", "value": "Citrus"}},  // [허용된 값] 중 선택
                        {{"column": "gender", "value": "Unisex"}}
                    ],
                    "note_keywords": ["Fresh", "Lime"], 
                    "use_vector_search": true
                }}
            ]
        }}
        """

        msg = client.chat.completions.create(
            model=HIGH_PERFORMANCE_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )

        # ================= [ksu] Researcher 토큰 집계 =================
        in_tok = msg.usage.prompt_tokens
        out_tok = msg.usage.completion_tokens

        # 이전 단계(Supervisor 등)에서 넘어온 토큰에 더하기
        total_in = state.get("input_tokens", 0) + in_tok
        total_out = state.get("output_tokens", 0) + out_tok
        # ================= [ksu] Researcher 토큰 집계 =================

        parsed = safe_json_parse(msg.choices[0].message.content)
        plans = parsed.get("plans", []) if parsed else []
        scenario_type = parsed.get("scenario_type", "Unknown")

        print(f"   💡 선택된 시나리오: {scenario_type}", flush=True)

        search_logs = []
        final_result_text = ""

        for plan in plans:
            priority = plan.get("priority", "?")
            strategy = plan.get("strategy_name", f"Strategy-{priority}")

            print(f"   👉 [Priority {priority}] 실행: {strategy}", flush=True)

            current_filters = []

            for f in plan.get("filters", []):
                if not isinstance(f, dict):
                    continue
                col = f.get("column")
                val = f.get("value")
                if not col or not val:
                    continue

                # 브랜드/향수명 오타 보정
                if col in ["brand", "perfume_name"]:
                    corrected = search_exact_entity(val, col)
                    if corrected:
                        f["value"] = corrected

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
                final_result_text += f"\n=== [{strategy}] ===\n{result_text}\n"
            else:
                print(f"     ❌ 결과 없음", flush=True)
                search_logs.append(f"전략 [{strategy}] 결과 없음")

        if not final_result_text:
            final_result_text = "검색 결과가 없습니다."

        return {
            "search_plans": plans,
            "search_logs": search_logs,
            "research_result": final_result_text,
            "route": "writer",
            "input_tokens": total_in,
            "output_tokens": total_out,
            "retry_count": retries + 1,  # <--- [추가] 횟수 증가
        }

    except Exception:
        print("\n🚨 [Researcher Error]", flush=True)
        traceback.print_exc()
        return {"research_result": "오류 발생", "route": "writer"}


# [New] 검색 결과 검증 및 경로 결정 함수
def check_search_result(state: State):
    result = state.get("research_result", "")
    retries = state.get("retry_count", 0)

    # 1. 실패 조건: 결과 텍스트에 "없습니다"가 포함되어 있고, 재시도 횟수가 2회 미만일 때
    # (tools.py가 이미 내부적으로 3단계 방어를 하지만, 그래도 실패한 경우 Agent 레벨에서 다시 시도)
    if (
        "검색 결과가 없습니다" in result or "조건이 너무 엄격하여" in result
    ) and retries < 2:
        print(
            f"   🔄 [Loop] 검색 실패 (시도 {retries + 1}/3) -> 전략 수정 후 재검색",
            flush=True,
        )
        return "retry"  # 다시 researcher로 돌아감

    # 2. 성공하거나 재시도 횟수를 다 쓴 경우 -> Writer로 진행
    print("   ✅ [Loop] 검색 완료 또는 재시도 초과 -> Writer로 이동", flush=True)
    return "writer"


# ==========================================
# 4. Writer (글쓰기) - 1전략 1향수 & 의도 설명
# ==========================================
# 원본 규칙
# 459 : - 검색 결과가 없다면 반드시 검색된 결과가 없음을 알리고 다른 검색용 쿼리로 만들수 있을만한 질문을 던질 것.
# 460 : - 절대로 임의의 향수를 추천하지 않을 것.


def writer(state: State) -> State:
    try:
        print("✍️ [Writer] 답변 작성 시작 (Streaming Mode)", flush=True)
        query = state["user_query"]
        result = state.get("research_result", "")

        # None 방지
        if result is None:
            result = ""

        # =========================================================
        # [모드 판단 및 프롬프트 선택 로직] (기존 유지)
        # =========================================================

        system_instruction = ""

        # [Case 1: 검색 시도했으나 실패]
        if "검색 결과가 없습니다" in result or "오류 발생" in result:
            system_instruction = f"""
            **[상황: 검색 실패 (Search Failed)]**
            사용자의 요청("{query}")에 대해 DB 검색을 시도했으나, 조건에 맞는 향수를 찾지 못했습니다.
            
            **[행동 지침]**:
            1. **"찾으시는 조건에 딱 맞는 향수가 없습니다"**라고 솔직하고 정중하게 말하세요.
            2. 검색 실패 이유를 추측하여 설명하세요. (예: "해당 브랜드에 그런 향조가 없거나, 조건이 너무 구체적일 수 있습니다.")
            3. **대안을 질문**하세요. (예: "혹시 다른 브랜드나, 비슷한 다른 분위기로 추천해 드릴까요?")
            4. 절대 임의로 없는 향수를 지어내지 마세요.
            """

        # [Case 2: 일상 대화 (General Chat)]
        elif not result.strip():
            system_instruction = f"""
            **[상황: 일상 대화 및 실시간 정보 문의]**
            사용자가 '날씨', '시간' 등 실시간 정보를 물어봤습니다.
            (당신은 API 연동이 없어 이를 알 수 없는 상태입니다.)
            
            **[행동 지침]**:
            1. **최대 3문장**을 넘기지 마세요. (짧고 굵게!)
            2. **"강의"하지 마세요.** (예: "비 오는 날엔 우디 계열이 좋고~" 같은 TMI 설명 절대 금지)
            3. 실시간 정보를 모른다는 점을 **위트 있게 짧게** 사과하고, 바로 **사용자에게 되물으세요.**
            
            **[좋은 예 - 깔끔]**: "앗, 제가 하루 종일 서버 안에 갇혀 있어서 바깥 날씨를 못 봤어요. 😅 오늘 맑은가요? 사용자님의 기분을 알려주시면 딱 맞는 향을 골라드릴게요!"
            """

        # [Case 3: 검색 성공 (Recommendation)] - 사용자님만의 상세 규칙
        else:
            system_instruction = f"""
            당신은 향수를 잘 모르는 초보자를 위한 세상에서 가장 친절한 향수 컨설턴트입니다.
            
            [검색된 향수 데이터]: 
            {result}
            
            [작성 규칙 - 필독]
            0. **검색결과에 따른 출력**:
               - 만약 데이터가 부족하다면 솔직히 말하고 대안을 제시할 것.
               - 절대로 DB에 없는 향수를 지어내지 말 것.

            1. **[★1전략 1향수 원칙★]**: 
               - 검색 결과에 여러 향수가 있더라도, **각 전략(Strategy) 당 가장 적합한 향수 딱 1개만** 선정하세요.
               - 결과적으로 총 3개의 향수만 추천되어야 합니다. (중복 추천 금지)
               - 단, "전략별로 하나씩 추천합니다" 같은 설명조의 멘트는 쓰지 마세요.
            
            2. **목차 스타일 (전략 의도 강조)**: 
               - 형식: **`## 번호. [전략이름] 브랜드 - 향수명`**
               - **[전략이름]**에는 Researcher가 정한 전략명(예: "겉차속따 반전 매력")을 그대로 넣으세요.
               - 예시: `## 1. [차가운 첫인상 속 따뜻한 반전] Chanel - Coco Noir`
            
            3. **이미지 필수**: `![향수명](이미지링크)`
            
            4. **[★매우 중요★] 서식 및 강조 규칙**:
               - **항목 제목(Label)**: 반드시 **`_` (언더바)**로 감싸세요. (예: `_어떤 향인가요?_`)
               - **내용 강조(Highlight)**: 핵심 단어는 **`**` (별표 2개)**로 감싸세요. (예: `처음엔 **상큼한 귤 향**이 나요.`)
            
            5. **구분선**: 향수 추천 사이에 `---` 삽입.
            
            6. **정보 표기**: 브랜드, 이름, 출시년도만 기재.
            
            7. **[★필수★] 향 설명 방식 (용어 절대 금지)**:
               - **[절대 금지]**: '탑', '미들', '베이스', '노트', '어코드' 단어 사용 금지. 괄호 표기 `(탑)` 금지.
               - **[작성법]**: 시간의 흐름을 자연스러운 문장으로 묘사하세요.
               - **[예외]**: 노트 구성이 단순할 경우 "전체적으로 ~~ 향이 지속돼요"라고 설명하세요.
               - *Bad*: "처음에는 레몬 향이 나요(탑)."
               - *Good*: "처음에는 **막 짠 레몬즙**처럼 상큼하게 시작해요. 시간이 지나면..."
               
            8. **[핵심] 추천 논리 연결 (Why?)**:
               - `_추천 이유_`에 **"왜 이 전략(반전/직관 등)으로 이 향수를 뽑았는지"** 설명하세요.
               - 과한 수식어("끝판왕") 대신 논리적으로 설득하세요.
               - *Good*: "고객님이 **시크한 이미지**를 원하셨죠? 이 향은 **단맛 없이 건조한 나무 향**이라..."

            9. **[매우 중요] 묘사 및 강조 규칙**:
               - **전문 용어 금지**: 노트, 어코드 등 금지.
               - **쉬운 우리말 번역**: "비에 젖은 나무", "포근한 이불 냄새" 등.
               - **★핵심 강조(필수)★**: 향 묘사나 비유 표현은 반드시 **굵게(`**...**`)** 처리하세요.

            [출력 형식 예시]
            안녕하세요! 요청하신 시크한 느낌을 3가지 무드로 해석해봤어요.
            
            ## 1. [날카롭고 정돈된 시크] **Chanel - Sycomore**
            ![Sycomore](링크)
            
            - _어떤 향인가요?_: 처음엔 **비 온 뒤의 숲**처럼 차갑고 상쾌해요. 시간이 지나면 **마른 장작** 같은 나무 향이 진해지면서 단정하게 마무리돼요.
            - _추천 이유_: 군더더기 없이 **깔끔하고 드라이한 향**이에요. **차가운 도시 이미지**를 가장 직관적으로 표현하고 싶을 때 완벽한 선택이에요.
            - _정보_: Chanel / Sycomore / 2008년 출시
            
            ---
            (이하 반복)
            """

        # =========================================================
        # [최종 요청 - Streaming 적용]
        # =========================================================
        prompt = f"""
        [사용자 요청]: "{query}"
        
        {system_instruction}
        
        위 지침을 완벽하게 준수하여 답변을 작성하세요.
        """

        # [수정 포인트 1] stream=True 활성화
        stream = client.chat.completions.create(
            model=HIGH_PERFORMANCE_MODEL,
            messages=[{"role": "user", "content": prompt}],
            stream=True,  # ★핵심: 여기서 기다리지 않고 스트림을 엽니다.
        )

        # [수정 포인트 2] 객체 자체를 리턴 (기다리지 않음)
        # Main 함수가 이 'stream' 객체를 받아서 사용자에게 뿌려줍니다.
        return {
            "writer_stream": stream,  # ★ State에 스트림 객체 전달
            "active_mode": None,
        }

    except Exception:
        print("\n🚨 [Writer Error]", flush=True)
        traceback.print_exc()

        # 에러 시에는 스트림 대신 그냥 텍스트를 보냄 (Main에서 처리 필요)
        return {
            "final_response": "죄송합니다. 답변 생성 중 시스템 오류가 발생했습니다.",
            "active_mode": None,
        }


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
        {"interviewer": "interviewer", "researcher": "researcher", "writer": "writer"},
    )

    graph.add_conditional_edges(
        "interviewer",
        route_decision,
        # {"researcher": "researcher", "end": END}
        {"researcher": "researcher", "writer": "writer", "end": END},
    )

    graph.add_conditional_edges(
        "researcher",
        check_search_result,
        {
            "retry": "researcher",  # 실패 시 다시 Researcher로 (Loop)
            "writer": "writer",  # 성공 시 Writer로
        },
    )
    graph.add_edge("writer", END)

    # 메모리 저장소(Checkpointer) 적용

    return graph.compile()
