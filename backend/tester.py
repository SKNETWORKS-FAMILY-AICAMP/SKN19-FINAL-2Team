import requests
import json
import time
import os
from datetime import datetime

# ==========================================
# ⚙️ 설정 (Configuration)
# ==========================================
BASE_URL = "http://localhost:8000/chat"
TODAY = datetime.now().strftime("%Y-%m-%d")
REPORT_FILE = f"test_{TODAY}.md"

# GPT-5.2 (High Performance) 단가
COST_INPUT_PER_1M = 1.750
COST_OUTPUT_PER_1M = 14.000

# ==========================================
# 📝 리포트 관리 (Report Manager)
# ==========================================
def init_report_file():
    """파일이 없으면 헤더를 생성합니다."""
    if not os.path.exists(REPORT_FILE):
        headers = [
            "테스트 시간", "테스트 목적", "상세 시나리오", "테스트 환경", 
            "입력 데이터", "기대 출력", "실제 출력 (요약)", 
            "응답 소요 시간(초)", "토큰 사용량 (In/Out)", "예상 비용($)", "분석 및 개선점"
        ]
        with open(REPORT_FILE, "w", encoding="utf-8") as f:
            f.write(f"# 🧪 자동화 테스트 리포트 ({TODAY})\n\n")
            f.write("| " + " | ".join(headers) + " |\n")
            f.write("|" + "---|" * len(headers) + "\n")
            print(f"[Info] 새로운 리포트 파일 생성: {REPORT_FILE}")

def append_to_report(data):
    """결과 데이터를 마크다운 표의 한 행으로 추가합니다."""
    init_report_file()
    
    # 마크다운 표 깨짐 방지: 줄바꿈, 파이프(|) 문자 제거/치환
    row_values = []
    for item in data:
        # None 타입 안전 처리 및 문자열 변환
        safe_str = str(item) if item is not None else ""
        safe_str = safe_str.replace("|", "\|").replace("\n", "<br>")
        row_values.append(safe_str)
        
    line = "| " + " | ".join(row_values) + " |\n"
    
    with open(REPORT_FILE, "a", encoding="utf-8") as f:
        f.write(line)
    print(f"[Info] 리포트 기록 완료: {data[6][:20]}...")

def calculate_cost(input_tokens, output_tokens):
    """비용 계산 (USD)"""
    cost = (input_tokens * COST_INPUT_PER_1M + output_tokens * COST_OUTPUT_PER_1M) / 1_000_000
    return round(cost, 6) # 소수점 6자리까지

# ==========================================
# 🚀 테스트 실행 (Test Runner)
# ==========================================
def run_test(purpose, scenario, user_query, expected_output, env="Local/GPT-5.2"):
    print(f"\n▶️ 테스트 시작: {scenario}")
    
    start_time = time.time()
    
    # 요청 데이터 (매번 새로운 스레드 ID 생성)
    payload = {
        "user_query": user_query,
        "thread_id": f"test_thread_{int(time.time())}"
    }
    
    final_answer = ""
    usage_data = {"input": 0, "output": 0}
    
    try:
        # 스트리밍 요청 보내기
        with requests.post(BASE_URL, json=payload, stream=True) as response:
            if response.status_code != 200:
                final_answer = f"[Error] HTTP {response.status_code}"
                
            for line in response.iter_lines():
                if not line: continue
                decoded_line = line.decode('utf-8')
                
                if decoded_line.startswith("data: "):
                    json_str = decoded_line[6:] # "data: " 제거
                    try:
                        data = json.loads(json_str)
                        
                        if data["type"] == "answer":
                            final_answer = data["content"]
                            # 토큰 정보가 있으면 갱신 (Main에서 보내준 usage)
                            if "usage" in data:
                                usage_data = data["usage"]
                                
                        elif data["type"] == "error":
                            final_answer = f"[System Error] {data['content']}"
                            
                    except json.JSONDecodeError:
                        pass
                        
    except Exception as e:
        final_answer = f"[Exception] {str(e)}"
    
    end_time = time.time()
    duration = round(end_time - start_time, 2)
    
    # ---------------------------
    # 데이터 정리
    # ---------------------------
    in_tokens = usage_data.get("input", 0)
    out_tokens = usage_data.get("output", 0)
    total_tokens = in_tokens + out_tokens
    
    cost = calculate_cost(in_tokens, out_tokens)
    
    # 실제 출력 요약 (앞 50자 + ...)
    summary_output = final_answer[:50] + "..." if len(final_answer) > 50 else final_answer
    
    # 리포트 행 데이터 구성 (11개 컬럼)
    report_row = [
        datetime.now().strftime("%H:%M:%S"), # 1. 시간
        purpose,                             # 2. 목적
        scenario,                            # 3. 시나리오
        env,                                 # 4. 환경
        user_query,                          # 5. 입력
        expected_output,                     # 6. 기대
        summary_output,                      # 7. 출력(요약)
        f"{duration}s",                      # 8. 시간
        f"{total_tokens} (In:{in_tokens}/Out:{out_tokens})", # 9. 토큰
        f"${cost}",                          # 10. 비용
        ""                                   # 11. 비고 (수동)
    ]
    
    append_to_report(report_row)
    print(f"✅ 테스트 종료. 비용: ${cost}")

# ==========================================
# 🏁 메인 실행부
# ==========================================
if __name__ == "__main__":
    import sys
    
    # 기본값
    query = "시크한 느낌의 향수 추천해줘"
    
    # 1. 커맨드라인 인자 확인 (예: python tester.py "여름 향수")
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    # 2. 아니면 사용자에게 직접 물어보기
    else:
        print("\n👇 테스트할 문장을 입력하세요 (그냥 엔터치면 '시크한...' 실행)")
        user_input = input("입력: ").strip()
        if user_input:
            query = user_input

    # 실행
    run_test(
        purpose="Manual Input Test", 
        scenario=f"Custom Query: {query}", 
        user_query=query, 
        expected_output="AI 응답 생성"
    )