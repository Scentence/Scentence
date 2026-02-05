"""
Evaluation 테스트용 프롬프트 및 설정

원본: backend/agent/prompts.py
"""

# Interviewer 프롬프트 - 테스트용 간소화 버전
INTERVIEWER_PROMPT_TEST = """
당신은 향수 추천을 위한 인터뷰어입니다. 사용자의 요청을 분석하여 필수 정보를 추출하세요.

[필수 정보]
1. 성별(Gender): Men, Women, Unisex 중 하나
2. 대상(Target): 본인, 남친, 여친, 부모님 등
3. 컨셉(Concept): 계절, 상황, 분위기, 노트 등 (최소 1개)

[처리 방식]
- 정보가 충분하면 is_sufficient=True로 설정
- 정보가 부족하면 적절한 질문을 생성
- 성별이 명확하지 않으면 "성별을 알려주시겠어요?" 라고 물어보기

[출력 형식]
JSON 형식으로 출력:
{
    "is_sufficient": true/false,
    "response_message": "사용자에게 볼 메시지",
    "user_preferences": {
        "gender": "Men/Women/Unisex",
        "target": "대상",
        "season": "계절",
        "occasion": "상황",
        "style": "스타일",
        "notes": ["노트1", "노트2"]
    }
}
"""

# Supervisor 프롬프트 - 테스트용 (Interviewer로 강제 라우팅)
SUPERVISOR_PROMPT_TEST = """
당신은 향수 추천 시스템의 Supervisor입니다.

사용자의 의도를 분류하세요:
- "recommendation": 향수 추천 요청
- "information": 정보 검색 요청
- "out_of_scope": 향수와 관련 없는 질문

테스트 모드에서는 모든 recommendation 요청을 "interviewer"로 라우팅합니다.

출력: {"next_step": "interviewer"}
"""

# Researcher 프롬프트 - 테스트용
RESEARCHER_PROMPT_TEST = """
당신은 향수 검색 전략을 수립하는 Researcher입니다.

사용자 정보를 바탕으로 검색 전략을 수립하세요:
1. Hard Filters: gender, season, occasion 등
2. Strategy Filters: style, notes, accords 등

출력 형식:
{
    "strategy_name": "전략명",
    "reason": "전략 설명",
    "hard_filters": {"gender": "...", "season": "..."},
    "strategy_filters": {"style": "...", "notes": [...]}
}
"""

# 테스트용 기본 성별 매핑
DEFAULT_GENDER_MAP = {
    "남자": "Men",
    "남성": "Men",
    "남친": "Men",
    "남자친구": "Men",
    "남편": "Men",
    "아빠": "Men",
    "아버지": "Men",
    "son": "Men",
    "boyfriend": "Men",
    "husband": "Men",
    "father": "Men",
    
    "여자": "Women",
    "여성": "Women",
    "여친": "Women",
    "여자친구": "Women",
    "아내": "Women",
    "엄마": "Women",
    "어머니": "Women",
    "daughter": "Women",
    "girlfriend": "Women",
    "wife": "Women",
    "mother": "Women",
    
    "중성": "Unisex",
    "유니섹스": "Unisex",
    "unisex": "Unisex",
    "남녀공용": "Unisex",
    "커플": "Unisex",
}

# 테스트용 계절 매핑
DEFAULT_SEASON_MAP = {
    "봄": "Spring",
    "spring": "Spring",
    "여름": "Summer",
    "summer": "Summer",
    "가을": "Fall",
    "autumn": "Fall",
    "fall": "Fall",
    "겨울": "Winter",
    "winter": "Winter",
}

# 테스트용 상황 매핑
DEFAULT_OCCASION_MAP = {
    "데일리": "Daily",
    "daily": "Daily",
    "매일": "Daily",
    "출근": "Business",
    "오피스": "Business",
    "office": "Business",
    "비즈니스": "Business",
    "business": "Business",
    "면접": "Business",
    "데이트": "Date",
    "date": "Date",
    "소개팅": "Date",
    "파티": "Party",
    "party": "Party",
    "결혼식": "Party",
    "여행": "Casual",
    "travel": "Casual",
    "울": "Casual",
    "휴식": "Casual",
    "잠들기": "Casual",
}

def extract_gender_from_query(query: str) -> str:
    """쿼리에서 성별 추출"""
    query_lower = query.lower()
    
    for keyword, gender in DEFAULT_GENDER_MAP.items():
        if keyword in query_lower:
            return gender
    
    return "Unisex"  # 기본값


def extract_season_from_query(query: str) -> str:
    """쿼리에서 계절 추출"""
    query_lower = query.lower()
    
    for keyword, season in DEFAULT_SEASON_MAP.items():
        if keyword in query_lower:
            return season
    
    return None


def extract_occasion_from_query(query: str) -> str:
    """쿼리에서 상황 추출"""
    query_lower = query.lower()
    
    for keyword, occasion in DEFAULT_OCCASION_MAP.items():
        if keyword in query_lower:
            return occasion
    
    return None
