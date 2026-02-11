import React from 'react';
import Link from 'next/link';
import { NMapAnalysisSummary } from '../types';

interface ScentHeaderProps {
  summary: NMapAnalysisSummary;
  meta: {
    [key: string]: number | string | boolean | null | undefined;
  };
}

/**
 * 향수 맵(NMap) 상단 헤더 컴포넌트
 * 페이지 타이틀, 설명 및 메인으로 가기 버튼을 포함합니다.
 */
const ScentHeader = ({ summary, meta }: ScentHeaderProps) => {
  return (
    <header className="flex items-center justify-between pb-8 border-b-2 border-[#E6DDCF]">
      <div className="space-y-2">
        <p className="text-xs uppercase tracking-[0.3em] text-[#7A6B57] font-medium">
          perfume network
        </p>
        <h1 className="text-4xl font-semibold text-[#1F1F1F]">
          향수 지도
        </h1>
        <p className="text-sm text-[#5C5448] max-w-2xl leading-relaxed">
          비슷하면서도 다른, 향수 지도로 새로운 취향을 발견해보세요.
        </p>
        
        {/* 분석 요약 정보가 있을 경우 추가적인 피드백 제공 가능 */}
        {meta.perfume_count && (
          <p className="text-[11px] text-[#9C8D7A] mt-2">
            현재 {meta.perfume_count}개의 향수 데이터를 바탕으로 분석 중입니다.
          </p>
        )}
      </div>
      
      <div className="flex items-center gap-3">
        <Link 
          href="/" 
          className="h-10 px-6 flex items-center justify-center rounded-full border border-[#E2D7C5] bg-white text-[13px] font-semibold text-[#5C5448] hover:bg-[#F8F4EC] transition-colors shadow-sm"
        >
          메인으로
        </Link>
      </div>
    </header>
  );
};

export default ScentHeader;
