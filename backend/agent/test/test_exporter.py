# backend/agent/test/test_exporter.py
"""
테스트 결과 내보내기 모듈
CSV, Excel, Markdown 형식으로 테스트 리포트를 생성합니다.
"""
 
import csv
import os
from datetime import datetime
from typing import List, Dict, Any
 
 
class TestExporter:
    """테스트 결과를 다양한 형식으로 내보내기"""
 
    COLUMNS = [
        "TC_ID",
        "타임스탬프",
        "대화_턴수",
        "실제입력",
        "실제출력",
        "기대_출력",
        "판정",
        "문제_유형",
        "심각도",
        "수정_방안_제안",
        "수정_대상_에이전트",
        "영향_파일"
    ]
 
    def __init__(self, results: List[Dict[str, Any]], output_dir: str = "test_reports"):
        """
        Args:
            results: 테스트 결과 리스트
            output_dir: 출력 디렉토리
        """
        self.results = results
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
 
    def _get_timestamp(self) -> str:
        """파일명용 타임스탬프 생성"""
        return datetime.now().strftime('%Y%m%d_%H%M%S')
 
    def _get_summary(self) -> Dict[str, int]:
        """결과 요약 계산"""
        return {
            "total": len(self.results),
            "pass": sum(1 for r in self.results if r.get('판정') == 'PASS'),
            "warning": sum(1 for r in self.results if r.get('판정') == 'WARNING'),
            "fail": sum(1 for r in self.results if r.get('판정') == 'FAIL'),
            "error": sum(1 for r in self.results if r.get('판정') == 'ERROR')
        }
 
    def _get_issue_groups(self) -> Dict[str, List[Dict]]:
        """문제 유형별 그룹핑"""
        groups = {}
        for r in self.results:
            issue_type = r.get('문제_유형')
            if issue_type:
                groups.setdefault(issue_type, []).append(r)
        return groups
 
    def to_csv(self, filename: str = None) -> str:
        """
        CSV 형식으로 내보내기
 
        Args:
            filename: 파일명 (없으면 자동 생성)
 
        Returns:
            생성된 파일 경로
        """
        if not filename:
            filename = f"test_report_{self._get_timestamp()}.csv"
 
        filepath = os.path.join(self.output_dir, filename)
 
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=self.COLUMNS, extrasaction='ignore')
            writer.writeheader()
 
            for result in self.results:
                # 컬럼명 매핑
                row = {
                    "TC_ID": result.get("TC_ID", ""),
                    "타임스탬프": result.get("타임스탬프", ""),
                    "대화_턴수": result.get("대화_턴수", ""),
                    "실제입력": result.get("실제입력", ""),
                    "실제출력": result.get("실제출력", "")[:500] + "..." if len(result.get("실제출력", "")) > 500 else result.get("실제출력", ""),
                    "기대_출력": result.get("기대_출력", ""),
                    "판정": result.get("판정", ""),
                    "문제_유형": result.get("문제_유형", ""),
                    "심각도": result.get("심각도", ""),
                    "수정_방안_제안": result.get("수정_방안_제안", ""),
                    "수정_대상_에이전트": result.get("수정_대상_에이전트", ""),
                    "영향_파일": result.get("영향_파일", "")
                }
                writer.writerow(row)
 
        return filepath
 
    def to_excel(self, filename: str = None) -> str:
        """
        Excel 형식으로 내보내기
 
        Args:
            filename: 파일명 (없으면 자동 생성)
 
        Returns:
            생성된 파일 경로
        """
        try:
            import pandas as pd
        except ImportError:
            # pandas가 없으면 CSV로 폴백
            print("Warning: pandas not installed. Falling back to CSV.")
            return self.to_csv(filename.replace('.xlsx', '.csv') if filename else None)
 
        if not filename:
            filename = f"test_report_{self._get_timestamp()}.xlsx"
 
        filepath = os.path.join(self.output_dir, filename)
 
        # DataFrame 생성
        df = pd.DataFrame(self.results)
 
        # 컬럼 순서 정렬
        existing_cols = [col for col in self.COLUMNS if col in df.columns]
        df = df[existing_cols]
 
        # Excel 저장
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='테스트결과')
 
            # 요약 시트 추가
            summary = self._get_summary()
            summary_df = pd.DataFrame([summary])
            summary_df.to_excel(writer, index=False, sheet_name='요약')
 
        return filepath
 
    def to_markdown(self, filename: str = None) -> str:
        """
        Markdown 형식으로 내보내기
 
        Args:
            filename: 파일명 (없으면 자동 생성)
 
        Returns:
            생성된 파일 경로
        """
        if not filename:
            filename = f"test_report_{self._get_timestamp()}.md"
 
        filepath = os.path.join(self.output_dir, filename)
 
        summary = self._get_summary()
        issue_groups = self._get_issue_groups()
 
        md = f"""# 챗봇 테스트 리포트
 
**생성 시간**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
 
---
 
## 1. 요약
 
| 항목 | 건수 |
|------|------|
| 전체 | {summary['total']} |
| ✅ PASS | {summary['pass']} |
| ⚠️ WARNING | {summary['warning']} |
| ❌ FAIL | {summary['fail']} |
| 🔴 ERROR | {summary['error']} |
 
---
 
## 2. 문제 유형별 분석
 
"""
 
        if not issue_groups:
            md += "_발견된 문제가 없습니다._\n"
        else:
            for issue_type, cases in issue_groups.items():
                md += f"\n### {issue_type} ({len(cases)}건)\n\n"
                for case in cases:
                    tc_id = case.get('TC_ID', 'N/A')
                    suggestion = case.get('수정_방안_제안', 'N/A')
                    affected = case.get('영향_파일', 'N/A')
                    target = case.get('수정_대상_에이전트', 'N/A')
 
                    md += f"- **{tc_id}**: {suggestion}\n"
                    md += f"  - 대상 에이전트: `{target}`\n"
                    md += f"  - 영향 파일: `{affected}`\n"
 
        md += """
---
 
## 3. 상세 결과
 
| TC_ID | 판정 | 문제유형 | 심각도 | 수정대상 | 영향파일 |
|-------|------|----------|--------|----------|----------|
"""
 
        for r in self.results:
            tc_id = r.get('TC_ID', '-')
            verdict = r.get('판정', '-')
            issue_type = r.get('문제_유형', '-') or '-'
            severity = r.get('심각도', '-') or '-'
            target = r.get('수정_대상_에이전트', '-') or '-'
            affected = r.get('영향_파일', '-') or '-'
 
            # 판정에 따른 이모지
            if verdict == 'PASS':
                verdict_display = '✅ PASS'
            elif verdict == 'WARNING':
                verdict_display = '⚠️ WARNING'
            elif verdict == 'FAIL':
                verdict_display = '❌ FAIL'
            else:
                verdict_display = f'🔴 {verdict}'
 
            md += f"| {tc_id} | {verdict_display} | {issue_type} | {severity} | {target} | {affected} |\n"
 
        md += """
---
 
## 4. 대화 상세 내역
 
"""
 
        for r in self.results:
            tc_id = r.get('TC_ID', 'N/A')
            turn = r.get('대화_턴수', 'N/A')
            user_input = r.get('실제입력', 'N/A')
            bot_output = r.get('실제출력', 'N/A')
            verdict = r.get('판정', 'N/A')
            suggestion = r.get('수정_방안_제안', '')
 
            # 긴 출력은 자르기
            if len(bot_output) > 300:
                bot_output = bot_output[:300] + "..."
 
            md += f"""### {tc_id} (Turn {turn})
 
**사용자 입력**:
> {user_input}
 
**챗봇 응답**:
> {bot_output}
 
**판정**: {verdict}
"""
            if suggestion:
                md += f"\n**제안**: {suggestion}\n"
 
            md += "\n---\n\n"
 
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(md)
 
        return filepath