"""
개인화 신호 가중치 설정

목적: tb_member_my_perfume_t 기반 사용자 취향을 점수화

사용처:
- 추천 전략 수립 시 사용자 선호 반영
- 리랭킹 시 개인화 신호 적용
- 제외 향수/브랜드 필터링

수정 방법:
이 파일의 상수들을 변경하면 개인화 가중치가 조정됩니다.
변경 후 서버 재시작 필요.
"""

# =================================================================
# 1. 선호도 가중치 (preference)
# =================================================================

# tb_member_my_perfume_t.preference 값별 점수
PREFERENCE_WEIGHTS = {
    "GOOD": 2.0,      # 좋아하는 향수 (양수)
    "NEUTRAL": 0.0,   # 중립 (영향 없음)
    "BAD": -3.0,      # 싫어하는 향수 (음수, 더 강한 패널티)
}

# 기본값 (DB에 없는 값이 들어올 경우)
DEFAULT_PREFERENCE_WEIGHT = 0.0


# =================================================================
# 2. 등록 상태 가중치 (register_status)
# =================================================================

# tb_member_my_perfume_t.register_status 값별 가중치 배수
# 최종 점수 = PREFERENCE_WEIGHT × REGISTER_STATUS_MULTIPLIER
REGISTER_STATUS_MULTIPLIERS = {
    "HAVE": 1.0,         # 현재 소유 중 (최대 신뢰도)
    "HAD": 0.5,          # 과거 소유 (중간 신뢰도)
    "RECOMMENDED": 0.7,  # 추천받았던 향수 (중상 신뢰도)
}

# 기본값
DEFAULT_REGISTER_STATUS_MULTIPLIER = 0.3


# =================================================================
# 3. 최근성 가중치 (recency)
# =================================================================

# 최근 N개 향수에 대한 가중치 부스트
RECENT_COUNT = 10          # 최신 10개
RECENT_MULTIPLIER = 1.2    # 최신 향수는 20% 가중치 증가

# 오래된 향수
OLD_MULTIPLIER = 1.0       # 기본 가중치


# =================================================================
# 4. 집계 설정
# =================================================================

# 개인화 요약에 포함할 최대 항목 수
MAX_LIKED_PERFUMES = 5     # 좋아하는 향수 Top 5
MAX_DISLIKED_PERFUMES = 5  # 싫어하는 향수 Top 5

# 조회 범위
QUERY_LIMIT = 20           # 최근 20개 향수만 조회 (성능)


# =================================================================
# 5. 최종 점수 계산 함수
# =================================================================

def calculate_personalization_score(
    preference: str,
    register_status: str,
    recency_rank: int
) -> float:
    """
    개인화 점수 계산

    Args:
        preference: GOOD/NEUTRAL/BAD
        register_status: HAVE/HAD/RECOMMENDED
        recency_rank: 0부터 시작 (0이 가장 최근)

    Returns:
        float: 개인화 점수 (양수=선호, 음수=비선호)

    Example:
        >>> calculate_personalization_score("GOOD", "HAVE", 0)
        2.4  # 2.0 × 1.0 × 1.2
        >>> calculate_personalization_score("BAD", "HAD", 15)
        -1.5  # -3.0 × 0.5 × 1.0
    """
    # 1. 선호도 점수
    pref_weight = PREFERENCE_WEIGHTS.get(preference, DEFAULT_PREFERENCE_WEIGHT)

    # 2. 등록 상태 배수
    status_mult = REGISTER_STATUS_MULTIPLIERS.get(
        register_status, DEFAULT_REGISTER_STATUS_MULTIPLIER
    )

    # 3. 최근성 배수
    recency_mult = RECENT_MULTIPLIER if recency_rank < RECENT_COUNT else OLD_MULTIPLIER

    # 최종 점수
    return pref_weight * status_mult * recency_mult


# =================================================================
# 6. 사용 예시 (주석)
# =================================================================

"""
예시 1: 최근 소유 중인 좋아하는 향수
- preference: GOOD
- register_status: HAVE
- recency_rank: 3
→ 점수: 2.0 × 1.0 × 1.2 = 2.4 (매우 선호)

예시 2: 오래전 싫어했던 향수
- preference: BAD
- register_status: HAD
- recency_rank: 18
→ 점수: -3.0 × 0.5 × 1.0 = -1.5 (중간 비선호)

예시 3: 추천받았지만 중립적인 향수
- preference: NEUTRAL
- register_status: RECOMMENDED
- recency_rank: 5
→ 점수: 0.0 × 0.7 × 1.2 = 0.0 (영향 없음)
"""
