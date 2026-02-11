"""
Follow-up 판별기 수동 테스트

pytest 없이 실행 가능한 간단한 테스트
"""

import sys
from pathlib import Path

# 경로 추가
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from agent.followup_classifier import classify_followup_rule_based


def test_cases():
    """대표 테스트 케이스 실행"""

    print("=" * 60)
    print("Follow-up 판별기 테스트")
    print("=" * 60)

    test_data = [
        # (쿼리, 이전컨텍스트, 기대intent, 설명)
        ("딥디크 추천", None, "NEW_RECO", "첫 요청"),
        ("더 추천해줘", {"user_preferences": {"brand": "딥디크"}}, "MORE_RECO", "후속 요청"),
        ("다른 거 있어?", {"user_preferences": {"brand": "조말론"}}, "MORE_RECO", "후속 변형"),
        ("부모님 선물로", {"user_preferences": {"brand": "딥디크"}}, "NEW_RECO", "대상 전환"),
        ("아까 건 잊고", {"user_preferences": {"brand": "딥디크"}}, "RESET", "명시적 리셋"),
        ("이 향수 어때?", {"user_preferences": {"brand": "딥디크"}}, "INFO_QUERY", "정보 질문"),
    ]

    passed = 0
    failed = 0

    for idx, (query, context, expected_intent, description) in enumerate(test_data, 1):
        result = classify_followup_rule_based(query, context)

        success = result.intent == expected_intent
        status = "✅ PASS" if success else "❌ FAIL"

        if success:
            passed += 1
        else:
            failed += 1

        print(f"\n{idx}. {description}")
        print(f"   쿼리: \"{query}\"")
        print(f"   {status}")
        print(f"   - 기대: {expected_intent}")
        print(f"   - 실제: {result.intent}")
        print(f"   - 신뢰도: {result.confidence:.2f}")
        print(f"   - 근거: {result.reason}")

        if result.keep_slots:
            print(f"   - 유지: {result.keep_slots}")
        if result.drop_slots:
            print(f"   - 제거: {result.drop_slots}")

    print("\n" + "=" * 60)
    print(f"결과: {passed} 통과 / {failed} 실패 (총 {len(test_data)}개)")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = test_cases()
    sys.exit(0 if success else 1)
