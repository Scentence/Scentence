"""
Scentence 개인화 지수 테스트 - Graph 로직 직접 사용 (로그 제거 버전)

사용법:
    cd /home/melonmacaron/Scentence
    source venv/bin/activate
    python backend/tests/evaluation/test_personalization_graph.py

설명:
    - agent 모듈의 로직을 복사하여 테스트용으로 수정
    - 모든 print/log 출력 제거
    - Supervisor → Interviewer 강제 라우팅
    - Interviewer → Researcher → 검색 결과 추출
"""

import os
import sys
import json
import math
import random
import statistics
import asyncio
import csv
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
from datetime import datetime
from collections import Counter
from tqdm import tqdm

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# 프로젝트 루트 설정
PROJECT_ROOT = "/home/melonmacaron/Scentence"
os.environ['PROJECT_ROOT'] = PROJECT_ROOT

sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'backend'))
load_dotenv()

# LangChain imports
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

# Import agent modules (suppress ExpressionLoader warnings)
import io
from contextlib import redirect_stderr, redirect_stdout
import logging

# Capture warnings during import
_import_buffer = io.StringIO()
with redirect_stdout(_import_buffer), redirect_stderr(_import_buffer):
    from agent.schemas import AgentState, UserPreferences, InterviewResult
    from agent.tools import smart_perfume_search

# Suppress sanitize_filters logging
logging.getLogger('agent.utils').setLevel(logging.ERROR)

# ==========================================
# 테스트용 Interviewer (로그 제거)
# ==========================================

# LLM 설정
SMART_LLM = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# Interviewer Prompt (간소화)
INTERVIEWER_PROMPT_TEST = """
당신은 향수 추천을 위한 인터뷰어입니다. 사용자의 요청을 분석하여 필수 정보를 추출하세요.

[필수 정보]
1. 성별(Gender): Men, Women, Unisex 중 하나 (필수)
2. 대상(Target): 본인, 남친, 여친, 부모님 등
3. 컨셉(Concept): 계절, 상황, 분위기, 노트 등 (최소 1개)

[성별 추출 규칙]
- "남자", "남성", "남친", "남자친구", "남편", "아빠", "아버지" → Men
- "여자", "여성", "여친", "여자친구", "아내", "엄마", "어머니" → Women  
- "중성", "유니섹스", "남녀공용", "커플" → Unisex
- 성별이 명확하지 않으면 "Unisex"

[출력 형식 - 반드시 JSON]
{
    "is_sufficient": true/false,
    "response_message": "사용자에게 볼 메시지 (정보 부족시 질문)",
    "user_preferences": {
        "gender": "Men/Women/Unisex",
        "target": "대상",
        "season": "계절 (Spring/Summer/Fall/Winter)",
        "occasion": "상황",
        "style": "스타일/분위기",
        "accord": "어코드",
        "notes": ["노트1", "노트2"],
        "brand": "브랜드"
    }
}

is_sufficient은 gender가 확복되고, concept 정보가 하나 이상 있을 때 true로 설정하세요.
"""


def interviewer_node_test(state: dict) -> dict:
    """테스트용 interviewer_node (로그 없음)"""
    current_prefs = state.get("user_preferences") or {}
    if isinstance(current_prefs, UserPreferences):
        current_prefs = current_prefs.model_dump(exclude_none=True)
    
    question_count = state.get("question_count", 0) + 1
    
    # 거부 키워드 감지
    rejection_keywords = ["몰라", "아무거나", "그냥 추천", "빨리", "모르겠", "상관없"]
    user_message = state["messages"][-1].content.lower() if state["messages"] else ""
    is_rejection = any(keyword in user_message for keyword in rejection_keywords)
    
    # 질문 상한 또는 거부 감지 시 fallback
    should_fallback = (question_count >= 3) or (question_count >= 2 and is_rejection)
    
    if should_fallback:
        fallback_prefs = {
            **current_prefs,
            "gender": current_prefs.get("gender") or extract_gender_from_text(user_message) or "Unisex",
            "target": current_prefs.get("target", "일반"),
        }
        
        return {
            "next_step": "researcher",
            "user_preferences": fallback_prefs,
            "active_mode": None,
            "question_count": question_count,
            "fallback_triggered": True,
        }
    
    # LLM으로 정보 추출
    try:
        messages = [
            SystemMessage(content=INTERVIEWER_PROMPT_TEST),
            HumanMessage(content=f"사용자 입력: {user_message}\n현재 정보: {json.dumps(current_prefs, ensure_ascii=False)}\n\n분석 결과:")
        ]
        
        response = SMART_LLM.invoke(messages)
        content = response.content.strip()
        
        # JSON 파싱
        if content.startswith("```json"):
            content = content[7:-3].strip()
        elif content.startswith("```"):
            content = content[3:-3].strip()
        
        result = json.loads(content)
        
        is_sufficient = result.get("is_sufficient", False)
        user_prefs = result.get("user_preferences", {})
        
        # 성별이 없으면 텍스트에서 추출 시도
        if not user_prefs.get("gender"):
            user_prefs["gender"] = extract_gender_from_text(user_message) or "Unisex"
        
        if is_sufficient:
            return {
                "next_step": "researcher",
                "user_preferences": user_prefs,
                "active_mode": None,
                "question_count": question_count,
                "fallback_triggered": False,
            }
        
        return {
            "messages": [AIMessage(content=result.get("response_message", "더 자세히 알려주세요."))],
            "user_preferences": {**current_prefs, **user_prefs},
            "active_mode": "interviewer",
            "next_step": "end",
            "question_count": question_count,
            "fallback_triggered": False,
        }
        
    except Exception as e:
        # 에러 시 fallback
        return {
            "next_step": "researcher",
            "user_preferences": {
                "gender": extract_gender_from_text(user_message) or "Unisex",
                "target": "일반",
            },
            "active_mode": None,
            "question_count": question_count,
            "fallback_triggered": True,
        }


def extract_gender_from_text(text: str) -> Optional[str]:
    """텍스트에서 성별 추출"""
    text_lower = text.lower()
    
    male_keywords = ["남자", "남성", "남친", "남자친구", "남편", "아빠", "아버지", "son", "boyfriend", "husband", "father"]
    female_keywords = ["여자", "여성", "여친", "여자친구", "아내", "엄마", "어머니", "daughter", "girlfriend", "wife", "mother"]
    unisex_keywords = ["중성", "유니섹스", "unisex", "남녀공용", "커플"]
    
    for keyword in male_keywords:
        if keyword in text_lower:
            return "Men"
    
    for keyword in female_keywords:
        if keyword in text_lower:
            return "Women"
    
    for keyword in unisex_keywords:
        if keyword in text_lower:
            return "Unisex"
    
    return None


# ==========================================
# 테스트 설정 및 클래스
# ==========================================

@dataclass
class TestConfig:
    """테스트 설정"""
    db_host: str = os.getenv("DB_HOST", "localhost")
    db_port: int = int(os.getenv("DB_PORT", "5432"))
    db_user: str = os.getenv("DB_USER", "scentence")
    db_password: str = os.getenv("DB_PASSWORD", "scentence")
    db_name: str = os.getenv("DB_NAME", "perfume_db")
    
    personalization_test_queries: int = 50
    output_dir: str = "backend/tests/evaluation_results"


@dataclass
class PersonalizationTestResult:
    query: str
    recommendations: List[Dict]
    brand_distribution: Dict[str, int]
    unique_brands: int
    total_recommendations: int
    brand_entropy: float
    top_brand_ratio: float
    gini_coefficient: float
    # 필터 정보 추가
    hard_filters: Dict[str, Any]
    strategy_filters: Dict[str, Any]
    dropped_filters: Dict[str, Any]
    match_type: str


@dataclass
class PersonalizationTestSummary:
    total_queries: int
    mean_unique_brands: float
    mean_brand_entropy: float
    mean_top_brand_ratio: float
    mean_gini_coefficient: float
    brand_diversity_score: float
    test_results: List[PersonalizationTestResult]
    overall_brand_distribution: Dict[str, int]
    detailed_results: List[Dict] = None
    
    def to_dict(self) -> Dict:
        return {
            "total_queries": self.total_queries,
            "mean_unique_brands": self.mean_unique_brands,
            "mean_brand_entropy": self.mean_brand_entropy,
            "mean_top_brand_ratio": self.mean_top_brand_ratio,
            "mean_gini_coefficient": self.mean_gini_coefficient,
            "brand_diversity_score": self.brand_diversity_score,
            "interpretation": self._interpret_score(),
        }
    
    def _interpret_score(self) -> str:
        if self.brand_diversity_score >= 80:
            return "우수: 매우 다양한 브랜드가 추천되고 있습니다"
        elif self.brand_diversity_score >= 60:
            return "양호: 적절한 브랜드 다양성을 보여줍니다"
        elif self.brand_diversity_score >= 40:
            return "주의: 일부 브랜드로 편향된 경향이 있습니다"
        else:
            return "위험: 특정 브랜드에 심하게 편중되어 있습니다"


class DBConnection:
    """데이터베이스 연결 관리"""
    
    def __init__(self, config: TestConfig):
        self.config = config
        self.conn = None
    
    def connect(self):
        self.conn = psycopg2.connect(
            host=self.config.db_host,
            port=self.config.db_port,
            user=self.config.db_user,
            password=self.config.db_password,
            dbname=self.config.db_name
        )
        return self.conn
    
    def close(self):
        if self.conn:
            self.conn.close()
    
    def execute(self, sql: str, params: Optional[tuple] = None) -> List[Dict]:
        if self.conn is None:
            raise RuntimeError("Database connection is not established")
        cur = self.conn.cursor(cursor_factory=RealDictCursor)
        try:
            cur.execute(sql, params)
            return [dict(row) for row in cur.fetchall()]
        finally:
            cur.close()
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


TEST_QUERIES = [
    "20대 남성이 데이트할 때 뿌릴 만한 향수 추천해줘",
    "30대 남성이 오피스에서 사용하기 좋은 향수",
    "남자친구한테 선물할 woody한 향수",
    "40대 남성에게 어울리는 성숙한 향수",
    "남성용 여름에 시원하게 쓸 수 있는 향수",
    "남자가 처음 향수를 사는데 입문용으로 좋은 거",
    "남성용 우디 계열의 향수 추천",
    "남자가 면접 볼 때 어울리는 깔끔한 향수",
    "20대 여성이 데이트할 때 뿌릴 달콤한 향수",
    "30대 여성이 오피스에서 사용하기 좋은 향수",
    "여자친구한테 선물할 우아한 향수",
    "40대 여성에게 어울리는 세련된 향수",
    "여성용 여름에 시원하게 쓸 수 있는 향수",
    "여자가 처음 향수를 사는데 입문용으로 좋은 거",
    "여성용 플로랄 계열의 향수 추천",
    "여자가 소개팅에 어울리는 청순한 향수",
    "성별 상관없이 누구나 쓸 수 있는 향수",
    "커플이 함께 쓸 수 있는 유니섹스 향수",
    "중성적인 느낌의 향수 추천",
    "남녀공용으로 좋은 시트러스 향수",
    "결혼식에 가기 좋은 향수",
    "여행 갈 때 가져갈 향수",
    "잠들기 전에 뿌릴 편안한 향수",
    "울 때 뿌릴 깔끔한 향수",
    "비 오는 날 어울리는 향수",
    "화창한 봄날에 뿌릴 향수",
    "장미 향이 나는 여성용 향수",
    "우디 계열의 남성용 향수",
    "시트러스 노트가 있는 상큼한 향수",
    "머스크 베이스의 섹시한 향수",
    "바닐라가 들어간 달콤한 여성 향수",
    "자스민 향이 나는 우아한 향수",
    "스파이시한 남성용 향수",
    "프루티한 청순한 향수",
    "조말론 비슷한 느낌의 여성 향수",
    "딥디크 스타일의 중성 향수",
    "샤넬 향수처럼 고급스러운 여성용 거",
    "입생로랑 스타일의 남성 향수",
    "불가리 향수 같은 남성용 거",
    "선물하기 좋은 여성 향수",
    "학생용으로 적당한 저렴한 향수",
    "부모님께 드릴 만한 성숙한 향수",
    "오래 지속되는 남성 향수",
    "가성비 좋은 여성 향수",
]


def calculate_entropy(distribution: Dict[str, int]) -> float:
    total = sum(distribution.values())
    if total == 0:
        return 0.0
    entropy = 0.0
    for count in distribution.values():
        if count > 0:
            p = count / total
            entropy -= p * math.log2(p)
    return entropy


def calculate_gini_coefficient(distribution: Dict[str, int]) -> float:
    values = list(distribution.values())
    n = len(values)
    if n == 0 or sum(values) == 0:
        return 0.0
    mean = sum(values) / n
    abs_diff_sum = sum(abs(x - y) for i, x in enumerate(values) for y in values[i+1:])
    gini = abs_diff_sum / (2 * n * n * mean) if mean > 0 else 0.0
    return gini


def calculate_diversity_score(mean_entropy: float, mean_top_brand_ratio: float, mean_gini: float) -> float:
    entropy_score = min(mean_entropy / 5.0, 1.0) * 40
    top_brand_score = (1 - mean_top_brand_ratio) * 30
    gini_score = (1 - mean_gini) * 30
    return entropy_score + top_brand_score + gini_score


class GraphBasedTester:
    """개인화 지수 테스트"""
    
    def __init__(self, db: DBConnection, config: TestConfig):
        self.db = db
        self.config = config
    
    async def run_interviewer_and_search(self, query: str) -> tuple:
        """Interviewer 노드 실행 → Researcher 검색 실행 - 필터 정보 포함"""
        state = {
            "messages": [HumanMessage(content=query)],
            "user_query": query,
            "member_id": 0,
            "thread_id": f"test_{random.randint(1000, 9999)}",
            "user_mode": "BEGINNER",
            "user_preferences": {},
            "active_mode": "interviewer",
            "question_count": 0,
            "fallback_triggered": False,
            "frame_id": None,
            "recommended_history": [],
        }
        
        max_questions = 3
        user_prefs = None
        
        for _ in range(max_questions):
            result = interviewer_node_test(state)
            
            if result.get("next_step") == "researcher":
                user_prefs = result.get("user_preferences", {})
                break
            
            state["user_preferences"] = result.get("user_preferences", {})
            state["question_count"] = result.get("question_count", 0)
            state["fallback_triggered"] = result.get("fallback_triggered", False)
            
            if result.get("fallback_triggered"):
                user_prefs = result.get("user_preferences", {})
                break
        
        if user_prefs is None:
            user_prefs = state.get("user_preferences", {})
        
        recommendations, filter_info = await self._run_search_from_preferences(user_prefs, query)
        return recommendations, user_prefs, filter_info
    
    async def _run_search_from_preferences(self, user_prefs: Dict, query: str) -> tuple:
        """UserPreferences를 기반으로 검색 실행 - 필터 정볼 함께 반환"""
        from agent.utils import sanitize_filters
        
        h_filters = {}
        s_filters = {}
        
        gender = user_prefs.get("gender", "Unisex")
        if gender and gender != "Unisex":
            h_filters["gender"] = gender
        
        season = user_prefs.get("season")
        if season:
            h_filters["season"] = season
        
        occasion = user_prefs.get("occasion")
        if occasion:
            h_filters["occasion"] = occasion
        
        style = user_prefs.get("style")
        if style:
            s_filters["style"] = style
        
        target = user_prefs.get("target")
        if target:
            s_filters["target"] = target
        
        notes = user_prefs.get("notes", [])
        if notes:
            s_filters["notes"] = notes
        
        brand = user_prefs.get("brand")
        if brand:
            h_filters["brand"] = brand
        
        # sanitize_filters를 호출하여 dropped_filters 정보 얻기
        sanitized_hard, sanitized_strategy, dropped_items = sanitize_filters(h_filters, s_filters)
        
        try:
            candidates, match_type = await smart_perfume_search(
                h_filters=h_filters,
                s_filters=s_filters,
                exclude_ids=[],
                query_text=query,
                rank_mode="DEFAULT"
            )
            
            recommendations = []
            if candidates:
                recommendations = [
                    {
                        "perfume_id": c.get("id") or c.get("perfume_id"),
                        "perfume_brand": c.get("brand") or c.get("perfume_brand"),
                        "perfume_name": c.get("name") or c.get("perfume_name"),
                    }
                    for c in candidates[:10]
                ]
            else:
                recommendations = self._get_fallback_recommendations(10)
                match_type = "Fallback"
            
            # 필터 정보와 함께 반환
            filter_info = {
                "hard_filters": h_filters,
                "strategy_filters": s_filters,
                "dropped_filters": dropped_items,
                "sanitized_hard": sanitized_hard,
                "sanitized_strategy": sanitized_strategy,
                "match_type": match_type
            }
            
            return recommendations, filter_info
                
        except Exception as e:
            recommendations = self._get_fallback_recommendations(10)
            filter_info = {
                "hard_filters": h_filters,
                "strategy_filters": s_filters,
                "dropped_filters": dropped_items,
                "sanitized_hard": {},
                "sanitized_strategy": {},
                "match_type": f"Error: {str(e)}"
            }
            return recommendations, filter_info
    
    def _get_fallback_recommendations(self, limit: int = 10) -> List[Dict]:
        """API 실패 시 DB에서 샘플링"""
        sql = """
            SELECT DISTINCT ON (m.perfume_id)
                m.perfume_id,
                m.perfume_brand,
                m.perfume_name
            FROM TB_PERFUME_BASIC_M m
            JOIN TB_PERFUME_ACCORD_R a ON m.perfume_id = a.perfume_id
            ORDER BY m.perfume_id, RANDOM()
            LIMIT %s
        """
        return self.db.execute(sql, (limit,))
    
    async def process_single_query(self, query: str, semaphore: asyncio.Semaphore) -> tuple:
        """단일 쿼리 처리 (병렬용) - 필터 정보 포함"""
        async with semaphore:
            recommendations, user_prefs, filter_info = await self.run_interviewer_and_search(query)
            
            brand_dist = Counter(r.get('perfume_brand', r.get('brand', 'Unknown')) for r in recommendations)
            total = len(recommendations)
            unique_brands = len(brand_dist)
            
            entropy = calculate_entropy(brand_dist)
            top_brand_count = max(brand_dist.values()) if brand_dist else 0
            top_brand_ratio = top_brand_count / total if total > 0 else 0
            gini = calculate_gini_coefficient(brand_dist)
            
            result = PersonalizationTestResult(
                query=query,
                recommendations=recommendations,
                brand_distribution=dict(brand_dist),
                unique_brands=unique_brands,
                total_recommendations=total,
                brand_entropy=entropy,
                top_brand_ratio=top_brand_ratio,
                gini_coefficient=gini,
                hard_filters=filter_info.get("hard_filters", {}),
                strategy_filters=filter_info.get("strategy_filters", {}),
                dropped_filters=filter_info.get("dropped_filters", {}),
                match_type=filter_info.get("match_type", "Unknown")
            )
            
            detailed = {
                'query': query,
                'user_prefs': json.dumps(user_prefs, ensure_ascii=False),
                'unique_brands': unique_brands,
                'total_recommendations': total,
                'brand_entropy': entropy,
                'top_brand_ratio': top_brand_ratio,
                'gini_coefficient': gini,
                'brands': json.dumps(dict(brand_dist), ensure_ascii=False),
                'hard_filters': json.dumps(filter_info.get("hard_filters", {}), ensure_ascii=False),
                'strategy_filters': json.dumps(filter_info.get("strategy_filters", {}), ensure_ascii=False),
                'dropped_filters': json.dumps(filter_info.get("dropped_filters", {}), ensure_ascii=False),
                'sanitized_hard': json.dumps(filter_info.get("sanitized_hard", {}), ensure_ascii=False),
                'sanitized_strategy': json.dumps(filter_info.get("sanitized_strategy", {}), ensure_ascii=False),
                'match_type': filter_info.get("match_type", "Unknown")
            }
            
            return result, detailed, brand_dist
    
    def run_test(self) -> PersonalizationTestSummary:
        """개인화 테스트 실행 - 병렬 처리"""
        test_queries = random.sample(
            TEST_QUERIES,
            min(self.config.personalization_test_queries, len(TEST_QUERIES))
        )
        
        print(f"\n   총 {len(test_queries)}개 쿼리 테스트 시작...")
        
        semaphore = asyncio.Semaphore(5)
        
        async def process_all_queries():
            tasks = [self.process_single_query(query, semaphore) for query in test_queries]
            results = []
            detailed_results = []
            all_brands = Counter()
            
            for f in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="   쿼리 처리"):
                result, detailed, brand_dist = await f
                results.append(result)
                detailed_results.append(detailed)
                all_brands.update(brand_dist)
            
            return results, detailed_results, all_brands
        
        results, detailed_results, all_brands = asyncio.run(process_all_queries())
        
        summary = self._calculate_summary(results, all_brands)
        summary.detailed_results = detailed_results
        return summary
    
    def _calculate_summary(
        self,
        results: List[PersonalizationTestResult],
        overall_brand_dist: Counter
    ) -> PersonalizationTestSummary:
        if not results:
            return PersonalizationTestSummary(0, 0, 0, 0, 0, 0, [], {})
        
        total = len(results)
        
        mean_unique = statistics.mean(r.unique_brands for r in results)
        mean_entropy = statistics.mean(r.brand_entropy for r in results)
        mean_top_ratio = statistics.mean(r.top_brand_ratio for r in results)
        mean_gini = statistics.mean(r.gini_coefficient for r in results)
        
        diversity_score = calculate_diversity_score(mean_entropy, mean_top_ratio, mean_gini)
        
        return PersonalizationTestSummary(
            total_queries=total,
            mean_unique_brands=mean_unique,
            mean_brand_entropy=mean_entropy,
            mean_top_brand_ratio=mean_top_ratio,
            mean_gini_coefficient=mean_gini,
            brand_diversity_score=diversity_score,
            test_results=results,
            overall_brand_distribution=dict(overall_brand_dist)
        )


def save_results(summary: PersonalizationTestSummary, config: TestConfig):
    """테스트 결과 저장 (JSON, Markdown, CSV)"""
    os.makedirs(config.output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # JSON 결과
    result_data = {
        "timestamp": timestamp,
        "personalization_test": summary.to_dict(),
    }
    
    json_path = os.path.join(config.output_dir, f"personalization_graph_results_{timestamp}.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)
    
    # Markdown 보고서
    report_path = os.path.join(config.output_dir, f"personalization_graph_report_{timestamp}.md")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(generate_markdown_report(summary))
    
    # CSV 상세 결과 (시각화용)
    csv_path = os.path.join(config.output_dir, f"personalization_graph_details_{timestamp}.csv")
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'query', 'user_prefs', 'unique_brands', 'total_recommendations',
            'brand_entropy', 'top_brand_ratio', 'gini_coefficient', 'brands'
        ])
        for r in summary.detailed_results:
            writer.writerow([
                r['query'],
                r['user_prefs'],
                r['unique_brands'],
                r['total_recommendations'],
                f"{r['brand_entropy']:.6f}",
                f"{r['top_brand_ratio']:.6f}",
                f"{r['gini_coefficient']:.6f}",
                r['brands']
            ])
    
    # 요약 통계 CSV
    summary_csv_path = os.path.join(config.output_dir, f"personalization_graph_summary_{timestamp}.csv")
    with open(summary_csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Metric', 'Value'])
        writer.writerow(['Total Queries', summary.total_queries])
        writer.writerow(['Mean Unique Brands', f"{summary.mean_unique_brands:.2f}"])
        writer.writerow(['Mean Brand Entropy', f"{summary.mean_brand_entropy:.4f}"])
        writer.writerow(['Mean Top Brand Ratio', f"{summary.mean_top_brand_ratio:.4f}"])
        writer.writerow(['Mean Gini Coefficient', f"{summary.mean_gini_coefficient:.4f}"])
        writer.writerow(['Brand Diversity Score', f"{summary.brand_diversity_score:.1f}"])
    
    print(f"\n📁 결과 저장 완료:")
    print(f"   - JSON: {json_path}")
    print(f"   - Markdown: {report_path}")
    print(f"   - CSV (상세): {csv_path}")
    print(f"   - CSV (요약): {summary_csv_path}")


def generate_markdown_report(summary: PersonalizationTestSummary) -> str:
    """Markdown 형식의 보고서 생성"""
    report = []
    report.append("# 개인화 지수 (Graph 기반) 테스트 보고서")
    report.append(f"\n생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("\n---\n")
    
    report.append("## 테스트 결과\n")
    report.append(f"- **총 테스트 쿼리 수**: {summary.total_queries}")
    report.append(f"- **평균 고유 브랜드 수**: {summary.mean_unique_brands:.2f}")
    report.append(f"- **평균 브랜드 엔트로피**: {summary.mean_brand_entropy:.4f}")
    report.append(f"- **평균 최다 브랜드 비율**: {summary.mean_top_brand_ratio:.4f}")
    report.append(f"- **평균 지니계수**: {summary.mean_gini_coefficient:.4f}")
    report.append(f"- **종합 다양성 점수**: {summary.brand_diversity_score:.1f}/100")
    report.append(f"- **해석**: {summary._interpret_score()}")
    
    report.append("\n### 쿼리별 상세 결과\n")
    report.append("| 쿼리 | 고유 브랜드 | 엔트로피 | 최다 브랜드 비율 | 지니계수 |")
    report.append("|------|-------------|----------|------------------|----------|")
    for r in summary.test_results:
        query_short = r.query[:30] + "..." if len(r.query) > 30 else r.query
        report.append(f"| {query_short} | {r.unique_brands} | {r.brand_entropy:.4f} | {r.top_brand_ratio:.4f} | {r.gini_coefficient:.4f} |")
    
    return "\n".join(report)


def print_summary(summary: PersonalizationTestSummary):
    """결과 출력"""
    print("\n" + "="*60)
    print("📊 개인화 지수 테스트 결과 (Graph 기반)")
    print("="*60)
    print(f"총 테스트 쿼리: {summary.total_queries}")
    print(f"평균 고유 브랜드: {summary.mean_unique_brands:.2f}")
    print(f"평균 브랜드 엔트로피: {summary.mean_brand_entropy:.4f}")
    print(f"평균 최다 브랜드 비율: {summary.mean_top_brand_ratio:.4f}")
    print(f"평균 지니계수: {summary.mean_gini_coefficient:.4f}")
    print(f"종합 다양성 점수: {summary.brand_diversity_score:.1f}/100")
    print(f"해석: {summary._interpret_score()}")
    print("="*60)


if __name__ == "__main__":
    config = TestConfig()
    
    print("="*60)
    print("🧪 Scentence 개인화 지수 테스트 (Graph.py 직접 사용)")
    print("="*60)
    print(f"테스트 쿼리 수: {config.personalization_test_queries}")
    
    with DBConnection(config) as db:
        try:
            tester = GraphBasedTester(db, config)
            summary = tester.run_test()
            print_summary(summary)
            save_results(summary, config)
            print("\n✅ 테스트 완료!")
        except Exception as e:
            print(f"\n❌ 테스트 실패: {e}")
            import traceback
            traceback.print_exc()
    
    print("="*60)
