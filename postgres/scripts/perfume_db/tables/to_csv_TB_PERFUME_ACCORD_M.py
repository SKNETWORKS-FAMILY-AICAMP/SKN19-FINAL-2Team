import pandas as pd
import ast
from datetime import datetime

# 데이터 로드
input_file = "raw/perfume_info_updated.tsv"
df = pd.read_csv(input_file, sep="\t")


df["PERFUME_ID"] = (
    df["perfume_id"].astype(str).str.replace("P_", "", regex=False).astype(int)
)
load_dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Accord 파싱 및 데이터 변환
records = []
for _, row in df.dropna(subset=["accord"]).iterrows():
    try:
        # 문자열 "{'A': '1'}" 을 실제 딕셔너리로 변환
        accord_dict = ast.literal_eval(row["accord"])

        if isinstance(accord_dict, dict):
            for accord_name, vote_count in accord_dict.items():
                records.append(
                    {
                        "PERFUME_ID": row["PERFUME_ID"],
                        "ACCORD": accord_name,
                        "VOTE": int(vote_count),  # 문자열 숫자를 정수형으로 변환
                        "LOAD_DT": load_dt,
                    }
                )
    except (ValueError, SyntaxError):
        continue

final_df = pd.DataFrame(records)
target_columns = ["PERFUME_ID", "ACCORD", "VOTE", "LOAD_DT"]
final_df = final_df[target_columns]
final_df.sort_values(by=["PERFUME_ID", "VOTE"], ascending=[True, False], inplace=True)

# 결과 저장
output_file = "outputs/TB_PERFUME_ACCORD_M.csv"
final_df.to_csv(output_file, index=False, encoding="utf-8-sig")