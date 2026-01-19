import pandas as pd

# Load Occasion data
df_occasion = pd.read_csv("outputs/TB_PERFUME_OCCASION_M.csv")

# Calculate total votes per perfume for ratio calculation
df_occasion["total_votes"] = df_occasion.groupby("PERFUME_ID")["VOTE"].transform("sum")
df_occasion["ratio"] = (df_occasion["VOTE"] / df_occasion["total_votes"] * 100).round(2)

# Apply 15% threshold as requested by the user
cutoff_occasion = 15.0
df_occasion_r = df_occasion[df_occasion["ratio"] >= cutoff_occasion].copy()

# Select required columns
output_columns = ["PERFUME_ID", "OCCASION", "ratio", "LOAD_DT"]
df_occasion_r = df_occasion_r[output_columns]

# Save to CSV
df_occasion_r.to_csv("routputs/TB_PERFUME_OCCASION_R.csv", index=False)

print(f"Generated TB_PERFUME_OCCASION_R.csv (Threshold: {cutoff_occasion}%)")
