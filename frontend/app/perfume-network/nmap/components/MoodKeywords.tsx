import React from 'react';

interface MoodKeywordsProps {
  keywords: string[];
  representativeColor?: string;
}

/**
 * 향수 맵(NMap) 분위기 키워드 분석 컴포넌트
 * 분석된 향기의 주요 분위기를 키워드 태그 형태로 보여줍니다.
 */
const MoodKeywords = ({ keywords, representativeColor }: MoodKeywordsProps) => {
  // 대표 색상이 없을 경우 기본값 설정
  const themeColor = representativeColor || '#7C3AED';

  return (
    <section className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-[#1F1F1F]">분위기 분석</h2>
        <p className="text-sm text-[#7A6B57]">당신의 취향에서 느껴지는 주요 분위기 키워드입니다.</p>
      </div>

      <div className="bg-white rounded-3xl p-8 border border-[#E6DDCF] shadow-sm relative overflow-hidden">
        {/* 배경에 은은한 테마 색상 효과 */}
        <div 
          className="absolute top-0 right-0 w-32 h-32 blur-[80px] opacity-10 rounded-full"
          style={{ backgroundColor: themeColor }}
        />
        
        <div className="flex flex-wrap gap-3 relative z-10">
          {keywords.length > 0 ? (
            keywords.map((keyword, index) => (
              <div
                key={keyword}
                className="px-5 py-2.5 rounded-full text-sm font-semibold transition-all hover:scale-105"
                style={{ 
                  backgroundColor: index === 0 ? themeColor : '#F8F4EC',
                  color: index === 0 ? '#FFFFFF' : '#5C5448',
                  border: index === 0 ? 'none' : '1px solid #E2D7C5'
                }}
              >
                {index === 0 && <span className="mr-2">✨</span>}
                {keyword}
              </div>
            ))
          ) : (
            <p className="text-sm text-[#9C8D7A] italic">분석된 분위기 키워드가 없습니다.</p>
          )}
        </div>

        {keywords.length > 0 && (
          <div className="mt-8 pt-6 border-t border-[#F5F2EA]">
            <p className="text-xs text-[#7A6B57] leading-relaxed">
              가장 두드러지는 <span className="font-bold" style={{ color: themeColor }}>{keywords[0]}</span> 분위기를 중심으로 
              다양한 향기 스펙트럼이 관찰됩니다. 이 키워드들은 당신의 향기 카드를 구성하는 핵심 요소가 됩니다.
            </p>
          </div>
        )}
      </div>
    </section>
  );
};

export default MoodKeywords;
