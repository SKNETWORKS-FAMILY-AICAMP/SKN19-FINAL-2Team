"use client";

import React from 'react';
import { NScentCard } from './NScentCard';
import { ScentCard } from './ncard-service';

interface ScentCardModalProps {
  card: ScentCard;
  onClose: () => void;
  onSave?: () => void;
  onContinueExplore?: () => void;
  isLoggedIn: boolean;
  userName?: string;
}

/**
 * 향기 카드 결과 모달 컴포넌트
 * NScentCard UI를 재사용하여 모달 형태로 표시합니다.
 */
const ScentCardModal = ({ 
  card, 
  onClose, 
  onSave, 
  onContinueExplore, 
  isLoggedIn,
  userName 
}: ScentCardModalProps) => {
  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 sm:p-6">
      {/* 배경 블러 및 어둡게 */}
      <div 
        className="absolute inset-0 bg-[#2E2B28]/60 backdrop-blur-md"
        onClick={onClose}
      />

      {/* 모달 컨텐츠 */}
      <div className="relative w-full max-w-[480px] bg-white rounded-[32px] shadow-2xl overflow-hidden animate-in fade-in zoom-in duration-300">
        {/* 상단 닫기 버튼 */}
        <button 
          onClick={onClose}
          className="absolute top-6 right-6 z-[110] w-10 h-10 flex items-center justify-center rounded-full bg-white/80 border border-[#E6DDCF] text-[#7A6B57] hover:bg-white transition-colors"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>

        <div className="max-h-[90vh] overflow-y-auto custom-scrollbar p-6 pt-12">
          <div className="text-center mb-8">
            <h2 className="text-2xl font-bold text-[#1F1F1F] mb-2">당신만의 향기 카드</h2>
            <p className="text-sm text-[#7A6B57]">탐색한 향기들을 분석하여 특별한 카드를 생성했습니다.</p>
          </div>

          {/* 실제 카드 UI (NScentCard 재사용) */}
          <div className="mb-8">
            <NScentCard card={card} userName={userName} />
          </div>

          {/* 액션 버튼 영역 */}
          <div className="space-y-3">
            {isLoggedIn ? (
              <button
                onClick={onSave}
                className="w-full py-4 rounded-2xl bg-[#C8A24D] text-white font-bold shadow-lg hover:bg-[#B69140] transition-all hover:scale-[1.02] active:scale-[0.98]"
              >
                나의 보관함에 저장하기
              </button>
            ) : (
              <div className="p-4 rounded-2xl bg-[#F8F4EC] border border-[#E6DDCF] text-center">
                <p className="text-xs text-[#7A6B57] mb-3">로그인하시면 생성된 카드를 저장하고 관리할 수 있습니다.</p>
                <button
                  onClick={() => window.location.href = '/login'}
                  className="text-sm font-bold text-[#C8A24D] hover:underline"
                >
                  로그인하고 저장하기
                </button>
              </div>
            )}
            
            <button
              onClick={onContinueExplore || onClose}
              className="w-full py-4 rounded-2xl border border-[#E2D7C5] bg-white text-[#5C5448] font-bold hover:bg-[#F8F4EC] transition-all"
            >
              계속 탐색하기
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ScentCardModal;
