"use client";

import React from "react";
import { useSession } from "next-auth/react";
import { usePerfumeNetwork } from "./use-perfume-network";
import NMapHeader from "./components/NMapHeader";
import NMapFilters from "./components/NMapFilters";
import NMapGraphSection from "./components/NMapGraphSection";
import NMapDetailPanel from "./components/NMapDetailPanel";
import CardTriggerBanner from "@/app/perfume-network/shared/CardTriggerBanner";
import LoadingOverlay from "@/app/perfume-network/shared/LoadingOverlay";
import ScentCardModal from "@/app/perfume-network/ncard/ScentCardModal";
import { NScentCard } from "@/app/perfume-network/ncard/NScentCard";

export default function NMapView({ sessionUserId }: { sessionUserId?: string | number }) {
  const { data: session } = useSession();
  const {
    fullPayload,
    labelsData,
    filterOptions,
    status,
    minSimilarity, setMinSimilarity,
    topAccords, setTopAccords,
    selectedAccords, setSelectedAccords,
    selectedBrands, setSelectedBrands,
    selectedSeasons, setSelectedSeasons,
    selectedOccasions, setSelectedOccasions,
    selectedGenders, setSelectedGenders,
    selectedPerfumeId, setSelectedPerfumeId,
    memberId,
    displayLimit, setDisplayLimit,
    showMyPerfumesOnly, setShowMyPerfumesOnly,
    scentSessionId,
    showCardTrigger,
    handleDismissCardTrigger,
    triggerMessage,
    isGeneratingCard,
    showCardModal, setShowCardModal,
    generatedCard, setGeneratedCard,
    generatedCardId, setGeneratedCardId,
    cardTriggerReady,
    error, setError,
    logActivity,
    handleGenerateCard,
    handleSaveCard,
    isSavingCard,
    saveSuccess,
    setSaveSuccess,
    myPerfumeIds,
    myPerfumeFilters,
    interactionCount,
  } = usePerfumeNetwork(sessionUserId);

  const [showLoginPrompt, setShowLoginPrompt] = React.useState(false);
  const [isKorean, setIsKorean] = React.useState(true);
  const [highlightedSimilarPerfumeId, setHighlightedSimilarPerfumeId] = React.useState<string | null>(null);
  const [profileNickname, setProfileNickname] = React.useState<string | null>(null);
  const [profileImageUrl, setProfileImageUrl] = React.useState<string | null>(null);
  const [mobileSheetOffsetY, setMobileSheetOffsetY] = React.useState(0);
  const [isDraggingSheet, setIsDraggingSheet] = React.useState(false);
  const sheetTouchStartYRef = React.useRef<number | null>(null);
  const sessionFallbackName = session?.user?.name || session?.user?.email?.split("@")[0] || null;
  const sessionFallbackImage = session?.user?.image || null;
  const normalizedSessionFallbackName = React.useMemo(() => {
    const name = sessionFallbackName?.trim();
    if (!name) return null;
    if (/^(member|user|guest)$/i.test(name)) return null;
    return name;
  }, [sessionFallbackName]);

  // 어코드 클릭 시 지도 필터 업데이트 핸들러
  const handleAccordClick = (accordName: string) => {
    let newAccords: string[];
    setSelectedAccords(prev => {
      if (prev.includes(accordName)) {
        newAccords = prev.filter(a => a !== accordName);
      } else {
        newAccords = [...prev, accordName];
      }
      return newAccords;
    });

    // 상태 업데이트 반영을 위해 약간의 지연 후 로깅하거나, 
    // 혹은 직접 계산된 값을 전달하여 정확한 데이터를 서버에 전송합니다.
    setTimeout(() => {
      logActivity({ accord_selected: accordName });
    }, 0);
  };

  const isLoading = status === "전체 데이터 로드 중..." || status === "대기 중";

  React.useEffect(() => {
    if (!selectedPerfumeId) {
      setMobileSheetOffsetY(0);
      setIsDraggingSheet(false);
      sheetTouchStartYRef.current = null;
    }
  }, [selectedPerfumeId]);

  React.useEffect(() => {
    setHighlightedSimilarPerfumeId(null);
  }, [selectedPerfumeId]);

  React.useEffect(() => {
    if (!memberId) {
      setProfileNickname(null);
      setProfileImageUrl(null);
      return;
    }

    let isCancelled = false;
    fetch(`/api/users/profile/${memberId}`, { cache: "no-store" })
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (isCancelled) return;
        setProfileNickname(data?.nickname || null);

        const rawUrl = data?.profile_image_url;
        if (!rawUrl) {
          setProfileImageUrl(null);
          return;
        }
        const finalUrl =
          rawUrl.startsWith("http") || rawUrl.startsWith("/uploads")
            ? rawUrl
            : `/api${rawUrl}`;
        setProfileImageUrl(finalUrl);
      })
      .catch(() => {
        if (isCancelled) return;
        setProfileImageUrl(null);
      });

    return () => {
      isCancelled = true;
    };
  }, [memberId]);

  const handleSheetTouchStart = (e: React.TouchEvent<HTMLDivElement>) => {
    sheetTouchStartYRef.current = e.touches[0]?.clientY ?? null;
    setIsDraggingSheet(true);
  };

  const handleSheetTouchMove = (e: React.TouchEvent<HTMLDivElement>) => {
    if (sheetTouchStartYRef.current === null) return;
    const deltaY = e.touches[0].clientY - sheetTouchStartYRef.current;
    setMobileSheetOffsetY(Math.max(0, deltaY));
  };

  const handleSheetTouchEnd = () => {
    if (sheetTouchStartYRef.current === null) return;
    const shouldClose = mobileSheetOffsetY > 90;
    sheetTouchStartYRef.current = null;
    setIsDraggingSheet(false);
    setMobileSheetOffsetY(0);
    if (shouldClose) setSelectedPerfumeId(null);
  };

  return (
    <div className="min-h-screen bg-[#FDFBF8] text-black relative overflow-x-hidden">
      <div className={`max-w-7xl mx-auto px-3 sm:px-6 pt-0 sm:pt-12 pb-10 sm:pb-12 space-y-2 sm:space-y-12 transition-all duration-500 ${showCardModal && generatedCard ? 'mr-[440px]' : ''}`}>
        <NMapHeader />

        {isLoading ? (
          // 필터 영역 스켈레톤 로딩
          <div className="space-y-6">
            <div className="space-y-3">
              <div className="h-5 w-48 bg-[#E6DDCF] rounded animate-pulse"></div>
              <div className="flex flex-wrap gap-2">
                {[...Array(8)].map((_, i) => (
                  <div key={i} className="h-10 w-24 bg-[#E6DDCF] rounded-full animate-pulse"></div>
                ))}
              </div>
            </div>
            <div className="space-y-3">
              <div className="h-5 w-32 bg-[#E6DDCF] rounded animate-pulse"></div>
              <div className="flex flex-wrap gap-2">
                {[...Array(6)].map((_, i) => (
                  <div key={i} className="h-10 w-28 bg-[#E6DDCF] rounded-full animate-pulse"></div>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <NMapFilters
            filterOptions={filterOptions}
            labelsData={labelsData}
            selectedAccords={selectedAccords}
            setSelectedAccords={setSelectedAccords}
            selectedBrands={selectedBrands}
            setSelectedBrands={setSelectedBrands}
            selectedSeasons={selectedSeasons}
            setSelectedSeasons={setSelectedSeasons}
            selectedOccasions={selectedOccasions}
            setSelectedOccasions={setSelectedOccasions}
            selectedGenders={selectedGenders}
            setSelectedGenders={setSelectedGenders}
            setSelectedPerfumeId={setSelectedPerfumeId}
            logActivity={logActivity}
            showMyPerfumesOnly={showMyPerfumesOnly}
            myPerfumeFilters={myPerfumeFilters}
          />
        )}

        <div className="border-t-2 border-[#E6DDCF]"></div>

        <section className="space-y-4">
          <div>
            <h2 className="text-lg font-semibold">향수 지도</h2>
            <p className="text-xs text-[#7A6B57]">궁금한 향수를 클릭하면, 유사한 향수가 나타나요.</p>
          </div>

          {isLoading ? (
            // 지도 영역 로딩 UI
            <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_380px]">
              <div className="bg-white rounded-3xl shadow-lg border border-[#E6DDCF] p-8 flex flex-col items-center justify-center min-h-[600px]">
                <div className="relative w-24 h-24 mb-6">
                  <div className="absolute inset-0 border-4 border-[#E6DDCF] rounded-full"></div>
                  <div className="absolute inset-0 border-4 border-[#C8A24D] border-t-transparent rounded-full animate-spin"></div>
                </div>
                <h3 className="text-xl font-bold text-[#2E2B28] mb-2">향수 정보를 불러오는 중...</h3>
                <p className="text-sm text-[#7A6B57] text-center max-w-md">
                  수천 개의 향수 데이터를 분석하고 있어요.<br />
                  잠시만 기다려주세요! 🌸
                </p>
                <div className="mt-8 flex gap-2">
                  <div className="w-2 h-2 bg-[#C8A24D] rounded-full animate-bounce" style={{ animationDelay: '0s' }}></div>
                  <div className="w-2 h-2 bg-[#C8A24D] rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                  <div className="w-2 h-2 bg-[#C8A24D] rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
                </div>
              </div>
              <div className="bg-white rounded-3xl shadow-lg border border-[#E6DDCF] p-6 min-h-[600px]">
                <div className="space-y-4 animate-pulse">
                  <div className="h-6 w-3/4 bg-[#E6DDCF] rounded"></div>
                  <div className="h-4 w-full bg-[#E6DDCF] rounded"></div>
                  <div className="h-4 w-5/6 bg-[#E6DDCF] rounded"></div>
                  <div className="h-48 w-full bg-[#E6DDCF] rounded-xl mt-6"></div>
                  <div className="space-y-2 mt-6">
                    <div className="h-4 w-full bg-[#E6DDCF] rounded"></div>
                    <div className="h-4 w-4/5 bg-[#E6DDCF] rounded"></div>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_380px]">
              <NMapGraphSection
                fullPayload={fullPayload}
                labelsData={labelsData}
                isKorean={isKorean}
                setIsKorean={setIsKorean}
                selectedPerfumeId={selectedPerfumeId}
                setSelectedPerfumeId={setSelectedPerfumeId}
                highlightedSimilarPerfumeId={highlightedSimilarPerfumeId}
                displayLimit={displayLimit}
                setDisplayLimit={setDisplayLimit}
                minSimilarity={minSimilarity}
                setMinSimilarity={setMinSimilarity}
                topAccords={topAccords}
                selectedAccords={selectedAccords}
                selectedBrands={selectedBrands}
                selectedSeasons={selectedSeasons}
                selectedOccasions={selectedOccasions}
                selectedGenders={selectedGenders}
                showMyPerfumesOnly={showMyPerfumesOnly}
                myPerfumeIds={myPerfumeIds}
                logActivity={logActivity}
                memberId={memberId}
                setShowLoginPrompt={setShowLoginPrompt}
                setShowMyPerfumesOnly={setShowMyPerfumesOnly}
              />
              <div className="hidden lg:block self-stretch">
                <NMapDetailPanel
                  selectedPerfumeId={selectedPerfumeId}
                  highlightedSimilarPerfumeId={highlightedSimilarPerfumeId}
                  setHighlightedSimilarPerfumeId={setHighlightedSimilarPerfumeId}
                  fullPayload={fullPayload}
                  labelsData={labelsData}
                  isKorean={isKorean}
                  selectedAccords={selectedAccords}
                  logActivity={logActivity}
                />
              </div>
            </div>
          )}
        </section>
      </div>

      {selectedPerfumeId && !isLoading && (
        <div
          className="lg:hidden fixed inset-0 z-[80] bg-black/35 backdrop-blur-[2px] flex items-end"
          onClick={() => setSelectedPerfumeId(null)}
        >
          <div
            className="w-full h-[88vh] bg-[#FDFBF8] rounded-t-[28px] border-t border-[#E2D7C5] shadow-2xl overflow-hidden"
            onClick={(e) => e.stopPropagation()}
            style={{
              transform: `translateY(${mobileSheetOffsetY}px)`,
              transition: isDraggingSheet ? "none" : "transform 220ms ease-out",
            }}
          >
            <div
              className="pt-2 pb-2 flex justify-center touch-none"
              onTouchStart={handleSheetTouchStart}
              onTouchMove={handleSheetTouchMove}
              onTouchEnd={handleSheetTouchEnd}
              onTouchCancel={handleSheetTouchEnd}
            >
              <div className="h-1.5 w-14 rounded-full bg-[#D9CFBE]" />
            </div>
            <NMapDetailPanel
              selectedPerfumeId={selectedPerfumeId}
              highlightedSimilarPerfumeId={highlightedSimilarPerfumeId}
              setHighlightedSimilarPerfumeId={setHighlightedSimilarPerfumeId}
              fullPayload={fullPayload}
              labelsData={labelsData}
              isKorean={isKorean}
              selectedAccords={selectedAccords}
              logActivity={logActivity}
              mode="modal"
            />
          </div>
        </div>
      )}

      {showLoginPrompt && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-6">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm p-6 text-center space-y-4">
            <div className="text-3xl">🔒</div>
            <h3 className="text-lg font-semibold text-[#2E2B28]">로그인이 필요해요</h3>
            <p className="text-xs text-[#7A6B57]">내 향수로 보기는 회원 전용 기능입니다. 로그인 후 더 편하게 이용할 수 있어요.</p>
            <div className="flex gap-2">
              <a href="/login" className="flex-1 h-9 rounded-full bg-[#C8A24D] text-white text-xs font-semibold flex items-center justify-center">로그인하러 가기</a>
              <button onClick={() => setShowLoginPrompt(false)} className="flex-1 h-9 rounded-full border border-[#E2D7C5] text-xs font-semibold">닫기</button>
            </div>
          </div>
        </div>
      )}

      {showCardTrigger && (
        <CardTriggerBanner
          message={triggerMessage}
          onAccept={handleGenerateCard}
          onDismiss={handleDismissCardTrigger}
        />
      )}

      {isGeneratingCard && <LoadingOverlay />}

      {error && (
        <div className="fixed bottom-24 left-1/2 transform -translate-x-1/2 z-50 max-w-md w-full mx-6 animate-fade-in">
          <div className="bg-white border-2 border-red-300 rounded-2xl shadow-2xl p-6">
            <div className="flex items-start gap-4">
              <div className="flex-shrink-0 w-12 h-12 rounded-full bg-red-100 flex items-center justify-center"><span className="text-2xl">⚠️</span></div>
              <div className="flex-1">
                <h3 className="text-base font-bold text-red-700 mb-1">오류가 발생했습니다</h3>
                <p className="text-sm text-red-600 leading-relaxed">{error}</p>
              </div>
              <button onClick={() => setError(null)} className="flex-shrink-0 w-8 h-8 rounded-full hover:bg-red-100 flex items-center justify-center transition-colors"><span className="text-xl">×</span></button>
            </div>
            <div className="mt-4 flex gap-2">
              <button onClick={handleGenerateCard} className="flex-1 py-2.5 bg-gradient-to-r from-red-500 to-red-600 text-white rounded-xl font-semibold">다시 시도하기</button>
              <button onClick={() => setError(null)} className="px-6 py-2.5 border-2 border-red-200 text-red-600 rounded-xl font-semibold">닫기</button>
            </div>
          </div>
        </div>
      )}

      {/* 고정 버튼 (하단 우측) */}
      <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end gap-3">
        {/* 클릭 카운트 표시 (개발 확인용) */}
        <div className="bg-white/80 backdrop-blur-md border border-[#E2D7C5] px-3 py-1.5 rounded-full text-[10px] font-bold text-[#7A6B57] shadow-sm animate-fade-in">
          탐색 활동: <span className="text-[#C8A24D]">{interactionCount}</span>
        </div>

        <button
          onClick={() => cardTriggerReady ? handleGenerateCard() : alert("아직 정보가 충분하지 않아요. 관심있는 향이나 필터를 더 클릭해보세요!")}
          className={`relative w-16 h-16 rounded-full shadow-2xl flex items-center justify-center text-3xl transition-all duration-300 group ${cardTriggerReady ? "bg-gradient-to-br from-[#6B4E71] via-[#8B6E8F] to-[#9B7EAC] animate-pulse-glow hover:scale-110" : "bg-gradient-to-br from-[#6B4E71] to-[#8B6E8F] hover:scale-105"}`}
          title={generatedCard ? (cardTriggerReady ? "새로운 정보를 토대로 향 MBTI 다시 만들기" : "더 탐색하면 다시 만들 수 있어요") : (cardTriggerReady ? "나의 향 MBTI 확인하기 (준비 완료!)" : "더 많은 향기를 탐색해보세요")}
        >
          {cardTriggerReady && <div className="absolute inset-0 rounded-full bg-gradient-to-r from-transparent via-white to-transparent opacity-30 animate-shimmer"></div>}
          <span className={`relative z-10 transition-transform duration-300 ${cardTriggerReady ? "group-hover:rotate-12" : "group-hover:scale-110"}`}>
            {generatedCard ? "🔄" : "🫧"}
          </span>
          {cardTriggerReady && <span className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 rounded-full flex items-center justify-center text-white text-xs font-bold animate-bounce">!</span>}
        </button>
        {cardTriggerReady && (
          <div className="absolute bottom-full right-0 mb-3 bg-[#2E2B28] text-white px-4 py-2 rounded-lg text-xs font-medium whitespace-nowrap shadow-lg">
            {generatedCard ? "새로운 분석 결과가 준비되었어요! 🎉" : "나의 향 MBTI 확인 준비 완료! 🎉"}
          </div>
        )}
      </div>

      {/* 향기 분석 사이드 패널 (기존 모달 대체) */}
      {showCardModal && generatedCard && (
        <NScentCard
          card={generatedCard}
          userName={profileNickname || normalizedSessionFallbackName || (memberId ? "회원" : "Guest")}
          userImageUrl={profileImageUrl || sessionFallbackImage}
          onClose={() => { setShowCardModal(false); setGeneratedCard(null); setGeneratedCardId(null); }}
          onAccordClick={handleAccordClick}
          onSave={memberId ? handleSaveCard : undefined}
          isSaving={isSavingCard}
        />
      )}

      {/* 카드 저장 성공 메시지 */}
      {saveSuccess && (
        <div className="fixed bottom-24 left-1/2 transform -translate-x-1/2 z-50 max-w-md w-full mx-6 animate-fade-in">
          <div className="bg-white border-2 border-green-300 rounded-2xl shadow-2xl p-6">
            <div className="flex items-start gap-4">
              <div className="flex-shrink-0 w-12 h-12 rounded-full bg-green-100 flex items-center justify-center">
                <span className="text-2xl">✅</span>
              </div>
              <div className="flex-1">
                <h3 className="text-base font-bold text-green-700 mb-1">카드 저장 완료!</h3>
                <p className="text-sm text-green-600 leading-relaxed">나의 보관함에 성공적으로 저장되었습니다. 새로운 세션이 시작되었어요!</p>
              </div>
              <button
                onClick={() => setSaveSuccess(false)}
                className="flex-shrink-0 w-8 h-8 rounded-full hover:bg-green-100 flex items-center justify-center transition-colors"
              >
                <span className="text-xl">×</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
