"""
향수 유사도 계산 배치 스크립트

전체 향수 간 유사도를 계산하여 TB_PERFUME_SIMILARITY 테이블에 저장합니다.
실행 시간: 약 10-30분 (향수 개수에 따라 다름)

실행 방법:
    cd Scentence\scentmap
    python scripts/batch_similarity.py
"""

import math
import time
import sys
import os

# 상위 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from collections import defaultdict
from typing import Dict, Tuple
from psycopg2.extras import RealDictCursor, execute_values

from db import get_db_connection, init_db_schema


def calculate_similarity(
    profile1: Dict[str, float], profile2: Dict[str, float]
) -> float:
    keys = set(profile1.keys()) & set(profile2.keys())
    if not keys:
        return 0.0

    vec1 = [profile1[k] for k in keys]
    vec2 = [profile2[k] for k in keys]

    dot = sum(a * b for a, b in zip(vec1, vec2))
    mag1 = math.sqrt(sum(v * v for v in profile1.values()))
    mag2 = math.sqrt(sum(v * v for v in profile2.values()))

    return dot / (mag1 * mag2) if mag1 * mag2 > 0 else 0.0


def format_time(seconds):
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def run_batch_job():
    print("🚀 [Batch] 향수 유사도 계산 및 적재 시작...")
    init_db_schema()

    process_start_time = time.time()

    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 1. 데이터 로드
            print("📦 향수 데이터 로딩 중...")
            cur.execute("SELECT perfume_id FROM TB_PERFUME_BASIC_M ORDER BY perfume_id")
            perfumes = cur.fetchall()

            cur.execute("SELECT perfume_id, accord, vote FROM TB_PERFUME_ACCORD_M")
            accords = cur.fetchall()

            accords_by_id = defaultdict(list)
            for row in accords:
                accords_by_id[row["perfume_id"]].append(
                    (row["accord"], row["vote"] or 0)
                )

            profiles = {}
            for p in perfumes:
                pid = p["perfume_id"]
                raw_accords = accords_by_id.get(pid, [])
                total = sum(v for _, v in raw_accords)
                if total > 0:
                    profiles[pid] = {k: v / total for k, v in raw_accords}
                else:
                    profiles[pid] = {}

            # 2. 유사도 계산
            results = []
            p_ids = list(profiles.keys())
            total_count = len(p_ids)

            print(f"📊 [Step 1/2] 상호 유사도 계산 중 ({total_count}개 향수)...")
            calc_start_time = time.time()

            for i in range(total_count):
                for j in range(i + 1, total_count):
                    pid_a = p_ids[i]
                    pid_b = p_ids[j]
                    sim = calculate_similarity(profiles[pid_a], profiles[pid_b])
                    if sim >= 0.3:
                        results.append((pid_a, pid_b, round(sim, 4)))

                if i % 50 == 0 or i == total_count - 1:
                    current = i + 1
                    percent = (current / total_count) * 100
                    elapsed = time.time() - calc_start_time
                    sys.stdout.write(
                        f"\r⏳ 계산 진행률: {percent:6.2f}% ({current}/{total_count})"
                    )
                    sys.stdout.flush()

            print("\n")  # 줄바꿈

            # 3. DB 적재 (Chunk Insert)
            total_results = len(results)
            print(f"💾 [Step 2/2] DB 적재 시작 (총 {total_results}건)...")

            cur.execute("TRUNCATE TABLE TB_PERFUME_SIMILARITY")

            insert_sql = "INSERT INTO TB_PERFUME_SIMILARITY (perfume_id_a, perfume_id_b, score) VALUES %s"

            # [핵심] 한 번에 다 넣지 않고 10,000개씩 잘라서 넣으며 진행상황 표시
            batch_size = 10000
            inserted_count = 0

            for i in range(0, total_results, batch_size):
                batch = results[i : i + batch_size]
                execute_values(cur, insert_sql, batch)

                inserted_count += len(batch)
                percent = (inserted_count / total_results) * 100

                # 적재 진행률 표시
                sys.stdout.write(
                    f"\r📥 적재 중: {percent:6.2f}% ({inserted_count}/{total_results}) "
                    f"| 남은 데이터: {total_results - inserted_count}건"
                )
                sys.stdout.flush()

            conn.commit()

    total_elapsed = time.time() - process_start_time
    print(f"\n✅ [완료] 총 소요시간: {format_time(total_elapsed)}")


if __name__ == "__main__":
    run_batch_job()
