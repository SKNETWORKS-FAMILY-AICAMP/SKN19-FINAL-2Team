"""Data loading and vectorization utilities for the layering service."""

from __future__ import annotations

import logging
import os
import re
from typing import Any, Dict, Iterable, List, Optional

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor
from psycopg2.extensions import connection as PGConnection

from . import schemas
from .constants import (
    ACCORDS,
    ACCORD_INDEX,
    BRAND_ALIAS_MAP,
    MATCH_SCORE_THRESHOLD,
    PERFUME_ALIAS_MAP,
    PERSISTENCE_MAP,
)

try:  # pragma: no cover - optional dependency
    import Levenshtein  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover
    Levenshtein = None


load_dotenv()
logger = logging.getLogger(__name__)

DB_CONFIG: Dict[str, Any] = {
    "dbname": os.getenv("DB_NAME", "perfume_db"),
    "user": os.getenv("DB_USER", "scentence"),
    "password": os.getenv("DB_PASSWORD", "scentence"),
    "host": os.getenv("DB_HOST", "host.docker.internal"),
    "port": os.getenv("DB_PORT", "5432"),
}

RECOM_DB_CONFIG: Dict[str, Any] = {
    **DB_CONFIG,
    "dbname": os.getenv("RECOM_DB_NAME", "recom_db"),
}

def get_db_connection(
    db_config: Optional[Dict[str, Any]] = None,
) -> PGConnection:
    try:
        return psycopg2.connect(**(db_config or DB_CONFIG))
    except psycopg2.Error as exc:
        raise LayeringDataError(
            code="DB_CONNECTION_FAILED",
            message="DB 연결에 실패했습니다.",
            step="db_connect",
            retriable=False,
            details=str(exc),
        ) from exc
    except Exception as exc:
        raise LayeringDataError(
            code="DB_CONNECTION_FAILED",
            message="DB 연결에 실패했습니다.",
            step="db_connect",
            retriable=False,
            details=str(exc),
        ) from exc


def check_db_health(db_config: Optional[Dict[str, Any]] = None) -> bool:
    try:
        conn = get_db_connection(db_config)
    except LayeringDataError:
        return False
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
        return True
    except psycopg2.Error:
        return False
    finally:
        conn.close()


def get_recom_db_connection(
    db_config: Optional[Dict[str, Any]] = None,
) -> PGConnection:
    try:
        logger.info("Connecting to recom_db (dbname=%s)", (db_config or RECOM_DB_CONFIG).get("dbname"))
        return psycopg2.connect(**(db_config or RECOM_DB_CONFIG))
    except psycopg2.Error as exc:
        logger.exception("Recom DB connection failed")
        raise LayeringDataError(
            code="RECOM_DB_CONNECTION_FAILED",
            message="추천 DB 연결에 실패했습니다.",
            step="recom_db_connect",
            retriable=False,
            details=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected recom DB connection error")
        raise LayeringDataError(
            code="RECOM_DB_CONNECTION_FAILED",
            message="추천 DB 연결에 실패했습니다.",
            step="recom_db_connect",
            retriable=False,
            details=str(exc),
        ) from exc


class LayeringDataError(RuntimeError):
    def __init__(
        self,
        code: str,
        message: str,
        step: str,
        retriable: bool = False,
        details: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.step = step
        self.retriable = retriable
        self.details = details


def _normalize_text(text: str) -> str:
    cleaned = re.sub(r"[^a-z0-9가-힣]+", " ", text.casefold())
    return " ".join(cleaned.split())


def _load_perfume_basics(conn) -> Dict[str, schemas.PerfumeBasic]:
    basics: Dict[str, schemas.PerfumeBasic] = {}
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT perfume_id, perfume_name, perfume_brand, img_link, concentration
            FROM TB_PERFUME_BASIC_M
            """
        )
        for row in cur.fetchall():
            perfume_id = str(row.get("perfume_id") or "").strip()
            if not perfume_id:
                continue
            perfume_name = str(row.get("perfume_name") or perfume_id).strip() or perfume_id
            perfume_brand = str(row.get("perfume_brand") or "Unknown").strip() or "Unknown"
            image_url = str(row.get("img_link") or "").strip() or None
            concentration = str(row.get("concentration") or "").strip() or None
            basics[perfume_id] = schemas.PerfumeBasic(
                perfume_id=perfume_id,
                perfume_name=perfume_name,
                perfume_brand=perfume_brand,
                image_url=image_url,
                concentration=concentration,
            )
    return basics


def _load_perfume_accords(conn) -> Dict[str, Dict[str, float]]:
    accords: Dict[str, Dict[str, float]] = {}
    staged: Dict[str, Dict[str, Dict[str, float]]] = {}
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT perfume_id, accord, ratio
            FROM TB_PERFUME_ACCORD_R
            """
        )
        for row in cur.fetchall():
            perfume_id = str(row.get("perfume_id") or "").strip()
            accord = str(row.get("accord") or "").strip()
            ratio_value = row.get("ratio")
            if not perfume_id or not accord:
                continue
            if accord not in ACCORDS:
                continue
            try:
                ratio = float(ratio_value)
            except (TypeError, ValueError):
                continue
            row_type = str(row.get("type") or "").strip().upper()
            buckets = staged.setdefault(perfume_id, {"base": {}, "all": {}})
            all_bucket = buckets["all"]
            all_bucket[accord] = all_bucket.get(accord, 0.0) + ratio
            if row_type == "BASE":
                base_bucket = buckets["base"]
                base_bucket[accord] = base_bucket.get(accord, 0.0) + ratio

    for perfume_id, buckets in staged.items():
        selected = buckets["base"] or buckets["all"]
        accords[perfume_id] = selected
    return accords


def _load_perfume_base_notes(conn) -> Dict[str, List[str]]:
    base_notes: Dict[str, List[str]] = {}
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT perfume_id, note
            FROM TB_PERFUME_NOTES_M
            WHERE type = 'BASE'
            """
        )
        for row in cur.fetchall():
            perfume_id = str(row.get("perfume_id") or "").strip()
            note = str(row.get("note") or "").strip()
            if not perfume_id or not note:
                continue
            base_notes.setdefault(perfume_id, []).append(note)
    return base_notes


def _load_perfume_records(conn) -> List[schemas.PerfumeRecord]:
    basics = _load_perfume_basics(conn)
    accord_map = _load_perfume_accords(conn)
    base_notes = _load_perfume_base_notes(conn)

    perfumes: List[schemas.PerfumeRecord] = []
    for perfume_id, accord_entries in accord_map.items():
        perfume = basics.get(perfume_id)
        if perfume is None:
            perfume = schemas.PerfumeBasic(
                perfume_id=perfume_id,
                perfume_name=perfume_id,
                perfume_brand="Unknown",
            )
        accords = [
            schemas.PerfumeAccord(accord=accord, ratio=ratio)
            for accord, ratio in accord_entries.items()
        ]
        notes = sorted(set(base_notes.get(perfume_id, [])))
        perfumes.append(
            schemas.PerfumeRecord(perfume=perfume, accords=accords, base_notes=notes)
        )
    return perfumes


def _vectorize(record: schemas.PerfumeRecord) -> schemas.PerfumeVector:
    vector = [0.0] * len(ACCORDS)
    for accord in record.accords:
        vector[ACCORD_INDEX[accord.accord]] = accord.ratio

    total_intensity = sum(vector)
    persistence_score = _persistence_score(vector)
    dominant = [ACCORDS[idx] for idx, value in enumerate(vector) if value > 5]
    return schemas.PerfumeVector(
        perfume_id=record.perfume.perfume_id,
        perfume_name=record.perfume.perfume_name,
        perfume_brand=record.perfume.perfume_brand,
        image_url=record.perfume.image_url,
        concentration=record.perfume.concentration,
        vector=vector,
        total_intensity=total_intensity,
        persistence_score=persistence_score,
        dominant_accords=dominant,
        base_notes=record.base_notes,
    )


def _persistence_score(vector: List[float]) -> float:
    numerator = 0.0
    denominator = 0.0
    for accord_name, value in zip(ACCORDS, vector):
        if value <= 0:
            continue
        weight = PERSISTENCE_MAP.get(accord_name, 0)
        numerator += value * weight
        denominator += value
    return numerator / denominator if denominator else 0.0


class PerfumeRepository:
    """In-memory cache of perfume vectors."""

    def __init__(
        self,
        db_config: Optional[Dict[str, str]] = None,
    ):
        self._db_config = db_config
        self._vectors = self._load_vectors()
        self._name_index = self._build_name_index()
        self._brand_index = self._build_brand_index()

    def _build_name_index(self) -> Dict[str, List[schemas.PerfumeVector]]:
        index: Dict[str, List[schemas.PerfumeVector]] = {}
        for perfume in self._vectors.values():
            candidates = [
                perfume.perfume_name,
                f"{perfume.perfume_brand} {perfume.perfume_name}",
                f"{perfume.perfume_name} {perfume.perfume_brand}",
            ]
            for candidate in candidates:
                normalized = _normalize_text(candidate)
                if not normalized:
                    continue
                index.setdefault(normalized, []).append(perfume)
        for alias, payload in PERFUME_ALIAS_MAP.items():
            normalized_alias = _normalize_text(alias)
            if not normalized_alias:
                continue
            resolved = self._resolve_alias_perfume(payload)
            if resolved is None:
                continue
            index.setdefault(normalized_alias, []).append(resolved)
        return index

    def _build_brand_index(self) -> Dict[str, List[schemas.PerfumeVector]]:
        index: Dict[str, List[schemas.PerfumeVector]] = {}
        for perfume in self._vectors.values():
            normalized = _normalize_text(perfume.perfume_brand)
            if not normalized:
                continue
            index.setdefault(normalized, []).append(perfume)
        return index

    def _resolve_alias_perfume(
        self, payload: Dict[str, str]
    ) -> Optional[schemas.PerfumeVector]:
        name = payload.get("name", "").strip()
        brand = payload.get("brand", "").strip()
        if not name:
            return None
        normalized_name = _normalize_text(name)
        normalized_brand = _normalize_text(brand) if brand else ""
        def _matches(perfume: schemas.PerfumeVector, require_brand: bool) -> bool:
            perfume_name = _normalize_text(perfume.perfume_name)
            if not perfume_name:
                return False
            if require_brand and normalized_brand:
                perfume_brand = _normalize_text(perfume.perfume_brand)
                if perfume_brand != normalized_brand:
                    return False
            if perfume_name == normalized_name:
                return True
            return normalized_name in perfume_name if normalized_name else False

        matches = [
            perfume
            for perfume in self._vectors.values()
            if _matches(perfume, require_brand=True)
        ]
        if not matches and brand:
            matches = [
                perfume
                for perfume in self._vectors.values()
                if _matches(perfume, require_brand=False)
            ]
        return matches[0] if matches else None

    def _load_vectors(self) -> Dict[str, schemas.PerfumeVector]:
        try:
            conn = get_db_connection(self._db_config)
            try:
                records = _load_perfume_records(conn)
            finally:
                conn.close()
        except psycopg2.Error as exc:
            raise LayeringDataError(
                code="DB_QUERY_FAILED",
                message="DB 조회에 실패했습니다.",
                step="data_load",
                retriable=False,
                details=str(exc),
            ) from exc
        except LayeringDataError:
            raise
        except Exception as exc:
            raise LayeringDataError(
                code="DB_QUERY_FAILED",
                message="DB 조회에 실패했습니다.",
                step="data_load",
                retriable=False,
                details=str(exc),
            ) from exc
        if not records:
            raise LayeringDataError(
                code="DATASET_EMPTY",
                message="향수 데이터가 비어 있습니다.",
                step="data_load",
                retriable=False,
            )
        return {record.perfume.perfume_id: _vectorize(record) for record in records}

    def reload(self) -> None:
        self._vectors = self._load_vectors()
        self._name_index = self._build_name_index()
        self._brand_index = self._build_brand_index()

    def find_perfume_candidates(
        self,
        query: str,
        limit: int = 5,
        min_score: float | None = None,
    ) -> List[tuple[schemas.PerfumeVector, float, str]]:
        normalized_query = _normalize_text(query)
        if not normalized_query:
            return []

        min_fuzzy_score = min_score if min_score is not None else MATCH_SCORE_THRESHOLD

        matches: Dict[str, tuple[float, str]] = {}
        for key, perfumes in self._name_index.items():
            score = 0.0
            if normalized_query == key:
                score = 1.0
            elif (
                len(key) >= 3
                and len(normalized_query) >= 3
                and (normalized_query in key or key in normalized_query)
            ):
                score = 0.9
            elif Levenshtein is not None:
                score = Levenshtein.ratio(normalized_query, key)
            if score < min_fuzzy_score:
                continue
            if score <= 0.0:
                continue
            for perfume in perfumes:
                current = matches.get(perfume.perfume_id, (0.0, ""))
                if score > current[0]:
                    matches[perfume.perfume_id] = (score, key)

        ranked = sorted(
            (
                (score, key, self._vectors[perfume_id])
                for perfume_id, (score, key) in matches.items()
                if perfume_id in self._vectors
            ),
            key=lambda item: item[0],
            reverse=True,
        )
        return [(perfume, score, key) for score, key, perfume in ranked[:limit]]

    def find_brand_candidates(self, query: str) -> List[str]:
        normalized_query = _normalize_text(query)
        if not normalized_query:
            return []

        matches: Dict[str, int] = {}
        for alias, brand in BRAND_ALIAS_MAP.items():
            normalized_alias = _normalize_text(alias)
            if normalized_alias and normalized_alias in normalized_query:
                normalized_brand = _normalize_text(brand)
                if normalized_brand in self._brand_index:
                    matches[brand] = max(matches.get(brand, 0), len(normalized_alias))

        for normalized_brand, perfumes in self._brand_index.items():
            if len(normalized_brand) < 2:
                continue
            if normalized_brand in normalized_query:
                brand_name = perfumes[0].perfume_brand
                matches[brand_name] = max(matches.get(brand_name, 0), len(normalized_brand))

        return [
            brand
            for brand, _ in sorted(matches.items(), key=lambda item: item[1], reverse=True)
        ]

    def get_brand_perfumes(self, brand_name: str) -> List[schemas.PerfumeVector]:
        normalized = _normalize_text(brand_name)
        if not normalized:
            return []
        return list(self._brand_index.get(normalized, []))

    def get_perfume(self, perfume_id: str) -> schemas.PerfumeVector:
        try:
            return self._vectors[perfume_id]
        except KeyError as exc:
            raise KeyError(f"Perfume '{perfume_id}' not found") from exc

    def all_candidates(
        self, exclude_id: Optional[str] = None
    ) -> Iterable[schemas.PerfumeVector]:
        for perfume_id, vector in self._vectors.items():
            if perfume_id == exclude_id:
                continue
            yield vector

    @property
    def count(self) -> int:
        return len(self._vectors)


def get_perfume_info(perfume_id: str) -> schemas.PerfumeInfo:
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    p.perfume_id,
                    p.perfume_brand,
                    p.perfume_name,
                    p.img_link,
                    p.concentration,
                    (SELECT gender FROM TB_PERFUME_GENDER_R WHERE perfume_id = p.perfume_id LIMIT 1) as gender,
                    (SELECT STRING_AGG(DISTINCT note, ', ') FROM TB_PERFUME_NOTES_M WHERE perfume_id = p.perfume_id AND type='TOP') as top_notes,
                    (SELECT STRING_AGG(DISTINCT note, ', ') FROM TB_PERFUME_NOTES_M WHERE perfume_id = p.perfume_id AND type='MIDDLE') as middle_notes,
                    (SELECT STRING_AGG(DISTINCT note, ', ') FROM TB_PERFUME_NOTES_M WHERE perfume_id = p.perfume_id AND type='BASE') as base_notes,
                    (SELECT STRING_AGG(accord, ', ' ORDER BY ratio DESC) FROM TB_PERFUME_ACCORD_R WHERE perfume_id = p.perfume_id) as accords,
                    (SELECT STRING_AGG(season, ', ' ORDER BY ratio DESC) FROM TB_PERFUME_SEASON_R WHERE perfume_id = p.perfume_id) as seasons,
                    (SELECT STRING_AGG(occasion, ', ' ORDER BY ratio DESC) FROM TB_PERFUME_OCA_R WHERE perfume_id = p.perfume_id) as occasions
                FROM TB_PERFUME_BASIC_M p
                WHERE p.perfume_id = %s
                LIMIT 1
                """,
                (perfume_id,),
            )
            row = cur.fetchone()
            if not row:
                raise KeyError(f"Perfume '{perfume_id}' not found")
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass

    def _split_list(value: object) -> list[str]:
        if not value:
            return []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        text = str(value)
        return [item.strip() for item in text.split(",") if item.strip()]

    return schemas.PerfumeInfo(
        perfume_id=str(row.get("perfume_id") or perfume_id),
        perfume_name=str(row.get("perfume_name") or perfume_id),
        perfume_brand=str(row.get("perfume_brand") or "Unknown"),
        image_url=str(row.get("img_link") or "").strip() or None,
        concentration=str(row.get("concentration") or "").strip() or None,
        gender=str(row.get("gender") or "").strip() or None,
        accords=_split_list(row.get("accords")),
        seasons=_split_list(row.get("seasons")),
        occasions=_split_list(row.get("occasions")),
        top_notes=_split_list(row.get("top_notes")),
        middle_notes=_split_list(row.get("middle_notes")),
        base_notes=_split_list(row.get("base_notes")),
    )


# 추천 결과를 recom_db에 기록하기 위함
def save_recommendation_results(
    member_id: int,
    recommendations: List[schemas.LayeringCandidate],
    recom_type: str = "LAYERING",
) -> schemas.SaveResult:
    conn = None
    if not member_id:
        logger.info("Skip recommendation save (member_id missing)")
        return schemas.SaveResult(
            target="recommendation",
            saved=False,
            saved_count=0,
            message="member_id is missing",
        )
    if not recommendations:
        logger.info("Skip recommendation save (no recommendations)")
        return schemas.SaveResult(
            target="recommendation",
            saved=False,
            saved_count=0,
            message="no recommendations to save",
        )

    try:
        conn = get_recom_db_connection()
        cur = conn.cursor()
        sql = (
            "INSERT INTO TB_MEMBER_RECOM_RESULT_T "
            "(MEMBER_ID, PERFUME_ID, PERFUME_NAME, RECOM_TYPE, RECOM_REASON, INTEREST_YN) "
            "VALUES (%s, %s, %s, %s, %s, 'N')"
        )
        for item in recommendations:
            # 저장되는 추천 이유를 바꾸려면 여기에서 reason 값을 재구성
            reason = item.analysis or "Layering recommendation"
            cur.execute(
                sql,
                (
                    member_id,
                    item.perfume_id,
                    item.perfume_name,
                    recom_type,
                    reason,
                ),
            )
        conn.commit()
        logger.info(
            "Recommendation save completed (member_id=%s, count=%s)",
            member_id,
            len(recommendations),
        )
        return schemas.SaveResult(
            target="recommendation",
            saved=True,
            saved_count=len(recommendations),
            message=None,
        )
    except Exception as exc:
        logger.exception("Failed to save layering recommendations")
        return schemas.SaveResult(
            target="recommendation",
            saved=False,
            saved_count=0,
            message=str(exc),
        )
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


# 보유 향수 저장 요청을 처리하기 위함
def save_my_perfume(
    member_id: int,
    perfume: schemas.PerfumeVector,
) -> schemas.SaveResult:
    conn = None
    if not member_id:
        logger.info("Skip my perfume save (member_id missing)")
        return schemas.SaveResult(
            target="my_perfume",
            saved=False,
            saved_count=0,
            message="member_id is missing",
        )

    try:
        conn = get_recom_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT 1 FROM TB_MEMBER_MY_PERFUME_T WHERE MEMBER_ID = %s AND PERFUME_ID = %s",
            (member_id, perfume.perfume_id),
        )
        if cur.fetchone():
            logger.info(
                "My perfume already exists (member_id=%s, perfume_id=%s)",
                member_id,
                perfume.perfume_id,
            )
            return schemas.SaveResult(
                target="my_perfume",
                saved=False,
                saved_count=0,
                message="already exists",
            )
        cur.execute(
            "INSERT INTO TB_MEMBER_MY_PERFUME_T "
            "(MEMBER_ID, PERFUME_ID, PERFUME_NAME, REGISTER_STATUS, PREFERENCE) "
            "VALUES (%s, %s, %s, 'RECOMMENDED', 'NEUTRAL')",
            (member_id, perfume.perfume_id, perfume.perfume_name),
        )
        conn.commit()
        logger.info(
            "My perfume save completed (member_id=%s, perfume_id=%s)",
            member_id,
            perfume.perfume_id,
        )
        return schemas.SaveResult(
            target="my_perfume",
            saved=True,
            saved_count=1,
            message=None,
        )
    except Exception as exc:
        logger.exception("Failed to save base perfume")
        return schemas.SaveResult(
            target="my_perfume",
            saved=False,
            saved_count=0,
            message=str(exc),
        )
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


# 추천 만족도 저장 요청을 처리하기 위함
def save_recommendation_feedback(
    member_id: int,
    perfume_id: str,
    perfume_name: str,
    preference: str,
) -> schemas.SaveResult:
    conn = None
    if not member_id:
        logger.info("Skip recommendation feedback save (member_id missing)")
        return schemas.SaveResult(
            target="my_perfume",
            saved=False,
            saved_count=0,
            message="member_id is missing",
        )

    if preference != "GOOD":
        logger.info(
            "Skip recommendation feedback save (preference=%s)",
            preference,
        )
        return schemas.SaveResult(
            target="my_perfume",
            saved=False,
            saved_count=0,
            message="only GOOD feedback is saved",
        )

    try:
        conn = get_recom_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO TB_MEMBER_MY_PERFUME_T
                (MEMBER_ID, PERFUME_ID, PERFUME_NAME, REGISTER_STATUS, PREFERENCE)
            VALUES (%s, %s, %s, 'RECOMMENDED', %s)
            ON CONFLICT (MEMBER_ID, PERFUME_ID)
            DO UPDATE SET
                REGISTER_STATUS = 'RECOMMENDED',
                PREFERENCE = EXCLUDED.PREFERENCE,
                ALTER_DT = CURRENT_TIMESTAMP
            """,
            (member_id, perfume_id, perfume_name, preference),
        )
        conn.commit()
        logger.info(
            "Recommendation feedback save completed (member_id=%s, perfume_id=%s, preference=%s)",
            member_id,
            perfume_id,
            preference,
        )
        return schemas.SaveResult(
            target="my_perfume",
            saved=True,
            saved_count=1,
            message=None,
        )
    except Exception as exc:
        logger.exception("Failed to save recommendation feedback")
        return schemas.SaveResult(
            target="my_perfume",
            saved=False,
            saved_count=0,
            message=str(exc),
        )
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
