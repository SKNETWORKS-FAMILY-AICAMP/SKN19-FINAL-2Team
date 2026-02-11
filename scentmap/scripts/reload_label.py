"""
라벨 데이터 수동 재로드 배치 스크립트

DB의 한글 매핑 데이터를 다시 로드하여 메모리 캐시를 갱신합니다.

실행 방법:
    cd Scentence\scentmap
    python scripts/reload_label.py

또는 API를 통한 갱신:
    curl -X POST http://localhost:8001/labels/reload
"""

import sys
import os

# 상위 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.label_service import load_labels, get_labels_metadata
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """라벨 데이터 재로드 실행"""
    logger.info("=" * 60)
    logger.info("라벨 데이터 수동 재로드 시작")
    logger.info("=" * 60)
    
    try:
        # 라벨 데이터 로드
        labels = load_labels()
        
        # 메타데이터 확인
        metadata = get_labels_metadata()
        
        logger.info("")
        logger.info("📊 재로드 완료 - 데이터 통계:")
        logger.info(f"  - 향수명: {metadata['counts']['perfume_names']:,}개")
        logger.info(f"  - 브랜드: {metadata['counts']['brands']:,}개")
        logger.info(f"  - 어코드: {metadata['counts']['accords']:,}개")
        logger.info(f"  - 계절: {metadata['counts']['seasons']:,}개")
        logger.info(f"  - 상황: {metadata['counts']['occasions']:,}개")
        logger.info(f"  - 성별: {metadata['counts']['genders']:,}개")
        logger.info(f"  - 로드 시간: {metadata['loaded_at']}")
        logger.info("")
        logger.info("=" * 60)
        logger.info("✅ 라벨 데이터 재로드 성공")
        logger.info("=" * 60)
        
        return 0
        
    except Exception as e:
        logger.error("")
        logger.error("=" * 60)
        logger.error(f"❌ 라벨 데이터 재로드 실패: {e}")
        logger.error("=" * 60)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
