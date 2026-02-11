import React, { useMemo, useState } from "react";
import { NetworkPayload, NetworkNode, LabelsData } from "../types";
import { BRAND_LABELS, ACCORD_LABELS } from "../../config";

interface Props {
  selectedPerfumeId: string | null;
  highlightedSimilarPerfumeId: string | null;
  setHighlightedSimilarPerfumeId: (id: string | null) => void;
  fullPayload: NetworkPayload | null;
  labelsData: LabelsData | null;
  isKorean: boolean;
  selectedAccords: string[];
  logActivity: (data: {
    accord_selected?: string;
    perfume_id?: number;
    filter_changed?: string;
    selected_accords_override?: string[];
  }) => void;
  mode?: "panel" | "modal";
}

export default function NMapDetailPanel({
  selectedPerfumeId,
  highlightedSimilarPerfumeId,
  setHighlightedSimilarPerfumeId,
  fullPayload,
  labelsData,
  isKorean,
  selectedAccords,
  logActivity,
  mode = "panel",
}: Props) {
  const isModal = mode === "modal";
  const [expandedSummaryId, setExpandedSummaryId] = useState<string | null>(null);
  const isSummaryExpanded = expandedSummaryId === selectedPerfumeId;

  const fmtAccord = (v: string) => {
    if (!isKorean) return v;
    const trimmed = v.trim();
    if (trimmed === "Fougère" || trimmed === "Foug\\u00e8re" || trimmed.includes("Foug")) return "푸제르";
    return labelsData?.accords[trimmed] || ACCORD_LABELS[trimmed] || v;
  };
  const fmtBrand = (v: string) => {
    if (!isKorean) return v;
    return labelsData?.brands[v.trim()] || BRAND_LABELS[v.trim()] || v;
  };
  const fmtPerfumeName = (node: NetworkNode) =>
    isKorean ? (labelsData?.perfume_names?.[node.id] || node.label) : node.label;
  
  const getStatusBadge = (status?: string | null) => {
    if (!status) return null;
    const normalized = status.trim().toUpperCase();
    const map: Record<string, { label: string; className: string }> = {
      HAVE: { label: isKorean ? "보유" : "Have", className: "bg-[#E8F0FF] text-[#3B5CC9]" },
      WANT: { label: isKorean ? "위시" : "Wish", className: "bg-[#FFE8EE] text-[#C24B6B]" },
      HAD: { label: isKorean ? "과거" : "Past", className: "bg-[#F2F2F2] text-[#7A6B57]" },
      RECOMMENDED: { label: isKorean ? "추천" : "Recommended", className: "bg-[#E8F6EC] text-[#2F7D4C]" },
    };
    const matched = map[normalized];
    return matched || { label: normalized, className: "bg-[#F8F4EC] text-[#8A7C68]" };
  };

  const selectedPerfumeInfo = useMemo(() => {
    if (!fullPayload || !selectedPerfumeId) return null;
    const p = fullPayload.nodes.find(n => n.id === selectedPerfumeId) as NetworkNode | undefined;
    if (!p) return null;

    const weights = new Map<string, number>();
    fullPayload.edges.forEach(e => {
      if (e.type === "HAS_ACCORD" && e.from === selectedPerfumeId) {
        weights.set(e.to.replace("accord_", ""), e.weight ?? 0);
      }
    });

    const accordEntries = Array.from(weights.entries()).sort((a,b) => b[1]-a[1]);
    const accordList = accordEntries.slice(0, 5).map(([acc]) => acc);
    
    const scoreMap = new Map<string, number>();
    fullPayload.edges.forEach(e => {
      if (e.type === "SIMILAR_TO") {
        if (e.from === selectedPerfumeId) scoreMap.set(e.to, e.weight ?? 0);
        else if (e.to === selectedPerfumeId) scoreMap.set(e.from, e.weight ?? 0);
      }
    });

    const similar = Array.from(scoreMap.entries())
      .map(([id, score]) => {
        const simP = fullPayload.nodes.find(n => n.id === id) as NetworkNode | undefined;
        if (!simP) return null;
        const common = (p.accords || []).filter(a => (simP.accords || []).includes(a));
        const added = (simP.accords || []).filter(a => !(p.accords || []).includes(a));
        return { perfume: simP, score, commonAccords: common, newAccords: added };
      })
      .filter((x): x is NonNullable<typeof x> => x !== null)
      .sort((a, b) => b.score - a.score)
      .slice(0, 5);

    return { perfume: p, accordList, similar };
  }, [fullPayload, selectedPerfumeId]);

  if (!selectedPerfumeInfo) {
    return (
      <div className={`${isModal ? "h-full bg-[#FDFBF8] p-6" : "h-full rounded-3xl bg-white/80 border border-[#E2D7C5] p-5"} flex flex-col items-center justify-center text-center ${isModal ? "py-12 space-y-4" : "space-y-3"}`}>
        <div className={`${isModal ? "w-16 h-16 text-3xl" : "w-14 h-14 text-2xl"} rounded-full bg-[#F8F4EC] flex items-center justify-center`}>✨</div>
        <h3 className={`${isModal ? "text-lg" : "text-base"} font-semibold mb-1 text-[#C8A24D]`}>{isKorean ? "궁금한 향수를 클릭해보세요" : "Tap a perfume to explore details"}</h3>
      </div>
    );
  }

  const { perfume, accordList, similar } = selectedPerfumeInfo;
  const visibleSimilar = similar.slice(0, 3);
  const selectedPerfumeName = fmtPerfumeName(perfume);
  const accordText = accordList.map((acc, idx) => idx === 0 ? `${fmtAccord(acc)}${isKorean ? "(대표)" : " (main)"}` : fmtAccord(acc)).join(", ");
  const statusBadge = getStatusBadge(perfume.register_status);
  const matchedAccords = selectedAccords.filter(acc => accordList.map(a => a.toLowerCase()).includes(acc.toLowerCase()));
  const unmatchedAccords = accordList.filter(acc => !matchedAccords.some(m => m.toLowerCase() === acc.toLowerCase()));
  const summaryText = matchedAccords.length > 0
    ? (isKorean
      ? `이 향수는 선택하신 ${matchedAccords.map(fmtAccord).join(", ")}가 포함되어 있고${unmatchedAccords.length > 0 ? ` ${unmatchedAccords.slice(0, 3).map(fmtAccord).join(", ")}도 포함되어 있어요.` : ""}`
      : `This perfume includes ${matchedAccords.map(fmtAccord).join(", ")}${unmatchedAccords.length > 0 ? ` and also features ${unmatchedAccords.slice(0, 3).map(fmtAccord).join(", ")}` : ""}.`)
    : (isKorean
      ? `이 향수는 ${accordText} 로 구성되어 있어요.`
      : `This perfume is built around ${accordText}.`);
  const isLongSummary = summaryText.length > 120;
  const summaryPreview = isLongSummary ? `${summaryText.slice(0, 120).trimEnd()}...` : summaryText;
  const sectionTitleClass = isModal
    ? "text-sm font-semibold text-[#4D463A]"
    : "text-[18px] font-semibold leading-[1.2] text-[#4D463A]";
  const desktopSummaryClampStyle: React.CSSProperties | undefined = isModal
    ? undefined
    : {
        display: "-webkit-box",
        WebkitLineClamp: 4,
        WebkitBoxOrient: "vertical",
        overflow: "hidden",
      };
  const desktopCardDescClampStyle: React.CSSProperties | undefined = isModal
    ? undefined
    : {
        display: "-webkit-box",
        WebkitLineClamp: 3,
        WebkitBoxOrient: "vertical",
        overflow: "hidden",
      };

  return (
    <div className={`${isModal ? "h-full bg-[#FDFBF8] px-5 pt-1 pb-8 overflow-y-auto space-y-4" : "h-full rounded-3xl bg-white/80 border border-[#E2D7C5] p-6 overflow-hidden"} flex flex-col`}>
      <div className={`${isModal ? "space-y-5" : "h-full flex flex-col"}`}>
        <div className={`${isModal ? "" : "shrink-0"}`}>
          {!isModal && (
            <p className={`${sectionTitleClass} mb-2`}>
              {isKorean ? "선택 향수" : "Selected Perfume"}
            </p>
          )}
          {isModal ? (
            <div className="mb-4 flex items-center gap-3">
              <div className="w-16 h-16 rounded-2xl overflow-hidden border border-[#E2D7C5] bg-white flex-shrink-0">
                {perfume.image ? (
                  <img src={perfume.image} alt={selectedPerfumeName} className="w-full h-full object-cover" />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-2xl">✨</div>
                )}
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-lg font-bold text-[#C8A24D] leading-tight truncate">{selectedPerfumeName}</p>
                <div className="mt-1 flex items-center gap-2 min-w-0">
                  <p className="text-xs text-[#7A6B57] truncate">{fmtBrand(perfume.brand || "")}</p>
                  {statusBadge && <span className={`text-[10px] px-2 py-0.5 rounded-full font-semibold shrink-0 ${statusBadge.className}`}>{statusBadge.label}</span>}
                </div>
              </div>
            </div>
          ) : (
            <div className="mb-3 flex items-start gap-3">
              <div className="w-16 h-16 rounded-2xl overflow-hidden border border-[#E2D7C5] bg-white flex-shrink-0">
                {perfume.image ? (
                  <img src={perfume.image} alt={selectedPerfumeName} className="w-full h-full object-contain p-1.5" />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-xl">✨</div>
                )}
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-lg font-bold text-[#C8A24D] leading-tight break-words">{selectedPerfumeName}</p>
                <div className="mt-0.5 flex items-center gap-2 flex-wrap min-w-0">
                  <p className="text-[13px] text-[#7A6B57] break-words">{fmtBrand(perfume.brand || "")}</p>
                  {statusBadge && <span className={`text-[10px] px-2 py-0.5 rounded-full font-semibold shrink-0 ${statusBadge.className}`}>{statusBadge.label}</span>}
                </div>
                <p className="text-xs text-[#7A6B57] mt-0.5">{isKorean ? "향수를 선택하셨어요." : "selected."}</p>
              </div>
            </div>
          )}

          <div className={`${isModal ? "space-y-2 text-sm leading-relaxed" : "space-y-2 text-[14px] leading-[1.7]"} text-[#2E2B28]`}>
            {isModal ? (
              <>
                <p>{isSummaryExpanded ? summaryText : summaryPreview}</p>
                {isLongSummary && (
                  <button
                    type="button"
                    onClick={() => setExpandedSummaryId(prev => prev === selectedPerfumeId ? null : selectedPerfumeId)}
                    className="text-xs font-semibold text-[#7A6B57] underline underline-offset-4"
                  >
                    {isSummaryExpanded ? (isKorean ? "설명 접기" : "Show less") : (isKorean ? "설명 더보기" : "Read more")}
                  </button>
                )}
              </>
            ) : (
              <>
                {matchedAccords.length > 0 ? (
                  <p style={desktopSummaryClampStyle}>
                    {isKorean ? (
                      <>
                        이 향수는 선택하신 <span className="font-bold text-[#C8A24D]">{matchedAccords.map(fmtAccord).join(", ")}</span>가 포함되어 있고
                        {unmatchedAccords.length > 0 && <> <span className="font-semibold text-[#5C5448]">{unmatchedAccords.slice(0, 3).map(fmtAccord).join(", ")}</span>도 포함되어 있어요.</>}
                      </>
                    ) : (
                      <>
                        This perfume includes <span className="font-bold text-[#C8A24D]">{matchedAccords.map(fmtAccord).join(", ")}</span>
                        {unmatchedAccords.length > 0 && <> and also features <span className="font-semibold text-[#5C5448]">{unmatchedAccords.slice(0, 3).map(fmtAccord).join(", ")}</span>.</>}
                      </>
                    )}
                  </p>
                ) : (
                  <p style={desktopSummaryClampStyle}>{isKorean ? <>이 향수는 <span className="font-semibold text-[#5C5448]">{accordText}</span> 로 구성되어 있어요.</> : <>This perfume is built around <span className="font-semibold text-[#5C5448]">{accordText}</span>.</>}</p>
                )}
              </>
            )}
          </div>
        </div>
	
        <div className={`${isModal ? "border-t border-[#E6DDCF] pt-5 space-y-4" : "border-t border-[#E6DDCF] pt-4 mt-4 flex-1 min-h-0 flex flex-col"}`}>
          <p className={`${sectionTitleClass} ${isModal ? "" : "mb-2"}`}>{isKorean ? "유사한 향수 Top3" : "Top 3 Similar Perfumes"}</p>
          {visibleSimilar.length > 0 ? (
            <div className={`${isModal ? "space-y-3" : "flex-1 min-h-0 flex flex-col gap-3"}`}>
              {visibleSimilar.map(({ perfume, score, newAccords }) => {
                const similarPerfumeName = fmtPerfumeName(perfume);
                const similarStatusBadge = getStatusBadge(perfume.register_status);
                const isHighlightedSimilar = highlightedSimilarPerfumeId === perfume.id;
                const handleSelectSimilarPerfume = () => {
                  setHighlightedSimilarPerfumeId(perfume.id);
                  const perfumeIdNum = perfume.id.match(/\d+/)?.[0];
                  if (perfumeIdNum) logActivity({ perfume_id: Number(perfumeIdNum) });
                };
                const handleSimilarKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    handleSelectSimilarPerfume();
                  }
                };

                return (
                  <div
                    key={perfume.id}
                    className={`${isModal ? "p-4" : "p-4 flex-1 min-h-0 flex flex-col"} rounded-2xl border bg-white transition-all cursor-pointer group hover:shadow-md ${isHighlightedSimilar ? "border-[#2F7D4C] shadow-[0_0_0_1px_rgba(47,125,76,0.15)]" : "border-[#E6DDCF] hover:border-[#C8A24D]"}`}
                    onClick={handleSelectSimilarPerfume}
                    onKeyDown={handleSimilarKeyDown}
                    role="button"
                    tabIndex={0}
                    aria-pressed={isHighlightedSimilar}
                  >
                    {isModal ? (
                      <div className="flex justify-between items-start gap-3 mb-3">
                        <div className="flex items-start gap-3 min-w-0">
                          <div className="w-16 h-16 rounded-xl overflow-hidden border border-[#E2D7C5] bg-[#F8F4EC] flex-shrink-0">
                            {perfume.image ? (
                              <img src={perfume.image} alt={similarPerfumeName} className="w-full h-full object-contain p-1" />
                            ) : (
                              <div className="w-full h-full flex items-center justify-center text-xl">✨</div>
                            )}
                          </div>
                          <div className="space-y-1 min-w-0">
                            <span className="text-sm font-bold group-hover:text-[#C8A24D] transition-colors block truncate">{similarPerfumeName}</span>
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className="text-[10px] text-[#7A6B57]">{fmtBrand(perfume.brand || "")}</span>
                              {similarStatusBadge && <span className={`text-[10px] px-2 py-0.5 rounded-full font-semibold ${similarStatusBadge.className}`}>{similarStatusBadge.label}</span>}
                            </div>
                          </div>
                        </div>
                        <span className="text-[10px] font-bold text-[#C8A24D] bg-[#C8A24D]/10 px-2 py-1 rounded-md whitespace-nowrap ml-2">{isKorean ? "유사도" : "Similarity"} {Math.round(score * 100)}%</span>
                      </div>
                    ) : (
                      <div className="flex items-start gap-3 mb-3">
                        <div className="w-16 h-16 rounded-xl overflow-hidden border border-[#E2D7C5] bg-[#F8F4EC] flex-shrink-0">
                          {perfume.image ? (
                            <img src={perfume.image} alt={similarPerfumeName} className="w-full h-full object-contain p-1" />
                          ) : (
                            <div className="w-full h-full flex items-center justify-center text-xl">✨</div>
                          )}
                        </div>
                        <div className="space-y-1 min-w-0 flex-1">
                          <div className="flex items-start justify-between gap-2">
                            <span className="text-[18px] font-bold group-hover:text-[#C8A24D] transition-colors block leading-tight break-words pr-1">{similarPerfumeName}</span>
                            <span className="text-[10px] font-bold text-[#C8A24D] bg-[#C8A24D]/10 px-2 py-1 rounded-md whitespace-nowrap mt-0.5">{isKorean ? "유사도" : "Similarity"} {Math.round(score * 100)}%</span>
                          </div>
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-[12px] text-[#7A6B57]">{fmtBrand(perfume.brand || "")}</span>
                            {similarStatusBadge && <span className={`text-[10px] px-2 py-0.5 rounded-full font-semibold ${similarStatusBadge.className}`}>{similarStatusBadge.label}</span>}
                          </div>
                        </div>
                      </div>
                    )}
                    <p className={`${isModal ? "text-xs" : "text-[14px]"} text-[#2E2B28] leading-relaxed`} style={desktopCardDescClampStyle}>
                      <span className="font-bold text-[#C8A24D]">{similarPerfumeName}</span>{isKorean ? "은(는)" : ""} {(perfume.accords || []).slice(0, 4).map(fmtAccord).join(", ")}{isKorean ? " 로 구성되어있지만 " : " includes "}
                      {newAccords.length > 0 ? (
                        <>
                          <span className="font-semibold text-[#C8A24D]">{newAccords.slice(0, 2).map(fmtAccord).join(", ")}</span>
                          {isKorean ? " 새로운 분위기도 느낄 수 있는 향수에요." : " for a fresh mood."}
                        </>
                      ) : (
                        <>{isKorean ? "비슷한 분위기를 즐길 수 있는 향수에요." : " with a very similar mood."}</>
                      )}
                    </p>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="py-8 text-center bg-[#F8F4EC]/50 rounded-2xl border border-dashed border-[#E6DDCF]">
              <p className="text-xs text-[#7A6B57]">
                {isKorean ? <>비슷한 향수를 찾을 수 없어요.<br />닮은 정도를 조금 낮춰보세요.</> : <>No similar perfumes found.<br />Try lowering similarity.</>}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
