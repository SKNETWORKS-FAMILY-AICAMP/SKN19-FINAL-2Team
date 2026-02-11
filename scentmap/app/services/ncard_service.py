import json
import random
import os
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
import psycopg2.extras
from openai import OpenAI
from scentmap.db import get_recom_db_connection, get_db_connection
from scentmap.app.schemas.ncard_schemas import (
    ScentCard,
    MBTIComponent,
    AccordDetail,
    ScentCardBase,
    GenerateFromSummaryRequest,
)
from scentmap.app.services.session_service import create_session, update_session_context
from .scent_analysis_service import (
    analyze_scent_type, 
    get_accord_descriptions, 
    load_mbti_data,
    load_accord_mbti_mapping,
    load_accord_type_mapping
)

"""
NCardService: 향기 분석 카드 생성, 저장 및 결과 관리 서비스
"""

logger = logging.getLogger(__name__)

class NCardService:
    def __init__(self):
        """서비스 초기화 및 데이터 로드"""
        self.mbti_data = {item["mbti"]: item for item in load_mbti_data()}
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY")) if os.getenv("OPENAI_API_KEY") else None

    async def _analyze_with_llm(self, mbti: Optional[str], selected_accords: List[str], descriptions: List[Dict]) -> Dict:
        """LLM의 사전지식과 프로젝트 정의를 바탕으로 향 MBTI 및 테마 결정"""
        if not self.client:
            return None
        
        try:
            # 어코드 설명 및 MBTI 정의 컨텍스트 준비
            accord_ctx = "\n".join([f"- {d['accord']}: {d['desc1']}, {d['desc2']}" for d in descriptions])
            
            prompt = f"""
            당신은 향기와 성격의 연결고리를 분석하는 전문 조향사이자 심리 분석가입니다.
            제공된 [향 MBTI 정의]와 [어코드 데이터]를 바탕으로 사용자의 향기 정체성을 결정하세요.

            [향 MBTI 정의 (4개 축)]
            1. E(외향) / I(내향) : 존재 방식 (확산성 및 발산력)
               - E: 공간을 채우는 압도적 존재감 및 화려한 오프닝 (예: Citrus, Fruity, Floral - 밝고 확산적)
               - I: 피부에 밀착되어 은은하게 남는 내밀한 여운 (예: Musk, Amber, Woody - 은은하고 깊이감)

            2. S(감각) / N(직관) : 인식 방식 (묘사의 구체성)
               - S: 원료의 생동감이 느껴지는 직관적이고 사실적인 향 (예: Green, Aquatic, Herbal - 자연 그대로)
               - N: 장면과 기억을 소환하는 추상적이고 서사적인 향 (예: Powdery, Gourmand, Oriental - 상상력 자극)

            3. T(사고) / F(감정) : 감정 질감 (향의 온도와 구조)
               - T: 이성적이고 정돈된 드라이/메탈릭한 구조적 인상 (예: Aromatic, Ozonic, Aldehydic - 차갑고 깔끔)
               - F: 감성을 자극하는 부드럽고 따뜻한 포근한 인상 (예: Vanilla, Floral, Creamy - 따뜻하고 부드러움)

            4. J(판단) / P(인식) : 취향 안정성 (조향의 전형성)
               - J: 균형 잡힌 밸런스의 대중적이고 클래식한 조화 (예: Chypre, Fougère - 전통적 조향 구조)
               - P: 독특한 킥(Kick)이 있는 실험적이고 개성 있는 감성 (예: Oud, Leather, Spicy - 파격적 개성)

            [사용자 데이터]
            - 실제 성격 MBTI: {mbti or '알 수 없음'}
            - 선택한 어코드들: {', '.join(selected_accords)}
            - 어코드 상세 인상:
            {accord_ctx}

            [점수 계산 방법론]
            각 축의 점수는 0~100점 범위이며, 대립되는 두 성향의 합은 100이어야 합니다.
            (예: E가 70점이면 I는 30점, S가 55점이면 N은 45점)

            **Step 1: 각 어코드의 기본 성향 파악**
            - 각 어코드가 4개 축에서 어느 쪽에 가까운지 판단
            - 예시:
              * Floral: E(외향적 확산), N(상상력), F(감성적), J(클래식)
              * Woody: I(은은함), S(자연 그대로), T(구조적), J(전통적)
              * Spicy: E(강렬함), N(상상력), T(날카로움), P(개성적)

            **Step 2: 어코드별 가중치 계산**
            - 사용자가 선택한 어코드 개수로 균등 분배
            - 예: 5개 어코드 선택 시 각 어코드당 20점씩 기여

            **Step 3: 조합 시너지 고려**
            - 비슷한 성향의 어코드가 많으면 그쪽으로 강화 (+10~20점 보너스)
            - 대립되는 어코드가 섞이면 중간값으로 조정
            - 예: Floral + Fruity + Citrus (모두 E 성향) → E 강화

            **Step 4: 사용자 실제 MBTI 반영**
            - 사용자의 성격 MBTI가 제공된 경우, 향 선택에 반영되었을 가능성 고려
            - 단, 향 MBTI는 독립적으로 도출하되, 실제 MBTI와의 연관성을 분석 이유에 포함
            - 가중치: 어코드 조합 70% + 실제 MBTI 영향 30%

            **Step 5: 최종 점수 산출**
            - 각 축별로 0~100 범위로 정규화
            - 대립 성향의 합이 100이 되도록 조정
            - 결과 예시:
              {{
                "E": 72, "I": 28,  // E 성향 강함
                "S": 45, "N": 55,  // N 성향 약간 우세
                "T": 60, "F": 40,  // T 성향 우세
                "J": 38, "P": 62   // P 성향 강함
              }}
              → 도출 MBTI: "ENTP"

            [임무]
            1. 위의 점수 계산 방법론을 따라 각 축(E/I, S/N, T/F, J/P)의 점수를 0~100 범위로 산출하세요.
               - 반드시 대립 성향의 합이 100이 되도록 계산
               - 계산 근거를 "reason" 필드에 상세히 설명

            2. 점수를 기반으로 향 MBTI 4문자를 결정하세요.
               - 각 축에서 50점 이상인 성향 선택

            3. 각 축별로 결정된 성향에 가장 어울리는 어코드를 사용자가 선택한 어코드들 중에서 3개씩 선정하세요.

            4. 위에서 선정된 총 12개의 어코드 중, 가장 사용자에게 어울릴 것 같은 최종 3가지 향(어코드)을 선정하고 각각의 선정 이유를 작성하세요.

            5. 'space', 'moment', 'sensation' 세 가지 테마 중 사용자의 선택 어코드와 가장 잘 어울리는 하나를 '대표 테마'로 선택하세요.

            6. "내면의 [성격 특징]이 [향의 특징]과 닮아 있음"을 강조하며 3문장 내외의 감성 스토리텔링을 작성하세요.

            [응답 형식 (JSON)]
            {{
                "derived_mbti": "결정된 4글자 MBTI",
                "axis_scores": {{
                    "E": 0~100 정수,
                    "I": 0~100 정수 (E + I = 100),
                    "S": 0~100 정수,
                    "N": 0~100 정수 (S + N = 100),
                    "T": 0~100 정수,
                    "F": 0~100 정수 (T + F = 100),
                    "J": 0~100 정수,
                    "P": 0~100 정수 (J + P = 100)
                }},
                "axis_accords": {{
                    "E_or_I": {{"selected": "E 또는 I", "accords": ["어코드1", "어코드2", "어코드3"]}},
                    "S_or_N": {{"selected": "S 또는 N", "accords": ["어코드1", "어코드2", "어코드3"]}},
                    "T_or_F": {{"selected": "T 또는 F", "accords": ["어코드1", "어코드2", "어코드3"]}},
                    "J_or_P": {{"selected": "J 또는 P", "accords": ["어코드1", "어코드2", "어코드3"]}}
                }},
                "final_three_accords": [
                    {{"name": "어코드명", "reason": "선정 이유"}},
                    {{"name": "어코드명", "reason": "선정 이유"}},
                    {{"name": "어코드명", "reason": "선정 이유"}}
                ],
                "selected_theme_type": "space | moment | sensation 중 하나",
                "persona_title": "선택한 테마의 내용 (예: 무지개가 핀 들판의 산들바람)",
                "story": "감성 스토리텔링 문구",
                "reason": "점수 계산 과정과 MBTI 도출 근거를 상세히 설명 (어떤 어코드가 어떤 축에 어떻게 기여했는지, 조합 시너지는 어떠했는지, 사용자 실제 MBTI와의 연관성 등)"
            }}
            """
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "당신은 향기 MBTI 시스템의 핵심 결정 엔진입니다. 반드시 JSON 형식으로만 응답하세요."},
                    {"role": "user", "content": prompt}
                ],
                response_format={ "type": "json_object" }
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"LLM 분석 실패: {e}")
            return None

    async def generate_card(self, session_id: str, mbti: Optional[str] = None, selected_accords: List[str] = []) -> Dict:
        """세션 데이터를 기반으로 향기 분석 카드 생성 및 DB 저장"""
        member_id = None
        try:
            # 세션 ID가 adhoc이 아닌 경우 DB에서 최신 데이터 조회
            if session_id != "adhoc":
                with get_recom_db_connection() as conn:
                    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                        cur.execute("SELECT member_id, selected_accords, device_type FROM TB_SCENT_CARD_SESSION_T WHERE session_id = %s", (session_id,))
                        session = cur.fetchone()
                        if session:
                            member_id = session['member_id']
                            selected_accords = session['selected_accords'] or selected_accords
                            try:
                                context = json.loads(session['device_type']) if session['device_type'] else {}
                                mbti = context.get('mbti') or mbti
                            except: pass
            # 1. 어코드 설명 조회
            descriptions = get_accord_descriptions(selected_accords)
            if not descriptions:
                descriptions = [{"accord": acc, "desc1": acc, "desc2": "향"} for acc in selected_accords]

            # 2. 향 타입 분석
            analysis = analyze_scent_type(selected_accords, descriptions, user_mbti=mbti)
            
            # LLM 기반 심층 분석 시도 (Decision Maker)
            llm_analysis = await self._analyze_with_llm(mbti, selected_accords, descriptions)
            
            if llm_analysis:
                derived_mbti = llm_analysis.get('derived_mbti', analysis.get('derived_mbti'))
                axis_scores = llm_analysis.get('axis_scores', analysis.get('axis_scores'))
                
                # LLM이 결정한 MBTI에 맞춰 페르소나 데이터 로드
                persona_data = self.mbti_data.get(derived_mbti, self.mbti_data.get("INFJ"))
                
                # LLM이 선택한 테마 타입에 따라 제목과 이미지 경로 결정
                theme_type = llm_analysis.get('selected_theme_type', 'space')
                persona_title = llm_analysis.get('persona_title', persona_data['persona'].get(theme_type))
                story = llm_analysis.get('story')
                
                # 이미지 경로도 선택된 테마에 맞춰 매칭
                image_url = persona_data["images"].get(theme_type, persona_data["images"]["space"])
            else:
                # Fallback: 기존 규칙 기반 분석
                derived_mbti = analysis.get('derived_mbti') or mbti or "INFJ"
                axis_scores = analysis.get('axis_scores', {})
                persona_data = self.mbti_data.get(derived_mbti, self.mbti_data.get("INFJ"))
                persona_title = persona_data['persona']['space']
                image_url = persona_data["images"]["space"]
                story = f"당신은 {persona_data['headline'].split('성향은,')[0]}성향을 가지고 계시네요. "
                story += f"오늘 선택하신 {descriptions[0].get('desc1', '향기')}는 {persona_data['persona']['space']}처럼 {persona_data['persona']['keywords'][0]} 당신의 내면과 닮아 있습니다. "
                story += f"이 향기는 당신의 {derived_mbti}다운 {persona_data['persona']['keywords'][1]} 매력을 더욱 돋보이게 해줄 거예요."

            scent_code = derived_mbti # MBTI 코드를 scent_code로 활용
            
            # 3. 컴포넌트 및 추천 어코드 구성
            components = self._generate_mbti_components(axis_scores, scent_code)
            
            # LLM이 선정한 최종 3가지 향 활용
            if llm_analysis and 'final_three_accords' in llm_analysis:
                recommends = llm_analysis['final_three_accords']
            else:
                recommends, _ = self._get_accord_details(analysis, derived_mbti, selected_accords)
            
            # 기피 어코드는 기존 로직 활용
            _, avoids = self._get_accord_details(analysis, derived_mbti, selected_accords)

            # 4. 카드 데이터 조립
            card_data = {
                "mbti": derived_mbti,
                "components": components,
                "recommends": recommends,
                "avoids": avoids,
                "story": story,
                "summary": f"{analysis['type_name']}인 당신에게 어울리는 향기 리포트입니다.",
                "persona_title": persona_title,
                "image_url": image_url,
                "keywords": analysis.get('axis_keywords', persona_data["persona"]["keywords"]),
                "recommended_perfume": self._get_representative_perfume(selected_accords),
                "suggested_accords": analysis.get('type_info', {}).get('harmonious_accords', [])[:3],
                "scent_type": analysis,
                "created_at": datetime.now().isoformat()
            }
            
            # LLM 분석 결과에 축별 어코드 정보가 있으면 추가
            if llm_analysis and 'axis_accords' in llm_analysis:
                card_data["axis_accords"] = llm_analysis['axis_accords']

            # 7. DB 저장
            card_id = self._save_card_to_db(session_id, card_data)

            # 8. 카드 생성 후 새 세션 ID 발급
            from scentmap.app.services.session_service import create_new_session_after_card
            new_session_id = create_new_session_after_card(member_id)

            return {
                "card": card_data,
                "session_id": new_session_id,  # 새로 발급된 세션 ID 반환
                "card_id": str(card_id),
                "generation_method": "template"
            }
        except Exception as e:
            logger.error(f"카드 생성 실패: {e}", exc_info=True)
            raise

    async def generate_card_from_summary(self, req: GenerateFromSummaryRequest) -> Dict:
        """NMap 요약(payload) 기반 카드 생성 (정식 엔드포인트용)"""
        # 1) 요약 노트(top/middle/base)를 합쳐 어코드 목록 구성
        merged = []
        seen = set()
        for bucket in (req.top_notes, req.middle_notes, req.base_notes):
            for acc in bucket:
                if acc and acc not in seen:
                    seen.add(acc)
                    merged.append(acc)

        if not merged:
            raise ValueError("No accords in summary payload")

        # 2) 세션 생성 및 컨텍스트 저장
        session = create_session(member_id=req.member_id, mbti=req.mbti)
        session_id = session["session_id"]

        update_session_context(
            session_id=session_id,
            member_id=req.member_id,
            mbti=req.mbti,
            selected_accords=merged,
        )

        # 3) 기존 카드 생성 엔진 사용 (LLM 포함)
        result = await self.generate_card(session_id, mbti=req.mbti, selected_accords=merged)

        # 4) 요약 텍스트/키워드가 있으면 카드에 반영 (디자인 영향 최소)
        if req.analysis_text:
            result["card"]["summary"] = req.analysis_text
        if req.mood_keywords:
            existing = result["card"].get("keywords") or []
            # mood_keywords를 앞에 두고 중복 제거
            merged_keywords = list(dict.fromkeys(req.mood_keywords + existing))
            result["card"]["keywords"] = merged_keywords

        result["generation_method"] = "nmap_summary"
        return result

    def _generate_mbti_components(self, axis_scores: Dict, scent_code: str) -> List[Dict]:
        """4축 점수 기반 MBTI 컴포넌트 생성 (E/I, S/N, T/F, J/P)"""
        if not scent_code or len(scent_code) != 4: return []
        mapping = load_accord_mbti_mapping()
        axis_desc = mapping.get('axis_descriptions', {})
        
        # improve_plan_v1 기반 축 명칭 정의
        axes = [
            ("존재방식", scent_code[0]), # E/I
            ("인식방식", scent_code[1]), # S/N
            ("감정질감", scent_code[2]), # T/F
            ("취향안정성", scent_code[3]) # J/P
        ]
        return [{"axis": name, "code": code, "desc": axis_desc.get(code, {}).get("description", "")} for name, code in axes]

    def _get_accord_details(self, analysis: Dict, mbti: str, selected: List[str]) -> tuple:
        """추천 및 기피 어코드 상세 정보 생성"""
        # 분석된 MBTI에 기반한 추천 어코드 선정 (v1 기획 반영)
        type_info = analysis.get('type_info', {})
        harmonious = type_info.get('harmonious_accords', [])
        avoid = type_info.get('avoid_accords', [])
        
        recommends = [
            {"name": acc, "reason": f"{mbti} 성향의 {analysis.get('type_name', '')}분들에게 안정감을 주는 향입니다."} 
            for acc in harmonious[:3]
        ]
        avoids = [
            {"name": acc, "reason": "현재의 분위기와 상충되어 집중을 방해할 수 있는 향입니다."} 
            for acc in avoid[:2]
        ]
        return recommends, avoids

    def _get_representative_perfume(self, selected_accords: List[str]) -> Optional[Dict]:
        """선택 어코드 빈도 가중치 기반 대표 향수 조회"""
        if not selected_accords: return None
        try:
            from collections import Counter
            
            # 어코드 빈도 계산 (사용자가 여러 번 클릭한 어코드에 가중치 부여)
            accord_frequency = Counter(selected_accords)
            
            # 상위 빈도 어코드 선정 (최대 8개)
            top_accords = [accord for accord, _ in accord_frequency.most_common(8)]
            
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    placeholders = ','.join(['%s'] * len(top_accords))
                    
                    # CASE 문으로 빈도 가중치를 score에 반영
                    weight_cases = ' + '.join([
                        f"CASE WHEN a.accord = %s THEN {freq} * a.vote ELSE 0 END"
                        for freq in [accord_frequency[acc] for acc in top_accords]
                    ])

                    # 어코드 일치 개수, 빈도 가중치, vote 점수를 종합한 쿼리
                    query = f"""
                        WITH perfume_matches AS (
                            SELECT
                                b.perfume_id,
                                b.perfume_name,
                                b.perfume_brand,
                                b.img_link,
                                COUNT(DISTINCT a.accord) as match_count,
                                SUM(a.vote) as total_vote_score,
                                SUM({weight_cases}) as weighted_score
                            FROM TB_PERFUME_BASIC_M b
                            JOIN TB_PERFUME_ACCORD_M a ON b.perfume_id = a.perfume_id
                            WHERE a.accord IN ({placeholders})
                            GROUP BY b.perfume_id, b.perfume_name, b.perfume_brand, b.img_link
                        )
                        SELECT *,
                               (match_count::float / %s * 100) as match_rate
                        FROM perfume_matches
                        ORDER BY weighted_score DESC, match_count DESC, total_vote_score DESC
                        LIMIT 1
                    """
                    
                    # 파라미터: 어코드(weight_cases용) + 어코드(WHERE IN용) + 총 어코드 개수
                    params = tuple(top_accords) + tuple(top_accords) + (len(set(selected_accords)),)
                    cur.execute(query, params)
                    row = cur.fetchone()
                    
                    if row:
                        return {
                            "id": row["perfume_id"],
                            "name": row["perfume_name"],
                            "brand": row["perfume_brand"],
                            "image": row["img_link"],
                            "match_rate": round(row["match_rate"], 1),
                            "reason": f"선택하신 어코드 중 {row['match_count']}개가 포함되며, 취향 빈도를 반영한 최적의 향수입니다."
                        }
        except Exception as e:
            logger.error(f"대표 향수 조회 실패: {e}")
        return None

    def _save_card_to_db(self, session_id: str, card_data: Dict) -> Any:
        """생성된 카드 데이터를 DB에 저장"""
        # 이미지 확장자 처리 (.jpg -> .png)
        if 'image_url' in card_data:
            card_data['image_url'] = card_data['image_url'].replace('.jpg', '.png')
            
        with get_recom_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO TB_SCENT_CARD_RESULT_T (session_id, card_data, generation_method)
                    VALUES (%s, %s, %s) RETURNING card_id
                """, (session_id, psycopg2.extras.Json(card_data), 'template'))
                card_id = cur.fetchone()[0]
                conn.commit()
                return card_id

    def save_member_card(self, card_id: str, member_id: int) -> Dict:
        """회원 계정에 카드 저장"""
        with get_recom_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE TB_SCENT_CARD_RESULT_T SET saved = TRUE, member_id = %s WHERE card_id = %s", (member_id, card_id))
                conn.commit()

                # 카드 저장 후 새 세션 ID 발급
                from scentmap.app.services.session_service import create_new_session_after_card
                new_session_id = create_new_session_after_card(member_id)

                return {
                    "success": True,
                    "message": "카드가 저장되었습니다. 새로운 세션이 시작되었습니다.",
                    "card_id": card_id,
                    "new_session_id": new_session_id
                }

    def get_member_cards(self, member_id: int, limit: int = 20, offset: int = 0) -> Dict:
        """회원의 저장된 카드 목록 조회"""
        with get_recom_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("SELECT card_id, card_data, created_dt FROM TB_SCENT_CARD_RESULT_T WHERE member_id = %s AND saved = TRUE ORDER BY created_dt DESC LIMIT %s OFFSET %s", (member_id, limit, offset))
                rows = cur.fetchall()
                cards = [{"card_id": str(r['card_id']), "card_data": r['card_data'], "created_at": r['created_dt'].isoformat()} for r in rows]
                return {"cards": cards, "total_count": len(cards)}

ncard_service = NCardService()
