import pandas as pd
import json
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics.pairwise import cosine_similarity
import scipy.stats

# 1. 데이터 로드 및 전처리
def run_performance_analysis(file_path='backend/scripts/vectorDB/raw/notes_mapping_final2.json'):
    accords_33 = [
        'Animal', 'Aquatic', 'Chypre', 'Citrus', 'Creamy', 'Earthy', 'Floral', 'Fougère', 
        'Fresh', 'Fruity', 'Gourmand', 'Green', 'Leathery', 'Oriental', 'Powdery', 
        'Resinous', 'Smoky', 'Spicy', 'Sweet', 'Synthetic', 'Woody',
        'Alcoholic', 'Aldehydic', 'Bitter', 'Chemical', 'Herbal', 'Metallic', 'Minty', 
        'Musky', 'Nuts', 'Hanbang', 'Hinoki', 'Temple'
    ]

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # DataFrame 변환
    rows = []
    for item in data:
        row = {acc: 0.0 for acc in accords_33}
        row.update(item['mappings'])
        row['note'] = item['note']
        row['primary_accord'] = item['primary_accord']
        rows.append(row)
    
    df = pd.DataFrame(rows)
    df_accords = df[accords_33]

    # --- [지표 4번] 어코드 커버리지 분석 (Entropy Score) ---
    accord_sums = df_accords.sum()
    probabilities = accord_sums / accord_sums.sum()
    entropy = scipy.stats.entropy(probabilities, base=2)
    max_entropy = np.log2(len(accords_33))
    coverage_score = (entropy / max_entropy) * 100  # 100%에 가까울수록 고른 분포

    # --- [지표 2번] 벡터 공간 정합성 분석 (Similarity Heatmap) ---
    similarity_matrix = cosine_similarity(df_accords.T)
    sim_df = pd.DataFrame(similarity_matrix, index=accords_33, columns=accords_33)

    # --- 시각화 1: 평행 좌표 그래프 (Parallel Coordinates) ---
    plt.figure(figsize=(16, 8))
    # 가독성을 위해 100개의 노트를 샘플링하여 시각화
    sample_df = df.sample(min(100, len(df)))
    pd.plotting.parallel_coordinates(sample_df[accords_33 + ['primary_accord']], 
                                     'primary_accord', colormap='tab20', alpha=0.4)
    plt.xticks(rotation=90)
    plt.title(f"Parallel Coordinates: Accord Coverage Analysis\n(Coverage Score: {coverage_score:.2f}%)", fontsize=15)
    plt.legend(bbox_to_anchor=(1.02, 1), loc='upper left', ncol=2, fontsize='small')
    plt.grid(axis='y', linestyle='--', alpha=0.3)
    plt.tight_layout()
    plt.savefig('performance_coverage_parallel.png')

    # --- 시각화 2: 어코드 유사도 히트맵 (Heatmap) ---
    plt.figure(figsize=(14, 12))
    sns.heatmap(sim_df, cmap='coolwarm', center=0.5, annot=False)
    plt.title("Accord Similarity Heatmap: Semantic Consistency Analysis", fontsize=15)
    plt.tight_layout()
    plt.savefig('performance_consistency_heatmap.png')

    # 결과 출력
    print(f"📊 [지표 4] 어코드 커버리지 점수: {coverage_score:.2f}% (엔트로피: {entropy:.2f})")
    print(f"📊 [지표 2] 가장 독립적인 어코드: {accord_sums.idxmin()} / 가장 지배적인 어코드: {accord_sums.idxmax()}")
    print(f"\n✅ 시각화 파일 저장 완료: \n1. performance_coverage_parallel.png \n2. performance_consistency_heatmap.png")

if __name__ == "__main__":
    run_performance_analysis()