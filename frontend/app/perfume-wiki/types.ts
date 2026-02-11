/**
 * 향수 백과 데이터 타입 정의
 */

/** 에피소드 본문의 섹션 타입 */
export type ContentSection = {
  subtitle: string;      // 섹션 제목
  paragraphs: string[];  // 단락 목록
};

/** 에피소드 타입 */
export type Episode = {
  id: string;            // 고유 ID
  tag: string;           // 태그 (예: "EP 1")
  title: string;         // 제목
  summary: string;       // 요약
  date: string;          // 작성일
  thumbnail: string;     // 썸네일 이미지 URL
  readTime?: string;     // 읽기 시간 (예: "3분")
  heroImage?: string;    // 히어로 이미지 URL (없으면 thumbnail 사용)
  content?: ContentSection[]; // 본문 콘텐츠
  tags?: string[];       // 관련 키워드 태그
};

/** 시리즈 타입 */
export type Series = {
  id: string;            // 고유 ID
  title: string;         // 시리즈 제목
  summary: string;       // 시리즈 설명
  thumbnail: string;     // 대표 이미지 URL
  episodes: Episode[];   // 포함된 에피소드 목록
};

/** 시즌 타입 */
export type Season = {
  id: string;            // 고유 ID
  title: string;         // 시즌 제목
  description: string;   // 시즌 설명
  series: Series[];      // 포함된 시리즈 목록
};

/** 전체 향수 백과 데이터 타입 */
export type PerfumeWikiData = {
  seasons: Season[];     // 시즌 목록
};
