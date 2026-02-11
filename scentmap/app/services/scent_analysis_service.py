import logging
import json
import os
from typing import Dict, List, Optional
from scentmap.db import get_db_connection

"""
ScentAnalysisService: 향기 데이터 분석 및 MBTI 도출 핵심 로직 처리 서비스
"""

logger = logging.getLogger(__name__)

# 데이터 캐시
_mbti_data_cache = None
_accord_type_mapping_cache = None
_accord_mbti_mapping_cache = None

def load_mbti_data() -> List[Dict]:
    """MBTI 데이터 로드 및 캐싱"""
    global _mbti_data_cache
    if _mbti_data_cache is not None:
        return _mbti_data_cache
    try:
        data_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "perfume_mbti.json")
        with open(data_path, 'r', encoding='utf-8') as f:
            _mbti_data_cache = json.load(f)
        return _mbti_data_cache
    except Exception as e:
        logger.error(f"MBTI 데이터 로드 실패: {e}")
        return []

def load_accord_type_mapping() -> Dict:
    """어코드 타입 매핑 데이터 로드 및 캐싱"""
    global _accord_type_mapping_cache
    if _accord_type_mapping_cache is not None:
        return _accord_type_mapping_cache
    try:
        data_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "accord_type_mapping.json")
        with open(data_path, 'r', encoding='utf-8') as f:
            _accord_type_mapping_cache = json.load(f)
        return _accord_type_mapping_cache
    except Exception as e:
        logger.error(f"어코드 타입 매핑 데이터 로드 실패: {e}")
        return {"accord_types": {}, "default_type": {"type_name": "독특한 탐험가"}}

def load_accord_mbti_mapping() -> Dict:
    """어코드 MBTI 4축 매핑 데이터 로드 및 캐싱"""
    global _accord_mbti_mapping_cache
    if _accord_mbti_mapping_cache is not None:
        return _accord_mbti_mapping_cache
    try:
        data_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "accord_mbti_mapping.json")
        with open(data_path, 'r', encoding='utf-8') as f:
            _accord_mbti_mapping_cache = json.load(f)
        return _accord_mbti_mapping_cache
    except Exception as e:
        logger.error(f"어코드 MBTI 매핑 데이터 로드 실패: {e}")
        return {"accord_axis_scores": {}, "axis_descriptions": {}, "mbti_code_mapping": {}}

def calculate_four_axis_scores(selected_accords: List[str]) -> Dict:
    """선택된 어코드를 기반으로 4축 점수 계산 (E/I, S/N, T/F, J/P)"""
    try:
        mapping_data = load_accord_mbti_mapping()
        accord_scores = mapping_data.get('accord_axis_scores', {})
        if not selected_accords:
            return {}
        
        # improve_plan_v1 및 perfume_mbti_v1 기준 4축 초기화
        # E/I: 존재방식, S/N: 인식방식, T/F: 감정질감, J/P: 취향안정성
        axis_totals = {
            "E": 0, "I": 0,  # 존재방식
            "S": 0, "N": 0,  # 인식방식
            "T": 0, "F": 0,  # 감정질감
            "J": 0, "P": 0   # 취향안정성
        }
        
        valid_accord_count = 0
        for accord in selected_accords:
            if accord in accord_scores:
                for axis, score in accord_scores[accord].items():
                    if axis in axis_totals:
                        axis_totals[axis] += score
                valid_accord_count += 1
        
        if valid_accord_count == 0:
            return {}
            
        return {axis: total / valid_accord_count for axis, total in axis_totals.items()}
    except Exception as e:
        logger.error(f"4축 점수 계산 실패: {e}")
        return {}

def determine_mbti_code(axis_scores: Dict) -> Optional[str]:
    """4축 점수를 기반으로 향 MBTI 코드 결정 (E/I, S/N, T/F, J/P)"""
    if not axis_scores:
        return None
    code = ""
    # 1. E/I : 존재방식 (확산성 및 발산력)
    code += "E" if axis_scores.get("E", 0) >= axis_scores.get("I", 0) else "I"
    # 2. S/N : 인식방식 (묘사의 구체성)
    code += "S" if axis_scores.get("S", 0) >= axis_scores.get("N", 0) else "N"
    # 3. T/F : 감정질감 (향의 온도와 구조)
    code += "T" if axis_scores.get("T", 0) >= axis_scores.get("F", 0) else "F"
    # 4. J/P : 취향안정성 (조향의 전형성)
    code += "J" if axis_scores.get("J", 0) >= axis_scores.get("P", 0) else "P"
    return code

def get_mbti_from_scent_code(scent_code: str) -> Optional[str]:
    """향 MBTI 코드를 인간 MBTI로 변환"""
    mapping_data = load_accord_mbti_mapping()
    return mapping_data.get('mbti_code_mapping', {}).get(scent_code)

def analyze_scent_type(selected_accords: List[str], accord_descriptions: List[Dict], user_mbti: Optional[str] = None) -> Dict:
    """선택된 어코드와 사용자 MBTI를 기반으로 향 타입 분석"""
    try:
        axis_scores = calculate_four_axis_scores(selected_accords)
        scent_code = determine_mbti_code(axis_scores)
        derived_mbti = get_mbti_from_scent_code(scent_code)
        
        mapping_data = load_accord_type_mapping()
        mbti_affinity = mapping_data.get('mbti_accord_affinity', {})
        
        from collections import Counter
        accord_counter = Counter(selected_accords)
        
        if derived_mbti and derived_mbti in mbti_affinity:
            for accord in mbti_affinity[derived_mbti].get('preferred_accords', []):
                if accord in accord_counter:
                    accord_counter[accord] += 1.5
        
        if user_mbti and user_mbti in mbti_affinity and user_mbti != derived_mbti:
            for accord in mbti_affinity[user_mbti].get('preferred_accords', []):
                if accord in accord_counter:
                    accord_counter[accord] += 0.5
        
        most_common_accord = sorted(accord_counter.items(), key=lambda item: (-item[1], item[0]))[0][0] if accord_counter else selected_accords[0]
        
        main_accord_desc = next((desc for desc in accord_descriptions if desc['accord'] == most_common_accord), accord_descriptions[0])
        type_info = mapping_data.get('accord_types', {}).get(most_common_accord, mapping_data.get('default_type', {}))
        
        active_mbti = derived_mbti or user_mbti
        mbti_profile_summary = None
        if active_mbti:
            mbti_data = load_mbti_data()
            profile = next((p for p in mbti_data if p.get("mbti") == active_mbti.upper()), None)
            if profile:
                mbti_profile_summary = {k: profile.get(k) for k in ["headline", "intro", "impression", "strengths", "weaknesses", "scent_preferences"]}

        return {
            "type_name": type_info.get('type_name', '독특한 탐험가'),
            "axis_scores": axis_scores,
            "scent_code": scent_code,
            "derived_mbti": derived_mbti,
            "mbti_profile": mbti_profile_summary,
            "main_accord_desc": main_accord_desc,
            "type_info": type_info
        }
    except Exception as e:
        logger.error(f"향 타입 분석 실패: {e}")
        return {"type_name": "독특한 탐험가", "axis_scores": {}, "scent_code": None, "derived_mbti": None}

def get_accord_descriptions(accord_names: List[str]) -> List[Dict]:
    """어코드 설명 DB 조회"""
    if not accord_names: return []
    try:
        import psycopg2.extras
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                placeholders = ','.join(['%s'] * len(accord_names))
                cur.execute(f"SELECT accord, desc1, desc2, desc3 FROM TB_ACCORD_DESC_M WHERE accord IN ({placeholders})", tuple(accord_names))
                results = cur.fetchall()
                desc_map = {row['accord']: dict(row) for row in results}
                return [desc_map[acc] for acc in accord_names if acc in desc_map]
    except Exception as e:
        logger.error(f"어코드 설명 조회 실패: {e}")
        return []
