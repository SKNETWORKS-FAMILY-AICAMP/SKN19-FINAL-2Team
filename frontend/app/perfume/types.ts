/**
 * 향수 상세 정보 타입 정의
 * Backend API 응답과 1:1 매핑
 */

export interface RatioItem {
  name: string;
  ratio: number; // 0~100 정수 (정규화됨)
}

export interface PerfumeNotes {
  top: string[];
  middle: string[];
  base: string[];
}

export interface PerfumeDetail {
  perfume_id: number;
  name: string;
  brand: string;
  image_url: string | null;
  release_year: number | null;
  concentration: string | null;
  perfumer: string | null;
  notes: PerfumeNotes;
  accords: RatioItem[];
  seasons: RatioItem[];
  occasions: RatioItem[];
}

/**
 * Ratio 정규화 규칙:
 * - 입력 ratio가 <= 1.0이면 ratio * 100으로 간주
 * - 입력 ratio가 > 1.0이면 이미 퍼센트(0~100)로 간주
 * - 결과는 0~100으로 클램프
 * - 표시 퍼센트 반올림: 정수 (예: 33%)
 * - 정렬: 표시 퍼센트 내림차순
 * - 노출: 상위 5개 기본 (나머지는 생략)
 */
