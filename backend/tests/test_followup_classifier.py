"""
Follow-up 판별기 테스트

목적: 규칙 기반 판별기의 정확도 검증
"""

import pytest
from backend.agent.followup_classifier import (
    classify_followup_rule_based,
    FollowUpIntent,
)


class TestFollowUpClassifier:
    """Follow-up 판별기 테스트"""

    def test_first_request_no_context(self):
        """첫 요청 (컨텍스트 없음) → NEW_RECO"""
        result = classify_followup_rule_based(
            current_query="딥디크 향수 추천해줘",
            previous_context=None
        )

        assert result.is_followup is False
        assert result.intent == "NEW_RECO"
        assert result.confidence == 1.0

    def test_more_recommendation_simple(self):
        """후속: "더 추천해줘" → MORE_RECO"""
        prev_context = {
            "user_preferences": {
                "brand": "딥디크",
                "gender": "Men",
                "season": "겨울"
            }
        }

        result = classify_followup_rule_based(
            current_query="더 추천해줘",
            previous_context=prev_context
        )

        assert result.is_followup is True
        assert result.intent == "MORE_RECO"
        assert "brand" in result.keep_slots
        assert "season" in result.keep_slots
        assert len(result.drop_slots) == 0

    def test_more_recommendation_variants(self):
        """후속 요청 변형들"""
        prev_context = {"user_preferences": {"brand": "조말론"}}

        test_cases = [
            "다른 거 추천",
            "다른 것도 보여줘",
            "또 있어?",
            "비슷한 거",
            "이거 말고",
        ]

        for query in test_cases:
            result = classify_followup_rule_based(query, prev_context)
            assert result.is_followup is True, f"Failed for: {query}"
            assert result.intent == "MORE_RECO", f"Failed for: {query}"

    def test_target_change_keywords(self):
        """대상 전환 → NEW_RECO (높은 신뢰도)"""
        prev_context = {"user_preferences": {"brand": "딥디크", "target": "남성"}}

        test_cases = [
            ("부모님 선물로", ["부모님", "선물"]),
            ("여자친구 향수 추천", ["여자친구"]),
            ("데이트용으로", ["데이트"]),
        ]

        for query, expected_keywords in test_cases:
            result = classify_followup_rule_based(query, prev_context)

            assert result.is_followup is False, f"Failed for: {query}"
            assert result.intent == "NEW_RECO", f"Failed for: {query}"
            assert result.confidence >= 0.9, f"Failed for: {query}"
            # 모든 제약 제거
            assert "brand" in result.drop_slots, f"Failed for: {query}"

    def test_explicit_reset(self):
        """명시적 리셋 → RESET"""
        prev_context = {"user_preferences": {"brand": "딥디크"}}

        test_cases = [
            "아까 건 잊고 새로 추천",
            "다시 처음부터",
            "아까거 말고 새로",
        ]

        for query in test_cases:
            result = classify_followup_rule_based(query, prev_context)

            assert result.is_followup is False, f"Failed for: {query}"
            assert result.intent == "RESET", f"Failed for: {query}"
            assert len(result.drop_slots) > 0, f"Failed for: {query}"

    def test_info_query(self):
        """정보 질문 → INFO_QUERY"""
        prev_context = {"user_preferences": {"brand": "딥디크"}}

        test_cases = [
            "이 향수 어때?",
            "딥디크가 뭐야?",
            "지속력 어떤가요?",
            "A랑 B 차이가 뭐야?",
        ]

        for query in test_cases:
            result = classify_followup_rule_based(query, prev_context)

            assert result.intent == "INFO_QUERY", f"Failed for: {query}"

    def test_short_query_followup_assumption(self):
        """짧은 쿼리 → 후속 추정 (낮은 신뢰도)"""
        prev_context = {"user_preferences": {"brand": "딥디크"}}

        result = classify_followup_rule_based("추천", prev_context)

        assert result.is_followup is True
        assert result.intent == "MORE_RECO"
        assert result.confidence <= 0.7  # 낮은 신뢰도

    def test_ambiguous_query(self):
        """애매한 쿼리 → NEW_RECO (기본값, 중간 신뢰도)"""
        prev_context = {"user_preferences": {"brand": "딥디크"}}

        result = classify_followup_rule_based(
            "겨울 남자 향수 알려줘",
            prev_context
        )

        # 애매하지만 구체적인 조건이 있으므로 NEW_RECO
        assert result.is_followup is False
        assert result.intent == "NEW_RECO"

    def test_confidence_thresholds(self):
        """신뢰도 검증"""
        prev_context = {"user_preferences": {"brand": "딥디크"}}

        # 높은 신뢰도: 대상 전환
        high_conf = classify_followup_rule_based("부모님 선물", prev_context)
        assert high_conf.confidence >= 0.9

        # 중간 신뢰도: 후속 요청
        mid_conf = classify_followup_rule_based("더 추천", prev_context)
        assert 0.7 <= mid_conf.confidence < 1.0

        # 낮은 신뢰도: 짧은 쿼리
        low_conf = classify_followup_rule_based("추천", prev_context)
        assert low_conf.confidence < 0.7


class TestFollowUpIntegration:
    """통합 시나리오 테스트"""

    def test_scenario_same_brand_more(self):
        """
        시나리오: 딥디크 추천 → 더 추천
        기대: brand 유지
        """
        # 1턴: 딥디크 추천
        context1 = {"user_preferences": {"brand": "딥디크", "gender": "Men"}}

        # 2턴: 더 추천
        result2 = classify_followup_rule_based("더 추천해줘", context1)

        assert result2.is_followup is True
        assert result2.intent == "MORE_RECO"
        assert "brand" in result2.keep_slots
        assert "딥디크" == context1["user_preferences"]["brand"]  # 유지 확인

    def test_scenario_topic_change(self):
        """
        시나리오: 딥디크 남성 → 부모님 선물
        기대: 모든 제약 제거
        """
        # 1턴: 딥디크 남성
        context1 = {
            "user_preferences": {
                "brand": "딥디크",
                "gender": "Men",
                "target": "남성"
            }
        }

        # 2턴: 부모님 선물
        result2 = classify_followup_rule_based("부모님 선물로 추천", context1)

        assert result2.is_followup is False
        assert result2.intent == "NEW_RECO"
        assert "brand" in result2.drop_slots
        assert "target" in result2.drop_slots

    def test_scenario_reset_then_new(self):
        """
        시나리오: 딥디크 → 아까 건 잊고 새로
        기대: RESET, 모든 제약 제거
        """
        context1 = {"user_preferences": {"brand": "딥디크", "season": "겨울"}}

        result2 = classify_followup_rule_based("아까 건 잊고 새로 추천", context1)

        assert result2.intent == "RESET"
        assert len(result2.drop_slots) > 0
        assert "brand" in result2.drop_slots
