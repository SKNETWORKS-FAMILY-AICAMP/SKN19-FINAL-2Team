"""
개수 안내 메시지 테스트
- 명시적 요청 vs 묵시적 요청 구분
- 과다 요청, 부족 결과, 정상 케이스
"""


def generate_count_notice(
    requested: int,
    actual: int,
    is_explicit: bool
) -> str:
    """
    추천 개수 관련 안내 메시지를 생성합니다.

    Args:
        requested: 요청된 개수 (명시적 또는 디폴트)
        actual: 실제 생성된 개수
        is_explicit: 사용자가 명시적으로 개수를 요청했는지

    Returns:
        안내 메시지 (필요 없으면 빈 문자열)
    """
    MAX_COUNT = 5

    # 케이스 1: 과다 요청 (명시적일 때만)
    if is_explicit and requested > MAX_COUNT:
        return (f"💡 안내: 한 번에 최대 {MAX_COUNT}개까지만 추천이 가능합니다. "
                f"{MAX_COUNT}개의 향수를 엄선하여 추천드리겠습니다.\n\n")

    # 케이스 2: 부분 실패 (명시적 요청일 때만!)
    if is_explicit and actual < requested:
        return (f"💡 안내: 요청하신 {requested}개 중 {actual}개의 향수를 찾았습니다. "
                f"조건에 맞는 향수가 제한적이었습니다.\n\n")

    # 케이스 3: 묵시적이거나 정상 → 아무 말 안 함
    return ""


def test_case(name: str, requested: int, actual: int, is_explicit: bool, expected: str):
    """테스트 케이스 실행"""
    result = generate_count_notice(requested, actual, is_explicit)

    # 결과 출력
    print(f"\n{'='*70}")
    print(f"🧪 테스트: {name}")
    print(f"{'='*70}")
    print(f"📥 입력:")
    print(f"   - 요청 개수: {requested}")
    print(f"   - 실제 개수: {actual}")
    print(f"   - 명시적 여부: {'✅ 명시적' if is_explicit else '❌ 묵시적 (디폴트)'}")
    print(f"\n📤 출력:")
    if result:
        print(f"   {result.strip()}")
    else:
        print(f"   (안내 없음)")

    # 검증
    is_pass = (result != "") == (expected != "")
    status = "✅ PASS" if is_pass else "❌ FAIL"
    print(f"\n{status}")

    if not is_pass:
        print(f"   예상: {'(안내 있음)' if expected else '(안내 없음)'}")
        print(f"   실제: {'(안내 있음)' if result else '(안내 없음)'}")

    return is_pass


def run_all_tests():
    """모든 테스트 실행"""
    print("\n" + "="*70)
    print("🚀 개수 안내 메시지 테스트 시작")
    print("="*70)

    results = []

    # ========================================
    # 1. 명시적 과다 요청 케이스
    # ========================================
    results.append(test_case(
        name="명시적 과다 요청 (10개 → 5개 제한)",
        requested=10,
        actual=5,
        is_explicit=True,
        expected="has_notice"  # 안내 있어야 함
    ))

    results.append(test_case(
        name="명시적 과다 요청 (7개 → 5개 제한)",
        requested=7,
        actual=5,
        is_explicit=True,
        expected="has_notice"  # 안내 있어야 함
    ))

    # ========================================
    # 2. 명시적 부족 결과 케이스
    # ========================================
    results.append(test_case(
        name="명시적 부족 (4개 요청 → 2개만 찾음)",
        requested=4,
        actual=2,
        is_explicit=True,
        expected="has_notice"  # 안내 있어야 함
    ))

    results.append(test_case(
        name="명시적 부족 (5개 요청 → 3개만 찾음)",
        requested=5,
        actual=3,
        is_explicit=True,
        expected="has_notice"  # 안내 있어야 함
    ))

    results.append(test_case(
        name="명시적 부족 (2개 요청 → 1개만 찾음)",
        requested=2,
        actual=1,
        is_explicit=True,
        expected="has_notice"  # 안내 있어야 함
    ))

    # ========================================
    # 3. 명시적 정상 케이스 (안내 없어야 함)
    # ========================================
    results.append(test_case(
        name="명시적 정상 (3개 요청 → 3개 성공)",
        requested=3,
        actual=3,
        is_explicit=True,
        expected=""  # 안내 없어야 함
    ))

    results.append(test_case(
        name="명시적 정상 (5개 요청 → 5개 성공)",
        requested=5,
        actual=5,
        is_explicit=True,
        expected=""  # 안내 없어야 함
    ))

    # ========================================
    # 4. 묵시적 케이스 (모두 안내 없어야 함)
    # ========================================
    results.append(test_case(
        name="묵시적 부족 (디폴트 3개 → 2개만 찾음)",
        requested=3,
        actual=2,
        is_explicit=False,
        expected=""  # 안내 없어야 함 ⭐
    ))

    results.append(test_case(
        name="묵시적 부족 (디폴트 3개 → 1개만 찾음)",
        requested=3,
        actual=1,
        is_explicit=False,
        expected=""  # 안내 없어야 함 ⭐
    ))

    results.append(test_case(
        name="묵시적 정상 (디폴트 3개 → 3개 성공)",
        requested=3,
        actual=3,
        is_explicit=False,
        expected=""  # 안내 없어야 함
    ))

    # ========================================
    # 5. Edge Case: 묵시적인데 과다 요청?
    # (이런 케이스는 실제로 발생하지 않지만 테스트)
    # ========================================
    results.append(test_case(
        name="묵시적 과다 (10개 → 5개) - 실제로는 발생 안 함",
        requested=10,
        actual=5,
        is_explicit=False,
        expected=""  # 안내 없어야 함 (묵시적이므로)
    ))

    # ========================================
    # 최종 결과
    # ========================================
    print("\n" + "="*70)
    print("📊 테스트 결과 요약")
    print("="*70)

    total = len(results)
    passed = sum(results)
    failed = total - passed

    print(f"✅ 통과: {passed}/{total}")
    print(f"❌ 실패: {failed}/{total}")

    if failed == 0:
        print("\n🎉 모든 테스트 통과!")
    else:
        print(f"\n⚠️ {failed}개 테스트 실패")

    print("="*70 + "\n")

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
