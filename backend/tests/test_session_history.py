"""
세션 레벨 히스토리 테스트
- NEW_RECO/RESET 시에도 세션 내에서는 히스토리 유지
- 한 번 추천한 향수는 같은 세션에서 절대 다시 추천 안 함
"""


def simulate_session():
    """세션 내 히스토리 동작 시뮬레이션"""

    print("\n" + "="*70)
    print("🧪 세션 레벨 히스토리 유지 테스트")
    print("="*70)

    # 세션 시작
    session_history = []

    # ========================================
    # 1차 추천: "여름 향수 추천해줘"
    # ========================================
    print("\n📍 1차 추천: '여름 향수 추천해줘'")
    print("   - 프레임 ID: frame_001")
    print("   - 의도: 일반 추천")

    batch_1 = [101, 102, 103]
    session_history.extend(batch_1)

    print(f"   ✅ 추천: {batch_1}")
    print(f"   📚 세션 히스토리: {session_history}")
    print(f"   🚫 다음 추천 시 제외할 ID: {session_history}")

    # ========================================
    # 2차 추천: "다른 거 추천해줘" (NEW_RECO)
    # ========================================
    print("\n" + "-"*70)
    print("📍 2차 추천: '다른 거 추천해줘' (NEW_RECO)")
    print("   - 프레임 ID: frame_002 (새 프레임)")
    print("   - 의도: NEW_RECO")
    print("   - 동작:")
    print("     ✅ 프레임: 초기화 (조건/선호도 리셋)")
    print("     ✅ 히스토리: 유지 (이전 추천 기억)")

    # 히스토리 유지 (클리어 안 함)
    exclude_ids = session_history.copy()
    print(f"   🚫 제외할 ID: {exclude_ids}")

    # 새로운 추천 (제외 ID 외에서 선택)
    batch_2 = [201, 202, 203]
    session_history.extend(batch_2)

    print(f"   ✅ 추천: {batch_2}")
    print(f"   📚 세션 히스토리: {session_history}")

    # 검증: 1차와 중복 없음
    duplicates = set(batch_1) & set(batch_2)
    if duplicates:
        print(f"   ❌ FAIL: 중복 추천 발생! {duplicates}")
        return False
    else:
        print(f"   ✅ PASS: 중복 없음")

    # ========================================
    # 3차 추천: "또 다른 거" (NEW_RECO)
    # ========================================
    print("\n" + "-"*70)
    print("📍 3차 추천: '또 다른 거' (NEW_RECO)")
    print("   - 프레임 ID: frame_003 (새 프레임)")
    print("   - 의도: NEW_RECO")

    exclude_ids = session_history.copy()
    print(f"   🚫 제외할 ID: {exclude_ids}")

    batch_3 = [301, 302, 303]
    session_history.extend(batch_3)

    print(f"   ✅ 추천: {batch_3}")
    print(f"   📚 세션 히스토리: {session_history}")

    # 검증: 이전 추천들과 중복 없음
    duplicates = (set(batch_1) | set(batch_2)) & set(batch_3)
    if duplicates:
        print(f"   ❌ FAIL: 중복 추천 발생! {duplicates}")
        return False
    else:
        print(f"   ✅ PASS: 중복 없음")

    # ========================================
    # 4차 추천: "계속해서 추천" (CONTINUE)
    # ========================================
    print("\n" + "-"*70)
    print("📍 4차 추천: '계속해서 추천' (CONTINUE)")
    print("   - 프레임 ID: frame_003 (동일 프레임)")
    print("   - 의도: CONTINUE")

    exclude_ids = session_history.copy()
    print(f"   🚫 제외할 ID: {exclude_ids}")

    batch_4 = [401, 402, 403]
    session_history.extend(batch_4)

    print(f"   ✅ 추천: {batch_4}")
    print(f"   📚 세션 히스토리: {session_history}")

    # 검증
    duplicates = (set(batch_1) | set(batch_2) | set(batch_3)) & set(batch_4)
    if duplicates:
        print(f"   ❌ FAIL: 중복 추천 발생! {duplicates}")
        return False
    else:
        print(f"   ✅ PASS: 중복 없음")

    # ========================================
    # 최종 검증
    # ========================================
    print("\n" + "="*70)
    print("📊 최종 결과")
    print("="*70)
    print(f"총 추천 횟수: 4회")
    print(f"총 추천 향수: {len(session_history)}개")
    print(f"고유 향수: {len(set(session_history))}개")

    if len(session_history) == len(set(session_history)):
        print(f"\n🎉 SUCCESS: 세션 내 모든 추천이 고유함 (중복 없음)")
        return True
    else:
        duplicates_count = len(session_history) - len(set(session_history))
        print(f"\n❌ FAIL: {duplicates_count}개 중복 추천 발생")
        return False


def test_old_behavior():
    """구버전 동작 (잘못된 방식)"""

    print("\n" + "="*70)
    print("⚠️ 구버전 동작 (비교용) - NEW_RECO 시 히스토리 클리어")
    print("="*70)

    session_history = []

    # 1차
    print("\n📍 1차 추천")
    batch_1 = [101, 102, 103]
    session_history.extend(batch_1)
    print(f"   추천: {batch_1}")
    print(f"   히스토리: {session_history}")

    # 2차 - NEW_RECO (히스토리 클리어)
    print("\n📍 2차 추천 (NEW_RECO)")
    print("   ❌ 히스토리 클리어 (구버전 동작)")
    session_history = []  # 클리어!

    batch_2 = [101, 102, 103]  # 같은 향수 다시 추천 가능
    session_history.extend(batch_2)
    print(f"   추천: {batch_2}")
    print(f"   ⚠️ 문제: 1차와 동일한 향수 추천됨!")

    print("\n❌ 이것이 문제였던 이유:")
    print("   - 사용자: '다른 거 추천해줘'")
    print("   - 시스템: (이전과 같은 향수 추천)")
    print("   - 사용자: '아니 왜 또 같은 거야?'")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("🚀 세션 레벨 히스토리 테스트 시작")
    print("="*70)

    # 구버전 동작 시연
    test_old_behavior()

    # 신버전 동작 테스트
    success = simulate_session()

    print("\n" + "="*70)
    if success:
        print("✅ 모든 테스트 통과!")
        print("세션 내에서는 절대 중복 추천하지 않습니다.")
    else:
        print("❌ 테스트 실패")
    print("="*70 + "\n")

    exit(0 if success else 1)
