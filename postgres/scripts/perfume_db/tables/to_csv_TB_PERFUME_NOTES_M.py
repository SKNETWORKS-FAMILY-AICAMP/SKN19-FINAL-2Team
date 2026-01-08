import pandas as pd
from datetime import datetime

# 데이터 로드
input_file = "raw/perfume_info_updated.tsv"
df = pd.read_csv(input_file, sep="\t")


df["PERFUME_ID"] = (
    df["perfume_id"].astype(str).str.replace("P_", "", regex=False).astype(int)
)
df["LOAD_DT"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# 노트 데이터 전처리 함수
def get_note_df(source_df, col_name, type_value):
    temp = (
        source_df[["PERFUME_ID", col_name, "LOAD_DT"]].dropna(subset=[col_name]).copy()
    )
    temp[col_name] = temp[col_name].str.split(",")  # 콤마 분리
    temp = temp.explode(col_name)  # 행 분리

    temp["NOTE"] = temp[col_name].str.strip()
    temp["TYPE"] = type_value
    return temp[["PERFUME_ID", "NOTE", "TYPE", "LOAD_DT"]]


# TOP, MIDDLE, BASE 각각 추출
top_df = get_note_df(df, "top_note", "TOP")
mid_df = get_note_df(df, "middle_note", "MIDDLE")
base_df = get_note_df(df, "base_note", "BASE")

final_df = pd.concat([top_df, mid_df, base_df], ignore_index=True)
final_df = final_df.sort_values(by=["PERFUME_ID", "TYPE"])

# 결과 저장
output_file = "outputs/TB_PERFUME_NOTES_M.csv"
final_df.to_csv(output_file, index=False, encoding="utf-8-sig")