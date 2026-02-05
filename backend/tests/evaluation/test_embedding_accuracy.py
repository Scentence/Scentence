"""
Scentence 임베딩 정확도 테스트

사용법:
    cd /home/melonmacaron/Scentence
    source venv/bin/activate
    
    # 기본 100개 테스트
    python backend/tests/evaluation/test_embedding_accuracy.py
    
    # 200개 테스트
    EMBEDDING_TEST_SIZE=200 python backend/tests/evaluation/test_embedding_accuracy.py
    
환경변수:
    OPENAI_API_KEY: OpenAI API 키
    DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME: DB 설정
    EMBEDDING_TEST_SIZE: 테스트할 노트 수 (기본: 100)
"""

import os
import sys
import json
import math
import random
import statistics
import asyncio
import csv
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
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
    
    embedding_test_size: int = int(os.getenv("EMBEDDING_TEST_SIZE", "100"))
    embedding_top_k: int = 10
    
    output_dir: str = "backend/tests/evaluation_results"


@dataclass
class EmbeddingTestResult:
    target_note: str
    query_description: str
    rank: int
    target_similarity: float
    top1_note: str
    top1_similarity: float
    similarity_gap: float
    found_in_top_k: bool


@dataclass
class EmbeddingTestSummary:
    total_tests: int
    found_in_top1: int
    found_in_top3: int
    found_in_top5: int
    found_in_top10: int
    mean_rank: float
    median_rank: float
    mean_similarity_gap: float
    mrr: float
    test_results: List[EmbeddingTestResult]
    
    def to_dict(self) -> Dict:
        return {
            "total_tests": self.total_tests,
            "found_in_top1": self.found_in_top1,
            "found_in_top3": self.found_in_top3,
            "found_in_top5": self.found_in_top5,
            "found_in_top10": self.found_in_top10,
            "accuracy_top1": self.found_in_top1 / self.total_tests if self.total_tests > 0 else 0,
            "accuracy_top3": self.found_in_top3 / self.total_tests if self.total_tests > 0 else 0,
            "accuracy_top5": self.found_in_top5 / self.total_tests if self.total_tests > 0 else 0,
            "accuracy_top10": self.found_in_top10 / self.total_tests if self.total_tests > 0 else 0,
            "mean_rank": self.mean_rank,
            "median_rank": self.median_rank,
            "mean_similarity_gap": self.mean_similarity_gap,
            "mrr": self.mrr,
        }


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


class EmbeddingTester:
    """임베딩 정확도 테스트"""
    
    def __init__(self, db: DBConnection, config: TestConfig):
        self.db = db
        self.config = config
        self.openai_available = self._check_openai()
    
    def _check_openai(self) -> bool:
        try:
            from openai import OpenAI
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                return False
            self.client = OpenAI(api_key=api_key)
            return True
        except ImportError:
            return False
    
    def get_embedding(self, text: str) -> List[float]:
        if not self.openai_available:
            raise RuntimeError("OpenAI API not available")
        
        response = self.client.embeddings.create(
            input=text.replace("\n", " "),
            model="text-embedding-3-small"
        )
        return response.data[0].embedding
    
    def get_test_notes_from_db(self) -> List[Dict]:
        """DB에서 랜덤하게 노트 샘플 가져오기"""
        sql = """
            SELECT note, description 
            FROM TB_NOTE_EMBEDDING_M 
            WHERE description IS NOT NULL 
              AND description != ''
            ORDER BY RANDOM()
            LIMIT %s
        """
        return self.db.execute(sql, (self.config.embedding_test_size,))
    
    def search_notes_by_vector(self, query_vector: List[float], top_k: int = 10) -> List[Dict]:
        """벡터로 노트 검색"""
        sql = """
            SELECT note, 
                   1 - (embedding <=> %s::vector) as similarity
            FROM TB_NOTE_EMBEDDING_M
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """
        return self.db.execute(sql, (query_vector, query_vector, top_k))
    
    def generate_korean_query_with_llm(self, note: str, description: str) -> str:
        """LLM을 사용하여 노트에 대한 한글 검색 쿼리 생성"""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": """You are a perfume expert helping to index fragrances for a search engine. Given a perfume note and its description, generate 3 different natural Korean descriptive phrases that capture the sensory experience, mood, or imagery of this note.

Constraints:
1. **STRICTLY FORBIDDEN**: Do not use the actual name of the note in the output (e.g., if the note is 'Rose', do not write 'Rose' or '장미').
2. **Format**: The phrases must be descriptive, typically ending in adjectives or nouns (e.g., '~한 향', '~한 분위기', '~가 연상되는', '~느낌'). Do not use question format.
3. **Content**: Focus on abstract descriptions like temperature, texture, visuals, or emotions (e.g., 'warm', 'powdery', 'forest-like', 'sexy').
4. Return only the 3 phrases, one per line."""
                    },
                    {
                        "role": "user",
                        "content": f"Note: {note}\nDescription: {description[:200]}\n\nGenerate 3 Korean search queries:"
                    }
                ],
                temperature=0.8,
                max_tokens=150
            )
            
            queries = response.choices[0].message.content.strip().split('\n')
            queries = [q.strip().strip('"').strip("'") for q in queries if q.strip()]
            
            if queries:
                return random.choice(queries)
            else:
                return f"{note} 향 나는 향수 추천해줘"
                
        except Exception as e:
            print(f"   ⚠️ 쿼리 생성 실패 ({note}): {e}")
            return f"{note} 향 나는 거"
    
    def translate_korean_to_english(self, korean_text: str) -> str:
        """LLM을 사용하여 한글을 영어로 번역"""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a perfume scent translator. Translate Korean scent descriptions to natural English scent descriptions. Keep it concise (5-10 words). Focus on sensory words like 'floral', 'citrus', 'woody', 'sweet', 'fresh', etc."
                    },
                    {
                        "role": "user",
                        "content": f"Translate this Korean scent description to English: '{korean_text}'"
                    }
                ],
                temperature=0.3,
                max_tokens=50
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"   ⚠️ 번역 실패: {e}")
            return korean_text
    
    def get_note_embedding_from_db(self, note: str) -> List[float]:
        """DB에서 특정 노트의 임베딩 벡터 가져오기"""
        sql = """
            SELECT embedding 
            FROM TB_NOTE_EMBEDDING_M 
            WHERE note = %s
        """
        result = self.db.execute(sql, (note,))
        if result and len(result) > 0:
            embedding = result[0]['embedding']
            if isinstance(embedding, str):
                import ast
                return ast.literal_eval(embedding)
            return list(embedding)
        return []
    
    def calculate_cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """두 벡터 간 코사인 유사도 계산"""
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    async def process_single_note(self, note_record: Dict, semaphore: asyncio.Semaphore) -> Optional[EmbeddingTestResult]:
        """단일 노트 처리 (병렬용)"""
        async with semaphore:
            target_note = note_record['note']
            description = note_record.get('description', '')
            
            try:
                korean_query = await asyncio.to_thread(self.generate_korean_query_with_llm, target_note, description)
                english_query = await asyncio.to_thread(self.translate_korean_to_english, korean_query)
                
                query_vector = await asyncio.to_thread(self.get_embedding, english_query)
                search_results = await asyncio.to_thread(self.search_notes_by_vector, query_vector, self.config.embedding_top_k)
                
                # 결과 분석
                rank = -1
                target_similarity = 0.0
                top1_note = search_results[0]['note'] if search_results else "N/A"
                top1_similarity = search_results[0]['similarity'] if search_results else 0.0
                
                target_embedding = self.get_note_embedding_from_db(target_note)
                if target_embedding:
                    target_similarity = self.calculate_cosine_similarity(query_vector, target_embedding)
                
                for i, result in enumerate(search_results):
                    if result['note'].lower() == target_note.lower():
                        rank = i + 1
                        break
                
                similarity_gap = top1_similarity - target_similarity if rank > 1 else 0.0
                combined_query = f"{korean_query} → {english_query}"
                
                return EmbeddingTestResult(
                    target_note=target_note,
                    query_description=combined_query[:80],
                    rank=rank if rank > 0 else 999,
                    target_similarity=target_similarity,
                    top1_note=top1_note,
                    top1_similarity=top1_similarity,
                    similarity_gap=similarity_gap,
                    found_in_top_k=rank > 0 and rank <= self.config.embedding_top_k
                )
                
            except Exception as e:
                print(f"   ⚠️ {target_note} 테스트 실패: {e}")
                return None
    
    def run_test(self) -> EmbeddingTestSummary:
        """임베딩 테스트 실행 - 병렬 처리"""
        if not self.openai_available:
            raise RuntimeError("OpenAI API not available")
        
        test_notes = self.get_test_notes_from_db()
        
        print(f"\n   총 {len(test_notes)}개 노트 테스트 시작...")
        print("\n   [테스트 예시 문장 샘플 - LLM 생성 → 영어 번역]")
        
        for i, note_record in enumerate(test_notes[:3]):
            note = note_record['note']
            description = note_record.get('description', '')
            korean_query = self.generate_korean_query_with_llm(note, description)
            english_query = self.translate_korean_to_english(korean_query)
            print(f"   - {note}: '{korean_query}' → '{english_query}'")
        print()
        
        semaphore = asyncio.Semaphore(20)
        
        async def run_all_tests():
            tasks = [self.process_single_note(note, semaphore) for note in test_notes]
            results = []
            for f in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="   테스트 진행"):
                result = await f
                if result:
                    results.append(result)
            return results
        
        results = asyncio.run(run_all_tests())
        
        print(f"   완료: {len(results)}/{len(test_notes)} 성공")
        
        return self._calculate_summary(results)
    
    def _calculate_summary(self, results: List[EmbeddingTestResult]) -> EmbeddingTestSummary:
        """종합 통계 계산"""
        if not results:
            return EmbeddingTestSummary(0, 0, 0, 0, 0, 0, 0, 0, 0, [])
        
        total = len(results)
        ranks = [r.rank for r in results]
        gaps = [r.similarity_gap for r in results if r.rank > 1]
        
        found_top1 = sum(1 for r in results if r.rank == 1)
        found_top3 = sum(1 for r in results if r.rank <= 3)
        found_top5 = sum(1 for r in results if r.rank <= 5)
        found_top10 = sum(1 for r in results if r.rank <= 10)
        
        mrr = sum(1/r.rank for r in results if r.rank <= 10) / total
        
        return EmbeddingTestSummary(
            total_tests=total,
            found_in_top1=found_top1,
            found_in_top3=found_top3,
            found_in_top5=found_top5,
            found_in_top10=found_top10,
            mean_rank=statistics.mean(ranks),
            median_rank=statistics.median(ranks),
            mean_similarity_gap=statistics.mean(gaps) if gaps else 0,
            mrr=mrr,
            test_results=results
        )


def save_results(summary: EmbeddingTestSummary, config: TestConfig):
    """테스트 결과 저장 (JSON, Markdown, CSV)"""
    os.makedirs(config.output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # JSON 결과
    result_data = {
        "timestamp": timestamp,
        "embedding_test": summary.to_dict(),
    }
    
    json_path = os.path.join(config.output_dir, f"embedding_test_results_{timestamp}.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)
    
    # Markdown 보고서
    report_path = os.path.join(config.output_dir, f"embedding_test_report_{timestamp}.md")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(generate_markdown_report(summary))
    
    # CSV 상세 결과 (시각화용)
    csv_path = os.path.join(config.output_dir, f"embedding_test_details_{timestamp}.csv")
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        # 헤더
        writer.writerow([
            'target_note', 'korean_query', 'english_query', 'rank', 
            'target_similarity', 'top1_note', 'top1_similarity', 
            'similarity_gap', 'found_in_top_k', 'accuracy_top1', 
            'accuracy_top3', 'accuracy_top5', 'accuracy_top10'
        ])
        # 데이터
        for r in summary.test_results:
            # 쿼리 분리 (한글 → 영어)
            parts = r.query_description.split(' → ')
            korean_query = parts[0] if len(parts) > 0 else ''
            english_query = parts[1] if len(parts) > 1 else ''
            
            writer.writerow([
                r.target_note,
                korean_query,
                english_query,
                r.rank,
                f"{r.target_similarity:.6f}",
                r.top1_note,
                f"{r.top1_similarity:.6f}",
                f"{r.similarity_gap:.6f}",
                r.found_in_top_k,
                1 if r.rank == 1 else 0,
                1 if r.rank <= 3 else 0,
                1 if r.rank <= 5 else 0,
                1 if r.rank <= 10 else 0
            ])
    
    # 요약 통계 CSV
    summary_csv_path = os.path.join(config.output_dir, f"embedding_test_summary_{timestamp}.csv")
    with open(summary_csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Metric', 'Value'])
        writer.writerow(['Total Tests', summary.total_tests])
        writer.writerow(['Top-1 Accuracy', f"{summary.found_in_top1/summary.total_tests*100:.2f}%"])
        writer.writerow(['Top-3 Accuracy', f"{summary.found_in_top3/summary.total_tests*100:.2f}%"])
        writer.writerow(['Top-5 Accuracy', f"{summary.found_in_top5/summary.total_tests*100:.2f}%"])
        writer.writerow(['Top-10 Accuracy', f"{summary.found_in_top10/summary.total_tests*100:.2f}%"])
        writer.writerow(['Mean Rank', f"{summary.mean_rank:.2f}"])
        writer.writerow(['Median Rank', f"{summary.median_rank:.2f}"])
        writer.writerow(['MRR', f"{summary.mrr:.4f}"])
        writer.writerow(['Mean Similarity Gap', f"{summary.mean_similarity_gap:.6f}"])
    
    print(f"\n📁 결과 저장 완료:")
    print(f"   - JSON: {json_path}")
    print(f"   - Markdown: {report_path}")
    print(f"   - CSV (상세): {csv_path}")
    print(f"   - CSV (요약): {summary_csv_path}")


def generate_markdown_report(summary: EmbeddingTestSummary) -> str:
    """Markdown 형식의 보고서 생성"""
    report = []
    report.append("# 임베딩 정확도 테스트 보고서")
    report.append(f"\n생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("\n---\n")
    
    report.append("## 테스트 결과\n")
    report.append(f"- **총 테스트 수**: {summary.total_tests}")
    report.append(f"- **Top-1 정확도**: {summary.found_in_top1}/{summary.total_tests} ({summary.found_in_top1/summary.total_tests*100:.1f}%)")
    report.append(f"- **Top-3 정확도**: {summary.found_in_top3}/{summary.total_tests} ({summary.found_in_top3/summary.total_tests*100:.1f}%)")
    report.append(f"- **Top-5 정확도**: {summary.found_in_top5}/{summary.total_tests} ({summary.found_in_top5/summary.total_tests*100:.1f}%)")
    report.append(f"- **Top-10 정확도**: {summary.found_in_top10}/{summary.total_tests} ({summary.found_in_top10/summary.total_tests*100:.1f}%)")
    report.append(f"- **평균 순위**: {summary.mean_rank:.2f}")
    report.append(f"- **중간 순위**: {summary.median_rank:.2f}")
    report.append(f"- **평균 유사도 차이 (Top-1과)**: {summary.mean_similarity_gap:.4f}")
    report.append(f"- **MRR**: {summary.mrr:.4f}")
    
    report.append("\n### 상세 결과 (Top 30)\n")
    report.append("| 노트 | 쿼리 | 순위 | 유사도 | Top-1 노트 | Top-1 유사도 | 차이 |")
    report.append("|------|------|------|--------|------------|--------------|------|")
    for r in summary.test_results[:30]:
        rank_str = str(r.rank) if r.rank <= 10 else 'X'
        report.append(f"| {r.target_note[:20]} | {r.query_description[:25]}... | {rank_str} | {r.target_similarity:.4f} | {r.top1_note[:15]}... | {r.top1_similarity:.4f} | {r.similarity_gap:.4f} |")
    
    return "\n".join(report)


def print_summary(summary: EmbeddingTestSummary):
    """결과 출력"""
    print("\n" + "="*60)
    print("📊 임베딩 정확도 테스트 결과")
    print("="*60)
    print(f"총 테스트 수: {summary.total_tests}")
    print(f"Top-1 정확도: {summary.found_in_top1}/{summary.total_tests} ({summary.found_in_top1/summary.total_tests*100:.1f}%)")
    print(f"Top-3 정확도: {summary.found_in_top3}/{summary.total_tests} ({summary.found_in_top3/summary.total_tests*100:.1f}%)")
    print(f"Top-5 정확도: {summary.found_in_top5}/{summary.total_tests} ({summary.found_in_top5/summary.total_tests*100:.1f}%)")
    print(f"Top-10 정확도: {summary.found_in_top10}/{summary.total_tests} ({summary.found_in_top10/summary.total_tests*100:.1f}%)")
    print(f"MRR (Mean Reciprocal Rank): {summary.mrr:.4f}")
    print(f"평균 순위: {summary.mean_rank:.2f}")
    print(f"중간 순위: {summary.median_rank:.2f}")
    print(f"평균 유사도 (정답 노트): {statistics.mean([r.target_similarity for r in summary.test_results]):.4f}")
    print(f"평균 유사도 (Top-1): {statistics.mean([r.top1_similarity for r in summary.test_results]):.4f}")
    print(f"평균 유사도 차이 (Top-1 - 정답): {summary.mean_similarity_gap:.4f}")
    print("="*60)


if __name__ == "__main__":
    config = TestConfig()
    
    print("="*60)
    print("🧪 Scentence 임베딩 정확도 테스트")
    print("="*60)
    print(f"테스트 노트 수: {config.embedding_test_size}")
    
    with DBConnection(config) as db:
        try:
            tester = EmbeddingTester(db, config)
            summary = tester.run_test()
            print_summary(summary)
            save_results(summary, config)
            print("\n✅ 테스트 완료!")
        except Exception as e:
            print(f"\n❌ 테스트 실패: {e}")
            import traceback
            traceback.print_exc()
    
    print("="*60)
