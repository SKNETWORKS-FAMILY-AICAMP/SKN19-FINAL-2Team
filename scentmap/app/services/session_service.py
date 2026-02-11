import logging
import uuid
import json
import os
from typing import Dict, List, Optional
import psycopg2.extras
from scentmap.db import get_recom_db_connection

"""
SessionService: 사용자 탐색 세션 관리 및 활동 추적 서비스
"""

logger = logging.getLogger(__name__)

def create_session(member_id: Optional[int] = None, mbti: Optional[str] = None) -> Dict:
    """새로운 탐색 세션 생성 및 세션 ID 발급"""
    session_id = str(uuid.uuid4())
    try:
        with get_recom_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO TB_SCENT_CARD_SESSION_T (session_id, member_id, selected_accords, clicked_perfume_ids, liked_perfume_ids, interested_perfume_ids, passed_perfume_ids, exploration_time, interaction_count)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (session_id, member_id, [], [], [], [], [], 0, 0))
                conn.commit()
        return {"session_id": session_id, "member_id": member_id}
    except Exception as e:
        logger.error(f"세션 생성 실패: {e}")
        raise

def create_session_with_id(session_id: str, member_id: Optional[int] = None, mbti: Optional[str] = None) -> Dict:
    """특정 세션 ID로 새로운 탐색 세션 생성 (자동 생성용)"""
    try:
        with get_recom_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO TB_SCENT_CARD_SESSION_T (session_id, member_id, selected_accords, clicked_perfume_ids, liked_perfume_ids, interested_perfume_ids, passed_perfume_ids, exploration_time, interaction_count)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (session_id) DO NOTHING
                """, (session_id, member_id, [], [], [], [], [], 0, 0))
                conn.commit()
        return {"session_id": session_id, "member_id": member_id}
    except Exception as e:
        logger.error(f"세션 생성 실패 (ID: {session_id}): {e}")
        raise

def update_session_activity(
    session_id: str,
    accord_selected: Optional[str] = None,
    selected_accords: Optional[List[str]] = None,
    perfume_id: Optional[int] = None,
    dwell_time: Optional[int] = None
):
    """세션 내 사용자 활동 데이터 업데이트 (interaction_count는 자동 증가)"""
    try:
        with get_recom_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("SELECT selected_accords, clicked_perfume_ids, interaction_count FROM TB_SCENT_CARD_SESSION_T WHERE session_id = %s", (session_id,))
                session = cur.fetchone()

                # 세션이 없으면 자동으로 생성
                if not session:
                    logger.info(f"세션 {session_id}가 존재하지 않아 자동 생성합니다.")
                    create_session_with_id(session_id)
                    # 새로 생성된 세션 조회
                    cur.execute("SELECT selected_accords, clicked_perfume_ids, interaction_count FROM TB_SCENT_CARD_SESSION_T WHERE session_id = %s", (session_id,))
                    session = cur.fetchone()
                    if not session:
                        logger.error(f"세션 {session_id} 생성 후에도 조회 실패")
                        return

                # 어코드 업데이트 로직
                accords_to_save = list(session['selected_accords'] or [])

                # 1. 프론트에서 selected_accords 배열을 보낸 경우: 전체 배열로 덮어쓰기
                if selected_accords is not None:
                    accords_to_save = selected_accords
                    logger.info(f"세션 {session_id}: 어코드 배열 업데이트됨 - {accords_to_save}")
                # 2. 개별 어코드 클릭인 경우: 기존 배열에 추가
                elif accord_selected and accord_selected not in accords_to_save:
                    accords_to_save.append(accord_selected)
                    logger.info(f"세션 {session_id}: 어코드 '{accord_selected}' 추가됨")

                # 향수 클릭 처리: clicked_perfume_ids 배열에 추가
                clicked_perfumes = list(session['clicked_perfume_ids'] or [])
                if perfume_id and perfume_id not in clicked_perfumes:
                    clicked_perfumes.append(perfume_id)
                    logger.info(f"세션 {session_id}: 향수 ID {perfume_id} 클릭됨 (총 {len(clicked_perfumes)}개)")

                # interaction_count는 항상 자동으로 +1 (프론트에서 보내지 않음)
                updated_interaction_count = session['interaction_count'] + 1

                cur.execute("""
                    UPDATE TB_SCENT_CARD_SESSION_T
                    SET selected_accords = %s, clicked_perfume_ids = %s, interaction_count = %s, exploration_time = %s, last_activity_dt = CURRENT_TIMESTAMP
                    WHERE session_id = %s
                """, (accords_to_save, clicked_perfumes, updated_interaction_count, dwell_time or 0, session_id))
                conn.commit()
                logger.info(f"✅ 세션 {session_id} DB 저장 완료 - 어코드: {len(accords_to_save)}개, 향수 클릭: {len(clicked_perfumes)}개, 총 상호작용: {updated_interaction_count}회")
    except Exception as e:
        logger.error(f"세션 활동 업데이트 실패: {e}")
        raise

def update_session_context(session_id: str, member_id: Optional[int] = None, mbti: Optional[str] = None, selected_accords: List[str] = [], filters: dict = {}, visible_perfume_ids: List[int] = []):
    """분석을 위한 상세 세션 컨텍스트 정보 저장"""
    try:
        with get_recom_db_connection() as conn:
            with conn.cursor() as cur:
                # 세션 존재 여부 확인
                cur.execute("SELECT session_id FROM TB_SCENT_CARD_SESSION_T WHERE session_id = %s", (session_id,))
                session = cur.fetchone()

                # 세션이 없으면 자동 생성
                if not session:
                    logger.info(f"세션 {session_id}가 존재하지 않아 자동 생성합니다.")
                    create_session_with_id(session_id, member_id, mbti)

                # 세션 컨텍스트 업데이트
                cur.execute("""
                    UPDATE TB_SCENT_CARD_SESSION_T
                    SET member_id = COALESCE(%s, member_id), selected_accords = %s, last_activity_dt = CURRENT_TIMESTAMP
                    WHERE session_id = %s
                """, (member_id, selected_accords, session_id))
                conn.commit()
    except Exception as e:
        logger.error(f"세션 컨텍스트 업데이트 실패: {e}")
        raise

def create_new_session_after_card(member_id: Optional[int] = None) -> str:
    """카드 생성 후 새로운 세션 ID 발급"""
    new_session_id = str(uuid.uuid4())
    try:
        with get_recom_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO TB_SCENT_CARD_SESSION_T (session_id, member_id, selected_accords, clicked_perfume_ids, liked_perfume_ids, interested_perfume_ids, passed_perfume_ids, exploration_time, interaction_count)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (new_session_id, member_id, [], [], [], [], [], 0, 0))
                conn.commit()
        logger.info(f"카드 생성 후 새 세션 발급: {new_session_id}")
        return new_session_id
    except Exception as e:
        logger.error(f"카드 생성 후 새 세션 발급 실패: {e}")
        raise

def check_card_trigger(session_id: str) -> Dict:
    """세션 활동 기준 카드 생성 제안 가능 여부 확인 (가중치 점수 시스템)"""
    try:
        with get_recom_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("SELECT clicked_perfume_ids, selected_accords FROM TB_SCENT_CARD_SESSION_T WHERE session_id = %s", (session_id,))
                session = cur.fetchone()
                if not session: return {"ready": False}

                # 실제 수집된 데이터 개수 확인
                clicked_perfumes_count = len(session['clicked_perfume_ids'] or [])
                selected_accords_count = len(session['selected_accords'] or [])

                # 가중치 기반 점수 계산
                PERFUME_WEIGHT = 20   # 향수 1개 = 20점 (여러 어코드 정보 포함)
                ACCORD_WEIGHT = 10    # 어코드 1개 = 10점
                THRESHOLD = 100       # 임계값: 100점 이상

                perfume_score = clicked_perfumes_count * PERFUME_WEIGHT
                accord_score = selected_accords_count * ACCORD_WEIGHT
                total_score = perfume_score + accord_score

                ready = total_score >= THRESHOLD

                logger.info(f"세션 {session_id} 트리거 체크 - 향수: {clicked_perfumes_count}개({perfume_score}점), 어코드: {selected_accords_count}개({accord_score}점), 총점: {total_score}점, Ready: {ready}")
                return {"ready": ready, "message": "취향이 충분히 쌓였어요! 나의 향 MBTI를 확인해볼까요?" if ready else None}
    except Exception as e:
        logger.error(f"트리거 체크 실패: {e}")
        return {"ready": False}
