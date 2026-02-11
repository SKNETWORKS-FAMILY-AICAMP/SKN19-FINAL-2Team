import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { NMapAnalysisSummary } from '../types';
import ScentCardModal from '@/app/perfume-network/ncard/ScentCardModal';
import LoadingOverlay from '@/app/perfume-network/shared/LoadingOverlay';
import { ncardService, ScentCard } from '@/app/perfume-network/ncard/ncard-service';

interface ActionButtonsProps {
  summary: NMapAnalysisSummary;
  isLoggedIn: boolean;
}

/**
 * 향수 맵(NMap) 하단 액션 버튼 컴포넌트
 * 향기 카드 생성 및 결과 공유 기능을 담당합니다.
 */
const ActionButtons = ({ summary, isLoggedIn }: ActionButtonsProps) => {
  const router = useRouter();
  const [isGenerating, setIsGenerating] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [generatedCard, setGeneratedCard] = useState<ScentCard | null>(null);
  const [error, setError] = useState<string | null>(null);

  // 향기 카드 생성 핸들러
  const handleGenerateCard = async () => {
    try {
      setIsGenerating(true);
      setError(null);
      
      // nmap의 summary 데이터를 ncard 형식으로 변환하여 저장
      const card = await ncardService.generateAndSaveCard({
        top_notes: summary.top_notes,
        middle_notes: summary.middle_notes,
        base_notes: summary.base_notes,
        mood_keywords: summary.mood_keywords,
        analysis_text: summary.analysis_text,
        representative_color: summary.representative_color
      });

      setGeneratedCard(card);
      setShowModal(true);
    } catch (err) {
      console.error('Failed to generate card:', err);
      setError('향기 카드 생성에 실패했습니다. 잠시 후 다시 시도해주세요.');
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="bg-white rounded-2xl p-6 border border-[#E6DDCF] shadow-sm space-y-4">
        <div className="space-y-1">
          <h3 className="text-sm font-bold text-[#4D463A]">분석 결과를 간직해보세요</h3>
          <p className="text-[11px] text-[#7A6B57] leading-relaxed">
            탐색한 향기 데이터를 바탕으로 나만의 특별한 향기 카드를 만들 수 있습니다.
          </p>
        </div>

        <button
          onClick={handleGenerateCard}
          disabled={isGenerating}
          className={`w-full py-4 rounded-xl font-bold text-white transition-all shadow-lg flex items-center justify-center gap-2 ${
            isGenerating 
              ? 'bg-[#A89486] cursor-not-allowed' 
              : 'bg-gradient-to-br from-[#6B4E71] via-[#8B6E8F] to-[#9B7EAC] hover:scale-[1.02] active:scale-[0.98]'
          }`}
        >
          {isGenerating ? (
            <>
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              카드 생성 중...
            </>
          ) : (
            <>
              <span className="text-xl">🫧</span>
              향기 카드 만들기
            </>
          )}
        </button>

        {!isLoggedIn && (
          <p className="text-[10px] text-center text-[#9C8D7A]">
            로그인하면 생성된 카드를 프로필에 저장할 수 있습니다.
          </p>
        )}
      </div>

      <div className="flex gap-3">
        <button 
          onClick={() => window.print()}
          className="flex-1 py-3 rounded-xl border border-[#E2D7C5] bg-white text-xs font-semibold text-[#5C5448] hover:bg-[#F8F4EC] transition-colors"
        >
          결과 인쇄하기
        </button>
        <button 
          onClick={() => router.push('/')}
          className="flex-1 py-3 rounded-xl border border-[#E2D7C5] bg-white text-xs font-semibold text-[#5C5448] hover:bg-[#F8F4EC] transition-colors"
        >
          다시 분석하기
        </button>
      </div>

      {/* 로딩 오버레이 */}
      {isGenerating && <LoadingOverlay />}

      {/* 향기 카드 결과 모달 */}
      {showModal && generatedCard && (
        <ScentCardModal
          card={generatedCard}
          onClose={() => setShowModal(false)}
          onSave={() => {
            alert("카드가 저장되었습니다!");
            setShowModal(false);
          }}
          onContinueExplore={() => setShowModal(false)}
          isLoggedIn={isLoggedIn}
        />
      )}
      
      {/* 에러 메시지 표시 */}
      {error && (
        <div className="fixed bottom-24 left-1/2 transform -translate-x-1/2 z-50 bg-red-50 border border-red-200 text-red-600 px-6 py-3 rounded-xl shadow-lg animate-fade-in">
          {error}
        </div>
      )}
    </div>
  );
};

export default ActionButtons;
