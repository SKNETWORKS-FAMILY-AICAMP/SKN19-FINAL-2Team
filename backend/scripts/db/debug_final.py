import psycopg2
import sys

print("="*60)
print("🛠️ DB 접속 최종 진단 (Windows 호환 모드)")
print("="*60)

# [핵심 변경 1] localhost 대신 127.0.0.1 사용 (IPv4 강제)
DB_CONFIG = {
    "host": "127.0.0.1", 
    "port": 5433,
    "dbname": "scentence_db",
    "user": "scentence",
    "password": "scentence2026!"
}

try:
    print(f"접속 시도 중... Target: {DB_CONFIG['host']}:{DB_CONFIG['port']}")
    
    # [핵심 변경 2] 인코딩 옵션 제거 (윈도우 기본값 사용)
    conn = psycopg2.connect(**DB_CONFIG)
    
    print("\n✅ 접속 성공! (문제 해결됨)")
    print("👉 해결책: 코드에서 'localhost' 대신 '127.0.0.1'을 사용하세요.")
    conn.close()

except Exception as e:
    print("\n❌ 접속 실패")
    print("-" * 30)
    
    # [핵심 변경 3] 에러 메시지 깨짐 방지 처리
    try:
        # 윈도우 한글 에러(CP949)를 안전하게 출력 시도
        error_str = str(e)
        print(f"에러 내용: {error_str}")
    except:
        # 그래도 깨지면 날것(bytes)으로 출력
        print(f"에러 내용(해석 불가): {repr(e)}")
        
    print("-" * 30)
    print("위 에러 메시지를 알려주세요.")

print("="*60)