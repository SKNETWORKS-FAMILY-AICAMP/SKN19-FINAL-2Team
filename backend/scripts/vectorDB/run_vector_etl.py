import os
import subprocess
import sys

# ==========================================
# 설정: 현재 파일(run_vector_etl.py) 위치 기준
# ==========================================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

def run_script(script_path):
    """스크립트 실행 함수 (에러 시에만 출력)"""
    try:
        # check=True: 에러 발생 시 예외 발생
        # capture_output=False: 자식 스크립트의 출력은 그대로 둠 (디버깅용)
        subprocess.run([sys.executable, script_path], check=True)
    except subprocess.CalledProcessError:
        print(f"[Vector-ETL ERROR] 실행 실패: {os.path.basename(script_path)}", file=sys.stderr)
        sys.exit(1)

def main():
    if not os.path.exists(CURRENT_DIR):
        print(f"[Vector-ETL ERROR] 폴더를 찾을 수 없음: {CURRENT_DIR}", file=sys.stderr)
        sys.exit(1)

    # 'load_'로 시작하는 파이썬 파일 찾기 (자기 자신 제외)
    scripts = [f for f in os.listdir(CURRENT_DIR) 
               if f.startswith("load_") and f.endswith(".py") and f != "run_vector_etl.py"]
    
    # 발견된 스크립트 순차 실행
    for script in scripts:
        full_path = os.path.join(CURRENT_DIR, script)
        run_script(full_path)

if __name__ == "__main__":
    main()