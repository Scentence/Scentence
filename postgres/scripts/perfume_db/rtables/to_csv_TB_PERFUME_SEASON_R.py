import pandas as pd

# 1. 데이터 로드
df_season = pd.read_csv("outputs/TB_PERFUME_SEASON_M.csv")

# 2. 비율(ratio) 계산
# 향수별 총 투표수 계산 후 각 행의 비율 계산
df_season["total_votes"] = df_season.groupby("PERFUME_ID")["VOTE"].transform("sum")
df_season["ratio"] = (df_season["VOTE"] / df_season["total_votes"] * 100).round(2)

# 3. 20% 미만 데이터 필터링 (컷오프)
cutoff = 20.0
df_season_filtered = df_season[df_season["ratio"] >= cutoff].copy()

# 4. 결과 저장 (PERFUME_ID, SEASON, ratio, LOAD_DT)
output_columns = ["PERFUME_ID", "SEASON", "ratio", "LOAD_DT"]
df_season_filtered = df_season_filtered[output_columns]

df_season_filtered.to_csv("routputs/TB_PERFUME_SEASON_R.csv", index=False)
print(f"TB_PERFUME_SEASON_R.csv 생성 완료. (기준: {cutoff}%)")
