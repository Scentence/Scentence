"""
개인화 신호 요약 및 주입

tb_member_my_perfume_t 기반 사용자 취향을 분석하여
추천 시스템에 주입할 수 있는 형태로 요약합니다.
"""

from typing import List, Dict, Any, Optional
from collections import defaultdict
from .archive_db import get_my_perfumes
from .personalization_weights import (
    calculate_personalization_score,
    QUERY_LIMIT,
    MAX_LIKED_PERFUMES,
    MAX_DISLIKED_PERFUMES,
)


def get_personalization_summary(member_id: int) -> Dict[str, Any]:
    """
    사용자의 개인화 취향 요약 생성

    Args:
        member_id: 사용자 ID (0이면 비로그인 → 빈 요약 반환)

    Returns:
        Dict containing:
        - liked_perfumes: List[Dict] - 좋아하는 향수 Top N
        - disliked_perfumes: List[Dict] - 싫어하는 향수 Top N
        - liked_brands: Dict[str, float] - 좋아하는 브랜드와 점수
        - disliked_brands: Dict[str, float] - 싫어하는 브랜드와 점수
        - total_count: int - 전체 개인화 데이터 개수
        - summary_text: str - 프롬프트용 한 줄 요약

    Example:
        >>> summary = get_personalization_summary(member_id=123)
        >>> print(summary['summary_text'])
        "딥디크, 조말론 브랜드를 선호하시는 것 같아요. 강한 시트러스 향수는 피하시는 편이네요."
    """
    # 비로그인 사용자
    if not member_id or member_id == 0:
        return _empty_summary()

    # DB에서 개인화 데이터 조회
    try:
        my_perfumes = get_my_perfumes(member_id)
    except Exception as e:
        print(f"⚠️ [Personalization] Error fetching my_perfumes: {e}")
        return _empty_summary()

    if not my_perfumes:
        return _empty_summary()

    # 최근 N개만 사용 (성능)
    my_perfumes = my_perfumes[:QUERY_LIMIT]

    # 점수 계산
    scored_perfumes = []
    brand_scores = defaultdict(float)

    for idx, perfume in enumerate(my_perfumes):
        # [★수정] preference 필드 사용 (archive_db.py에서 추가됨)
        preference = perfume.get("preference", "NEUTRAL")
        register_status = perfume.get("register_status", "RECOMMENDED")

        score = calculate_personalization_score(
            preference=preference,
            register_status=register_status,
            recency_rank=idx,
        )

        scored_perfumes.append({
            **perfume,
            "personalization_score": score,
        })

        # 브랜드별 집계
        brand = perfume.get("brand", "Unknown")
        if brand and brand != "Unknown":
            brand_scores[brand] += score

    # 정렬
    scored_perfumes.sort(key=lambda x: x["personalization_score"], reverse=True)

    # Top N 추출
    liked = [p for p in scored_perfumes if p["personalization_score"] > 0][:MAX_LIKED_PERFUMES]
    disliked = [p for p in scored_perfumes if p["personalization_score"] < 0][:MAX_DISLIKED_PERFUMES]
    disliked.sort(key=lambda x: x["personalization_score"])  # 가장 싫어하는 것부터

    # 브랜드 Top N
    liked_brands = {k: v for k, v in sorted(brand_scores.items(), key=lambda x: x[1], reverse=True) if v > 0}
    disliked_brands = {k: v for k, v in sorted(brand_scores.items(), key=lambda x: x[1]) if v < 0}

    # 한 줄 요약 생성
    summary_text = _generate_summary_text(liked_brands, disliked_brands, liked, disliked)

    return {
        "liked_perfumes": liked,
        "disliked_perfumes": disliked,
        "liked_brands": liked_brands,
        "disliked_brands": disliked_brands,
        "total_count": len(my_perfumes),
        "summary_text": summary_text,
    }


def _empty_summary() -> Dict[str, Any]:
    """빈 개인화 요약 (비로그인 또는 데이터 없음)"""
    return {
        "liked_perfumes": [],
        "disliked_perfumes": [],
        "liked_brands": {},
        "disliked_brands": {},
        "total_count": 0,
        "summary_text": "",
    }


def _generate_summary_text(
    liked_brands: Dict[str, float],
    disliked_brands: Dict[str, float],
    liked_perfumes: List[Dict],
    disliked_perfumes: List[Dict],
) -> str:
    """
    프롬프트 주입용 한 줄 요약 생성

    민감정보 최소화: 브랜드명만 사용, 향수 전체 이름은 포함하지 않음
    """
    parts = []

    # 좋아하는 브랜드 (최대 3개)
    if liked_brands:
        top_brands = list(liked_brands.keys())[:3]
        brands_str = ", ".join(top_brands)
        parts.append(f"{brands_str} 브랜드를 선호하시는 것 같아요")

    # 싫어하는 브랜드 (최대 2개)
    if disliked_brands:
        bottom_brands = list(disliked_brands.keys())[:2]
        brands_str = ", ".join(bottom_brands)
        parts.append(f"{brands_str} 브랜드는 피하시는 편이네요")

    if not parts:
        return ""

    return ". ".join(parts) + "."


# =================================================================
# 사용 예시
# =================================================================

"""
Example usage:

    from agent.personalization import get_personalization_summary

    # 로그인 사용자
    summary = get_personalization_summary(member_id=123)
    print(summary['summary_text'])
    # → "딥디크, 조말론 브랜드를 선호하시는 것 같아요"

    # 비로그인 사용자
    summary = get_personalization_summary(member_id=0)
    print(summary['total_count'])  # → 0

    # 프롬프트 주입
    if summary['summary_text']:
        prompt += f"\\n\\n사용자 취향: {summary['summary_text']}"
"""
