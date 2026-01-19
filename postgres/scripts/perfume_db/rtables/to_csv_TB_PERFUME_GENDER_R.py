import pandas as pd

# Load Audience data
df_audience = pd.read_csv("outputs/TB_PERFUME_AUDIENCE_M.csv")

# Unique perfumes in the audience file
all_perfume_ids = df_audience["PERFUME_ID"].unique()

# Extract feminine and masculine votes
gender_df = df_audience[df_audience["AUDIENCE"].isin(["Feminine", "Masculine"])]

results = []

for pid in all_perfume_ids:
    # Get all original rows for this perfume to find the LOAD_DT
    p_full = df_audience[df_audience["PERFUME_ID"] == pid]
    load_dt = p_full["LOAD_DT"].max()

    # Filter for gender rows
    p_gender = gender_df[gender_df["PERFUME_ID"] == pid]

    if p_gender.empty:
        gender = "Unisex"
    else:
        v_fem = p_gender[p_gender["AUDIENCE"] == "Feminine"]["VOTE"].sum()
        v_masc = p_gender[p_gender["AUDIENCE"] == "Masculine"]["VOTE"].sum()

        if v_fem > 0 and v_masc == 0:
            gender = "Feminine"
        elif v_masc > 0 and v_fem == 0:
            gender = "Masculine"
        elif v_fem > 0 and v_masc > 0:
            total = v_fem + v_masc
            if v_fem / total >= 0.66:
                gender = "Feminine"
            elif v_masc / total >= 0.66:
                gender = "Masculine"
            else:
                gender = "Unisex"
        else:
            # Should not happen based on p_gender.empty check, but safety
            gender = "Unisex"

    results.append({"PERFUME_ID": pid, "GENDER": gender, "LOAD_DT": load_dt})

df_gender = pd.DataFrame(results)

# Save to CSV
output_path = "routputs/TB_PERFUME_GENDER_R.csv"
df_gender.to_csv(output_path, index=False)

print(f"Generated {output_path} with {len(df_gender)} records.")
