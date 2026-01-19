import pandas as pd
import numpy as np

# Load the accord data
df_accord = pd.read_csv("outputs/TB_PERFUME_ACCORD_M.csv")


def process_accords_with_ratio(group_df, cliff_threshold=0.5, budget=80.0):
    total_votes = group_df["VOTE"].sum()
    if total_votes == 0:
        return pd.DataFrame()

    # Step 1: Calculate % and round to nearest integer for grouping
    temp_df = group_df.copy()
    temp_df["pct"] = (temp_df["VOTE"] / total_votes) * 100
    temp_df["rounded_pct"] = temp_df["pct"].round(0).astype(int)

    # Step 2: Sort by vote descending
    temp_df = temp_df.sort_values("VOTE", ascending=False)

    # Form groups by rounded_pct
    groups = []
    current_rounded = -1
    for _, row in temp_df.iterrows():
        if row["rounded_pct"] != current_rounded:
            groups.append([])
            current_rounded = row["rounded_pct"]
        groups[-1].append(row.to_dict())

    selected_rows = []
    cum_pct = 0.0

    for i, group in enumerate(groups):
        group_pcts = [item["pct"] for item in group]
        avg_pct = np.mean(group_pcts)
        group_size = len(group)

        # Step 3: First group is always in
        if i == 0:
            selected_rows.extend(group)
            cum_pct += sum(group_pcts)
            continue

        # Step 4: Cliff Filter (50%)
        prev_avg_pct = np.mean([item["pct"] for item in groups[i - 1]])
        if avg_pct < prev_avg_pct * cliff_threshold:
            break

        # Step 5: Democratic Budget Filter (80%)
        num_fit = 0
        temp_cum = cum_pct
        for p in group_pcts:
            if temp_cum + p <= budget + 1e-9:
                num_fit += 1
                temp_cum += p

        # Inclusive Majority (>= 50%)
        if num_fit >= (group_size / 2.0):
            selected_rows.extend(group)
            cum_pct += sum(group_pcts)
        else:
            break

    return pd.DataFrame(selected_rows)


# Apply the logic perfume by perfume
result_list = []
for pid, group in df_accord.groupby("PERFUME_ID"):
    processed = process_accords_with_ratio(group)
    if not processed.empty:
        result_list.append(processed)

df_final = pd.concat(result_list, ignore_index=True)

# Add ratio column rounded to 2 decimal places
df_final["ratio"] = df_final["pct"].round(2)

# Select and order columns
columns_to_keep = ["PERFUME_ID", "ACCORD", "ratio", "LOAD_DT"]
df_final_output = df_final[columns_to_keep]

# Save to CSV
output_filename = "routputs/TB_PERFUME_ACCORD_R.csv"
df_final_output.to_csv(output_filename, index=False)

print(f"Generated {output_filename}")
