"use client";

import React, { useState, useEffect } from 'react';

/**
 * 향수 맵 및 카드 생성 시 사용되는 공통 로딩 오버레이
 */
const LoadingOverlay = () => {
  const [loadingMessages, setLoadingMessages] = useState([
    "당신의 향기를 분석 중입니다",
    "탐색하신 데이터를 바탕으로...",
    "세상에 하나뿐인\n향기카드를 만들고 있어요",
    "거의 다 되었어요!"
  ]);
  const [currentMessageIdx, setCurrentMessageIdx] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentMessageIdx((prev) => (prev + 1) % loadingMessages.length);
    }, 2000);
    return () => clearInterval(interval);
  }, [loadingMessages.length]);

  return (
    <div className="fixed inset-0 z-[200] flex flex-col items-center justify-center bg-[#F8F4EC]/90 backdrop-blur-xl animate-in fade-in duration-700">
      <div className="relative w-32 h-32 mb-10">
        {/* 다중 레이어 애니메이션 */}
        <div className="absolute inset-0 bg-[#C8A24D]/10 rounded-full animate-ping duration-[3000ms]"></div>
        <div className="absolute inset-4 bg-[#C8A24D]/5 rounded-full animate-pulse"></div>

        {/* 중앙 아이콘 */}
        <div className="absolute inset-0 flex items-center justify-center text-5xl animate-bounce duration-[2000ms]">
          🫧
        </div>

        {/* 정교한 회전 링 */}
        <div className="absolute inset-0 border-[1px] border-[#C8A24D]/20 rounded-full"></div>
        <div className="absolute inset-0 border-t-2 border-r-2 border-[#C8A24D] rounded-full animate-spin duration-[1500ms]"></div>
      </div>

      <div className="text-center space-y-4 px-6">
        <h3 className="text-2xl font-serif italic text-[#1F1F1F] tracking-tight transition-all duration-500 whitespace-pre-line">
          {loadingMessages[currentMessageIdx]}
        </h3>
        <p className="text-sm text-[#7A6B57] max-w-[280px] mx-auto leading-relaxed font-light">
          잠시만 기다려주세요.<br />
          당신의 취향을 시적인 문장으로<br />
          빚어내고 있습니다.
        </p>
      </div>

      {/* 우아한 진행 바 */}
      <div className="mt-16 w-64 h-[2px] bg-[#E6DDCF] rounded-full overflow-hidden">
        <div className="h-full bg-gradient-to-r from-[#E6DDCF] via-[#C8A24D] to-[#E6DDCF] animate-progress-shimmer w-full origin-left"></div>
      </div>

      <style jsx>{`
        @keyframes progress-shimmer {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(100%); }
        }
        .animate-progress-shimmer {
          animation: progress-shimmer 2.5s infinite linear;
        }
      `}</style>
    </div>
  );
};

export default LoadingOverlay;
