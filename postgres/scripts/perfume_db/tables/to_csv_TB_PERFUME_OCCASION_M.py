import pandas as pd
import ast
from datetime import datetime
import os

# 데이터 로드
input_file = "raw/perfume_info_updated.tsv"
df = pd.read_csv(input_file, sep="\t")


df["PERFUME_ID"] = (
    df["perfume_id"].astype(str).str.replace("P_", "", regex=False).astype(int)
)
load_dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Occasion 파싱 및 데이터 변환
records = []
for _, row in df.dropna(subset=["occasion"]).iterrows():
    try:
        occasion_dict = ast.literal_eval(row["occasion"])

        if isinstance(occasion_dict, dict):
            for occasion_name, vote_count in occasion_dict.items():
                records.append(
                    {
                        "PERFUME_ID": row["PERFUME_ID"],
                        "OCCASION": occasion_name,
                        "VOTE": int(vote_count),
                        "LOAD_DT": load_dt,
                    }
                )
    except (ValueError, SyntaxError):
        continue

final_df = pd.DataFrame(records)
target_columns = ["PERFUME_ID", "OCCASION", "VOTE", "LOAD_DT"]
final_df = final_df[target_columns]
final_df.sort_values(by=["PERFUME_ID", "VOTE"], ascending=[True, False], inplace=True)

# 결과 저장
output_file = "outputs/TB_PERFUME_OCCASION_M.csv"
final_df.to_csv(output_file, index=False, encoding="utf-8-sig")