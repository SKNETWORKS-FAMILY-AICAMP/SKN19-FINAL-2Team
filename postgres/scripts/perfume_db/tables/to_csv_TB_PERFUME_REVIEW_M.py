import pandas as pd
import ast
from datetime import datetime
import os

# 데이터 로드
input_file = "raw/cleaned_reviews.tsv"
df = pd.read_csv(input_file, sep="\t")

# 식별자 전처리 (R_, P_ 제거 후 정수 변환)
df["REVIEW_ID"] = (
    df["review_id"].astype(str).str.replace("R_", "", regex=False).astype(int)
)
df["PERFUME_ID"] = (
    df["perfume_id"].astype(str).str.replace("P_", "", regex=False).astype(int)
)
df["LOAD_DT"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

column_mapping = {"content": "CONTENT"}
df.rename(columns=column_mapping, inplace=True)

# author 제외, 필요한 컬럼만 선택
target_columns = ["REVIEW_ID", "PERFUME_ID", "CONTENT", "LOAD_DT"]
final_df = df[target_columns]

output_file = "outputs/TB_PERFUME_REVIEW_M.csv"
final_df.to_csv(output_file, index=False, encoding="utf-8-sig")