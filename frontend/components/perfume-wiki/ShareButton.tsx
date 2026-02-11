"use client";

/**
 * 공유 버튼 컴포넌트
 * 현재 페이지 URL을 클립보드에 복사하여 공유 기능 제공
 */
import { useState } from "react";

export default function ShareButton() {
  const [showToast, setShowToast] = useState(false);

  const handleShare = async () => {
    try {
      // 현재 페이지 URL을 클립보드에 복사
      await navigator.clipboard.writeText(window.location.href);
      setShowToast(true);
      setTimeout(() => setShowToast(false), 2000);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  };

  return (
    <>
      <button
        type="button"
        onClick={handleShare}
        className="flex items-center gap-2.5 px-5 py-2.5 rounded-full border border-[#EFEFEF] bg-white hover:border-[#C8A24D] hover:shadow-md transition-all duration-300"
        aria-label="공유하기"
      >
        <span className="text-lg text-[#777]">↗</span>
        <span className="text-sm font-semibold text-[#555]">공유</span>
      </button>

      {showToast && (
        <div className="fixed bottom-10 left-1/2 -translate-x-1/2 px-6 py-3.5 rounded-full bg-[#2B2B2B] text-white text-sm font-medium shadow-xl z-50 animate-fade-in">
          링크가 복사되었습니다
        </div>
      )}
    </>
  );
}
