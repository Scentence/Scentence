"""
Scentence 개인화 지수 테스트 (API 호출)

사용법:
    cd /home/melonmacaron/Scentence
    source venv/bin/activate
    python backend/tests/evaluation/test_personalization_diversity.py
    
    # FastAPI 서버가 http://localhost:8000 에서 실행 중이어야 함
    
환경변수:
    OPENAI_API_KEY: OpenAI API 키
    DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME: DB 설정
"""

import os
import sys
import json
import math
import random
import statistics
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from collections import Counter
from tqdm import tqdm

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
load_dotenv()


@dataclass
class TestConfig:
    """테스트 설정"""
    db_host: str = os.getenv("DB_HOST", "localhost")
    db_port: int = int(os.getenv("DB_PORT", "5432"))
    db_user: str = os.getenv("DB_USER", "scentence")
    db_password: str = os.getenv("DB_PASSWORD", "scentence")
    db_name: str = os.getenv("DB_NAME", "perfume_db")
    
    personalization_test_queries: int = 50
    personalization_sample_size: int = 50
    
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
    # 상황별 쿼리
    "데이트할 때 뿌릴 향수 추천해줘",
    "오피스에서 사용하기 좋은 향수",
    "여름에 시원하게 쓸 수 있는 향수",
    "겨울에 따뜻한 느낌의 향수",
    "울 때 뿌릴 깔끔한 향수",
    "면접 볼 때 어울리는 향수",
    "여행 갈 때 가져갈 향수",
    "잠들기 전에 뿌릴 편안한 향수",
    "소개팅에 어울리는 향수",
    "결혼식에 가기 좋은 향수",
    "비 오는 날 어울리는 향수",
    "화창한 봄날에 뿌릴 향수",
    
    # 감성/분위기 쿼리
    "우아하고 고급스러운 향수",
    "청순하고 깨끗한 느낌의 향수",
    "관능적이고 매혹적인 향수",
    "활기차고 에너지 넘치는 향수",
    "차분하고 묵직한 향수",
    "달콤하고 사랑스러운 향수",
    "시원하고 남성적인 향수",
    "부드럽고 여성스러운 향수",
    "성숙하고 세련된 느낌의 향수",
    "귀엽고 발랄한 향수",
    "시크하고 도시적인 향수",
    "내추럴하고 자연스러운 향수",
    
    # 노트/어코드 기반 쿼리
    "장미 향이 나는 향수",
    "우디 계열의 향수 추천",
    "시트러스 노트가 있는 향수",
    "머스크 베이스의 향수",
    "바닐라가 들어간 달콤한 향수",
    "자스민 향이 나는 향수",
    "스파이시한 향수 추천해줘",
    "프루티한 향수",
    "파우더리한 향수",
    "아쿠아틱한 향수",
    "그린 계열의 향수",
    "레더(가죽) 향이 나는 향수",
    
    # 브랜드 관련 쿼리
    "조말론 비슷한 느낌의 향수",
    "딥디크 스타일의 향수",
    "샤넬 향수처럼 고급스러운 거",
    "입생로랑 스타일의 향수",
    "불가리 향수 같은 거",
    "딥티크 향수 느낌",
    "조말론 우드세이지 앤 씨솔트 비슷한 거",
    "샤넬 넘버5 같은 클래식한 향수",
    
    # 특수 상황 쿼리
    "선물하기 좋은 향수",
    "20대 여자친구에게 줄 향수",
    "40대 남성에게 어울리는 향수",
    "처음 향수를 사는데 입문용으로 좋은 거",
    "오래 지속되는 향수",
    "가성비 좋은 향수",
    "학생용으로 적당한 향수",
    "부모님께 드릴 만한 향수",
    "면접 볼 때 안정감 주는 향수",
    "데이트 첫만남에 어울리는 향수",
    "결혼기념일 선물로 좋은 향수",
    "생일 선물로 인기있는 향수",
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


class PersonalizationTester:
    """개인화 지수 테스트 - graph.py 직접 사용"""
    
    def __init__(self, db: DBConnection, config: TestConfig):
        self.db = db
        self.config = config
        self._init_graph()
    
    def _init_graph(self):
        """LangGraph 초기화"""
        try:
            from agent.graph import app_graph
            self.graph = app_graph
            print("   ✅ LangGraph 초기화 완료")
        except Exception as e:
            print(f"   ⚠️ LangGraph 초기화 실패: {e}")
            self.graph = None
    
    async def get_recommendations_from_graph(self, query: str, limit: int = 10) -> List[Dict]:
        """
        graph.py의 LangGraph를 직접 호출하여 추천 결과 가져오기
        """
        if self.graph is None:
            return self._get_fallback_recommendations(limit)
        
        try:
            # LangGraph 입력 구성
            from langchain_core.messages import HumanMessage
            
            inputs = {
                "messages": [HumanMessage(content=query)],
                "user_query": query,
                "member_id": 0,
                "thread_id": f"test_{random.randint(1000, 9999)}",
                "user_mode": "BEGINNER",
                "recommended_count": limit,
            }
            
            # Graph 실행
            result = await self.graph.ainvoke(inputs)
            
            # 결과에서 추천 향수 추출
            recommendations = []
            if "recommendations" in result:
                for rec in result["recommendations"][:limit]:
                    recommendations.append({
                        "perfume_id": rec.get("id") or rec.get("perfume_id"),
                        "perfume_brand": rec.get("brand") or rec.get("perfume_brand"),
                        "perfume_name": rec.get("name") or rec.get("perfume_name")
                    })
            
            return recommendations if recommendations else self._get_fallback_recommendations(limit)
            
        except Exception as e:
            print(f"   ⚠️ Graph 실행 실패: {e}")
            return self._get_fallback_recommendations(limit)
    
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
    
    def run_test(self) -> PersonalizationTestSummary:
        """개인화 테스트 실행"""
        results = []
        all_brands = Counter()
        
        test_queries = random.sample(
            TEST_QUERIES,
            min(self.config.personalization_test_queries, len(TEST_QUERIES))
        )
        
        print(f"\n   총 {len(test_queries)}개 쿼리 테스트 시작...")
        
        async def run_all_queries():
            for query in tqdm(test_queries, desc="   쿼리 처리"):
                recommendations = await self.get_recommendations_from_graph(
                    query,
                    self.config.personalization_sample_size
                )
                
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
                    gini_coefficient=gini
                )
                results.append(result)
                all_brands.update(brand_dist)
        
        asyncio.run(run_all_queries())
        
        return self._calculate_summary(results, all_brands)
    
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
    """테스트 결과 저장"""
    os.makedirs(config.output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    result_data = {
        "timestamp": timestamp,
        "personalization_test": summary.to_dict(),
    }
    
    json_path = os.path.join(config.output_dir, f"personalization_test_results_{timestamp}.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)
    
    # Markdown 보고서
    report_path = os.path.join(config.output_dir, f"personalization_test_report_{timestamp}.md")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(generate_markdown_report(summary))
    
    print(f"\n📁 결과 저장 완료:")
    print(f"   - JSON: {json_path}")
    print(f"   - Report: {report_path}")


def generate_markdown_report(summary: PersonalizationTestSummary) -> str:
    """Markdown 형식의 보고서 생성"""
    report = []
    report.append("# 개인화 지수 (브랜드 다양성) 테스트 보고서")
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
    print("📊 개인화 지수 테스트 결과")
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
    print("🧪 Scentence 개인화 지수 테스트 (graph.py 직접 사용)")
    print("="*60)
    print(f"테스트 쿼리 수: {config.personalization_test_queries}")
    
    with DBConnection(config) as db:
        try:
            tester = PersonalizationTester(db, config)
            summary = tester.run_test()
            print_summary(summary)
            save_results(summary, config)
            print("\n✅ 테스트 완료!")
        except Exception as e:
            print(f"\n❌ 테스트 실패: {e}")
            import traceback
            traceback.print_exc()
    
    print("="*60)
