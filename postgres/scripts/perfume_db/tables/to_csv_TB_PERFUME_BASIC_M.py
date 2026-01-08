import pandas as pd
from datetime import datetime
import numpy as np

# 1. 데이터 로드 (tsv 파일)
input_file = "raw/perfume_info_updated.tsv"
df = pd.read_csv(input_file, sep="\t")


df["PERFUME_ID"] = (
    df["perfume_id"].astype(str).str.replace("P_", "", regex=False).astype(int)
)
df["RELEASE_YEAR"] = pd.to_numeric(df["release_year"], errors="coerce").astype("Int64")
df["LOAD_DT"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
df["PRODUCT_LINK"] = np.nan


# 컬럼 매핑
column_mapping = {
    "perfume": "PERFUME_NAME",
    "brand": "PERFUME_BRAND",
    "concentration": "CONCENTRATION",
    "perfumer": "PERFUMER",
    "img": "IMG_LINK",
    # "link": "PRODUCT_LINK",  # 제품의 링크는 제공되지 않음
}
df.rename(columns=column_mapping, inplace=True)

target_columns = [
    "PERFUME_ID",  # 1. 향수ID (BIGINT)
    "PERFUME_NAME",  # 2. 향수명 (VARCHAR)
    "PERFUME_BRAND",  # 3. 브랜드 (VARCHAR)
    "RELEASE_YEAR",  # 4. 출시년도 (INTEGER로 변경됨)
    "CONCENTRATION",  # 5. 농도등급 (VARCHAR)
    "PERFUMER",  # 6. 조향사 (VARCHAR)
    "IMG_LINK",  # 7. 이미지주소 (TEXT)
    # "PRODUCT_LINK",  # 8. 제품주소 (TEXT) - 제거
    "LOAD_DT",  # 10. 적재일자 (DATETIME)
]

final_df = df[target_columns]

# 결과 저장
output_file = "outputs/TB_PERFUME_BASIC_M.csv"
final_df.to_csv(output_file, index=False, encoding="utf-8-sig") 