import json
import psycopg2
import psycopg2.extras
from typing import List, Dict, Any, Optional

# 기존 DB 연결 함수 사용
from .database import get_recom_db_connection, get_db_connection, release_recom_db_connection, release_db_connection

def get_my_perfumes(member_id: int) -> List[Dict[str, Any]]:
    """
    [복구] 기존 tb_member_my_perfume_t 테이블에서 데이터 조회
    """
    conn_user = get_recom_db_connection()
    if not conn_user:
        return []
    
    my_perfumes = []
    try:
        cur = conn_user.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        # 테이블명: tb_member_my_perfume_t
        cur.execute("""
            SELECT 
                p.member_id, p.perfume_id, p.perfume_name, p.register_status, p.preference,
                p.register_dt
            FROM tb_member_my_perfume_t p
            WHERE p.member_id = %s
            ORDER BY p.register_dt DESC
        """, (member_id,))
        my_perfumes = cur.fetchall()
        cur.close()
    except Exception as e:
        print(f"Error fetching my perfumes: {e}")
        return []
    finally:
        release_recom_db_connection(conn_user)

    if not my_perfumes:
        return []

    # 향수 상세 정보 (이미지, 브랜드) 병합
    perfume_ids = [p['perfume_id'] for p in my_perfumes]
    conn_perfume = get_db_connection()
    details_map = {}
    try:
        with conn_perfume.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if perfume_ids:
                fmt = ','.join(['%s'] * len(perfume_ids))
                cur.execute(f"""
                    SELECT 
                        b.perfume_id, b.perfume_brand, b.img_link,
                        k.name_kr, k.brand_kr
                    FROM tb_perfume_basic_m b
                    LEFT JOIN tb_perfume_name_kr k ON b.perfume_id = k.perfume_id
                    WHERE b.perfume_id IN ({fmt})
                """, tuple(perfume_ids))
                rows = cur.fetchall()
                for r in rows:
                    details_map[r['perfume_id']] = r
    except Exception as e:
        print(f"Error fetching perfume details: {e}")
    finally:
        release_db_connection(conn_perfume)

    result = []
    for p in my_perfumes:
        pid = p['perfume_id']
        detail = details_map.get(pid, {})
        merged = {
            "my_perfume_id": pid, # 프론트엔드 호환용
            "member_id": p['member_id'],
            "perfume_id": pid,
            "register_status": p['register_status'],
            "preference": p.get('preference', 'NEUTRAL'),  # [★추가] 개인화용
            "register_dt": str(p['register_dt']) if p['register_dt'] else None,
            "perfume_name": p['perfume_name'],
            "name_en": p['perfume_name'],  # 기본 테이블의 영어 이름
            "name_kr": detail.get('name_kr') or p['perfume_name'], # 한글 테이블에 없으면 영어 이름 대체
            "brand": detail.get('perfume_brand', "Unknown"),
            "brand_kr": detail.get('brand_kr') or detail.get('perfume_brand', "Unknown"),
            "image_url": detail.get('img_link', None)
        }
        result.append(merged)
    return result

def add_my_perfume_logic(member_id: int, perfume_id: int, perfume_name: str, status: str, preference: str = "NEUTRAL"):
    """
    [복구] 기존 테이블에 향수 등록 (성욱님 기존 logic 복사)
    """
    conn = get_recom_db_connection()
    if not conn:
        return {"status": "error", "message": "DB Connection Failed"}
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO tb_member_my_perfume_t 
            (member_id, perfume_id, perfume_name, register_status, preference, register_reason, register_dt)
            VALUES (%s, %s, %s, %s, %s, 'USER', NOW())
            ON CONFLICT (member_id, perfume_id) 
            DO UPDATE SET 
                register_status = EXCLUDED.register_status,
                preference = EXCLUDED.preference,
                alter_dt = NOW()
        """, (member_id, perfume_id, perfume_name, status, preference))
        conn.commit()
        return {"status": "success"}
    except Exception as e:
        conn.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        cur.close()
        release_recom_db_connection(conn)

def delete_my_perfume_logic(member_id: int, perfume_id: int):
    """
    [복구] 기존 테이블에서 삭제
    """
    conn = get_recom_db_connection()
    if not conn:
        return {"status": "error", "message": "DB Connection Failed"}
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM tb_member_my_perfume_t WHERE member_id = %s AND perfume_id = %s", (member_id, perfume_id))
        conn.commit()
        return {"status": "success"}
    except Exception as e:
        conn.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        cur.close()
        release_recom_db_connection(conn)

def update_my_perfume_logic(member_id: int, perfume_id: int, status: str, preference: str = None):
    """
    [복구] 향수 상태 변경 (HAVE -> HAD 등)
    """
    conn = get_recom_db_connection()
    if not conn:
        return {"status": "error", "message": "DB Connection Failed"}
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE tb_member_my_perfume_t
            SET register_status = %s, preference = COALESCE(%s, preference), alter_dt = NOW()
            WHERE member_id = %s AND perfume_id = %s
        """, (status, preference, member_id, perfume_id))
        conn.commit()
        return {"status": "success"}
    except Exception as e:
        conn.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        cur.close()
        release_recom_db_connection(conn)

def get_perfume_notes_and_accords(perfume_ids: List[int]) -> Dict[int, Dict[str, Any]]:
    """
    Get notes and accords for a list of perfume IDs.
    
    Args:
        perfume_ids: List of perfume IDs to fetch notes/accords for
    
    Returns:
        Dictionary mapping perfume_id to {notes: List[str], accords: List[str]}
        Example: {
            123: {
                "notes": ["Rose", "Vanilla", "Sandalwood"],
                "accords": ["Floral", "Woody"]
            }
        }
    """
    if not perfume_ids:
        return {}
    
    conn = get_db_connection()
    if not conn:
        return {}
    
    result = {}
    
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Fetch accords
            fmt = ','.join(['%s'] * len(perfume_ids))
            cur.execute(f"""
                SELECT perfume_id, accord
                FROM TB_PERFUME_ACCORD_R
                WHERE perfume_id IN ({fmt}) AND accord IS NOT NULL
            """, tuple(perfume_ids))
            accords_rows = cur.fetchall()
            
            # Fetch notes (all types: TOP, MIDDLE, BASE)
            cur.execute(f"""
                SELECT perfume_id, note
                FROM TB_PERFUME_NOTES_M
                WHERE perfume_id IN ({fmt}) AND note IS NOT NULL
            """, tuple(perfume_ids))
            notes_rows = cur.fetchall()
            
            # Build result dictionary
            for pid in perfume_ids:
                result[pid] = {"notes": [], "accords": []}
            
            # Populate accords
            for row in accords_rows:
                pid = row['perfume_id']
                accord = row['accord']
                if pid in result and accord and accord not in result[pid]["accords"]:
                    result[pid]["accords"].append(accord)
            
            # Populate notes (deduplicated across TOP/MIDDLE/BASE)
            for row in notes_rows:
                pid = row['perfume_id']
                note = row['note']
                if pid in result and note and note not in result[pid]["notes"]:
                    result[pid]["notes"].append(note)
    
    except Exception as e:
        print(f"Error fetching notes/accords: {e}")
        return {}
    finally:
        release_db_connection(conn)
    
    return result
