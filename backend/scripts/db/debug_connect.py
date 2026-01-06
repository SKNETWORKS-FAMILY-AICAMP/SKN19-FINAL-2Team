import os
import psycopg2

# [핵심] 윈도우 한글 에러 충돌을 피하기 위해 강제로 인코딩 환경변수 설정
os.environ["PGCLIENTENCODING"] = "utf-8"

print("="*60)
print("🔍 DB 접속 정밀 진단 시작")
print("="*60)

# 테스트할 설정 (현재 사용중인 값)
DB_CONFIG = {
    "host": "localhost",
    "port": 5433,
    "dbname": "scentence_db",
    "user": "scentence",
    "password": "scentence2026!"
}

try:
    print(f"1. 접속 시도 중... (Host: {DB_CONFIG['host']}, Port: {DB_CONFIG['port']})")
    
    # [핵심] lc_messages='C' 옵션: DB 에러 메시지를 강제로 '영어'로 출력하게 함
    # 이렇게 하면 한글 깨짐 현상이 사라지고 진짜 에러가 보입니다.
    conn = psycopg2.connect(
        **DB_CONFIG,
        options="-c client_encoding=utf8 -c lc_messages=C"
    )
    print("\n✅ 접속 성공! (비밀번호와 포트 모두 정상입니다)")
    conn.close()

except psycopg2.OperationalError as e:
    print("\n❌ 접속 실패 (OperationalError)")
    print("-" * 30)
    # 진짜 에러 메시지 출력
    print(f"진짜 에러 내용:\n{e}")
    print("-" * 30)
    
    error_msg = str(e)
    if "Connection refused" in error_msg:
        print("👉 분석: 포트가 닫혀있거나 연결이 거부되었습니다.")
        print("   해결: docker ps로 포트가 5433인지 5432인지 다시 확인하세요.")
    elif "password authentication failed" in error_msg:
        print("👉 분석: 비밀번호가 틀렸습니다.")
    elif "role" in error_msg and "does not exist" in error_msg:
        print("👉 분석: 사용자(scentence)가 DB에 없습니다.")
        
except Exception as e:
    print(f"\n❌ 예상치 못한 에러: {e}")

print("="*60)