import pandas as pd
import json
import ast
import os

def parse_tags(value):
    """
    {'Spicy': '93', 'Sweet': '29'} 형태의 문자열을 
    'Spicy, Sweet' 형태의 문자열로 변환합니다.
    """
    if pd.isna(value) or value == "":
        return ""
    try:
        # 문자열을 실제 딕셔너리로 변환
        tag_dict = ast.literal_eval(value)
        if isinstance(tag_dict, dict):
            # 키(Key)들만 뽑아서 쉼표로 연결
            return ", ".join(list(tag_dict.keys()))
        return str(value)
    except:
        return str(value)

def convert_tsv_to_jsonl():
    # 1. 파일 경로 설정 (자동 감지)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_dir)) # backend -> Final
    input_path = os.path.join(project_root, "data", "perfume_info.tsv")
    output_path = os.path.join(project_root, "data", "perfume_data.jsonl") # 확장자 .jsonl

    print(f"Reading file from: {input_path}")

    if not os.path.exists(input_path):
        print("[ERROR] 파일을 찾을 수 없습니다.")
        return

    # 2. TSV 파일 읽기
    try:
        df = pd.read_csv(input_path, sep='\t')
        df = df.fillna("") # 빈 값 처리
    except Exception as e:
        print(f"[ERROR] TSV 파일 읽기 실패: {e}")
        return

    print("Converting data to JSONL...")
    
    # 3. JSONL 파일 쓰기 (줄 단위 저장)
    with open(output_path, 'w', encoding='utf-8') as f:
        count = 0
        for _, row in df.iterrows():
            brand = row.get('brand', '')
            name = row.get('perfume', '')
            
            # 태그 파싱
            accord = parse_tags(row.get('accord', ''))
            season = parse_tags(row.get('season', ''))
            style = parse_tags(row.get('audience', '')) # audience -> Style
            occasion = parse_tags(row.get('occasion', ''))
            img = row.get('img', '')

            # 요청하신 문장 포맷
            embed_text = (
                f"{brand}의 {name}은(는) {accord}한 느낌을 가진 향수로 "
                f"{season}에 잘 어울리며 {style}한 향수입니다. "
                f"{occasion}한 상황에 잘 어울립니다."
            )

            # 메타데이터
            metadata = {
                "Name": name,
                "Brand": brand,
                "Accord": accord,
                "Season": season,
                "Style": style,
                "Occasion": occasion,
                "img": img,
                "id": str(row.get('perfume_id', '')),
                "link": row.get('link', '')
            }

            # JSONL용 데이터 객체
            record = {
                "embed": embed_text,
                "metadata": metadata
            }

            # 한 줄에 하나씩 JSON 쓰기
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1

    print(f"[DONE] 총 {count}개 데이터 변환 완료!")
    print(f"저장된 파일: {output_path}")

if __name__ == "__main__":
    convert_tsv_to_jsonl()