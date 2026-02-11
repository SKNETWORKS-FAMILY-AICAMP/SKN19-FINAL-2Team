"""
필터 옵션 JSON 파일 생성 스크립트
[개선] DB 조회를 정적 JSON 파일로 변환하여 API 호출 제거
"""
import json
import os
import sys
from pathlib import Path

# 프로젝트 루트를 PYTHONPATH에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scentmap.app.services.nmap_service import get_filter_options


def export_filter_options():
    """필터 옵션을 JSON 파일로 내보내기"""
    print("📥 필터 옵션 조회 중...")
    
    try:
        # DB에서 필터 옵션 조회
        options = get_filter_options()
        
        # 프론트엔드 public 디렉토리 경로
        frontend_data_dir = project_root.parent / "frontend" / "public" / "data"
        frontend_data_dir.mkdir(parents=True, exist_ok=True)
        
        output_path = frontend_data_dir / "filter-options.json"
        
        # JSON 파일로 저장
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(options, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 필터 옵션 내보내기 완료: {output_path}")
        print(f"   - 브랜드: {len(options['brands'])}개")
        print(f"   - 계절: {len(options['seasons'])}개")
        print(f"   - 상황: {len(options['occasions'])}개")
        print(f"   - 성별: {len(options['genders'])}개")
        print(f"   - 어코드: {len(options['accords'])}개")
        
    except Exception as e:
        print(f"❌ 필터 옵션 내보내기 실패: {e}")
        raise


if __name__ == "__main__":
    export_filter_options()
