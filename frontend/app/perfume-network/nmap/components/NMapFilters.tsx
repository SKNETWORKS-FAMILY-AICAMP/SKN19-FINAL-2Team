import React, { useState } from "react";
import { FilterOptions, LabelsData } from "../types";
import { Sparkles } from "lucide-react";
import { ACCORD_ICONS, ACCORD_LABELS, BRAND_LABELS, SEASON_LABELS, OCCASION_LABELS, GENDER_TARGET_LABELS } from "../../config";

interface Props {
  filterOptions: FilterOptions;
  labelsData: LabelsData | null;
  selectedAccords: string[];
  setSelectedAccords: (acc: string[]) => void;
  selectedBrands: string[];
  setSelectedBrands: (brands: string[] | ((prev: string[]) => string[])) => void;
  selectedSeasons: string[];
  setSelectedSeasons: (seasons: string[] | ((prev: string[]) => string[])) => void;
  selectedOccasions: string[];
  setSelectedOccasions: (occasions: string[] | ((prev: string[]) => string[])) => void;
  selectedGenders: string[];
  setSelectedGenders: (genders: string[] | ((prev: string[]) => string[])) => void;
  setSelectedPerfumeId: (id: string | null) => void;
  logActivity: (data: { accord_selected?: string; filter_changed?: string; selected_accords_override?: string[] }) => void;
  showMyPerfumesOnly: boolean;
  myPerfumeFilters: FilterOptions | null;
}

export default function NMapFilters({
  filterOptions,
  labelsData,
  selectedAccords,
  setSelectedAccords,
  selectedBrands,
  setSelectedBrands,
  selectedSeasons,
  setSelectedSeasons,
  selectedOccasions,
  setSelectedOccasions,
  selectedGenders,
  setSelectedGenders,
  setSelectedPerfumeId,
  logActivity,
  showMyPerfumesOnly,
  myPerfumeFilters,
}: Props) {
  const [isAccordFilterOpen, setIsAccordFilterOpen] = useState(true);
  const [isDetailFilterOpen, setIsDetailFilterOpen] = useState(false);
  const [brandPage, setBrandPage] = useState(1);
  const BRANDS_PER_PAGE = 20;

  const effectiveFilterOptions = showMyPerfumesOnly ? (myPerfumeFilters ?? { accords: [], brands: [], seasons: [], occasions: [], genders: [] }) : filterOptions;

  const fmtAccord = (v: string) => {
    const trimmed = v.trim();
    if (trimmed === "Fougère" || trimmed === "Foug\\u00e8re" || trimmed.includes("Foug")) return "푸제르";
    return labelsData?.accords[trimmed] || ACCORD_LABELS[trimmed] || v;
  };
  const fmtBrand = (v: string) => labelsData?.brands[v.trim()] || BRAND_LABELS[v.trim()] || v;
  const fmtSeason = (v: string) => labelsData?.seasons[v.trim()] || SEASON_LABELS[v.trim()] || v;
  const fmtOccasion = (v: string) => labelsData?.occasions[v.trim()] || OCCASION_LABELS[v.trim()] || v;
  const fmtGender = (v: string) => labelsData?.genders[v.trim()] || GENDER_TARGET_LABELS[v.trim()] || v;

  const formatLabelWithEnglishPair = (value: string, formatter: (v: string) => string) => {
    const korean = formatter(value);
    return korean === value ? value : `${korean} (${value})`;
  };

  const totalPages = Math.ceil(effectiveFilterOptions.brands.length / BRANDS_PER_PAGE) || 1;
  const safeBrandPage = Math.min(brandPage, totalPages);
  const visibleBrands = effectiveFilterOptions.brands.slice((safeBrandPage - 1) * BRANDS_PER_PAGE, safeBrandPage * BRANDS_PER_PAGE);

  return (
    <>
      {/* 1단계: 분위기 필터 */}
      <section className="space-y-4">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-[15px] sm:text-lg font-semibold">어떤 분위기를 원하세요?</h2>
            <p className="text-xs text-[#7A6B57]">관심 있는 분위기를 선택해 원하는 향수를 찾아보세요.</p>
          </div>
          <button
            onClick={() => setIsAccordFilterOpen(!isAccordFilterOpen)}
            className="h-8 px-3 rounded-full border border-[#E2D7C5] bg-white text-[11px] font-semibold whitespace-nowrap sm:h-9 sm:px-4 sm:text-xs"
          >
            {isAccordFilterOpen ? "▲ 접기" : "▼ 펼치기"}
          </button>
        </div>
        {isAccordFilterOpen && (
          <div className="grid grid-cols-4 sm:grid-cols-5 md:grid-cols-7 lg:grid-cols-10 gap-3">
            {effectiveFilterOptions.accords.map(acc => {
              const Icon = ACCORD_ICONS[acc] ?? Sparkles;
              return (
                <button key={acc} onClick={() => {
                  const isAdding = !selectedAccords.includes(acc);
                  const newAccords = isAdding ? [...selectedAccords, acc] : selectedAccords.filter(a => a !== acc);
                  setSelectedAccords(newAccords);
                  setSelectedPerfumeId(null);
                  // 어코드 추가/제거 시 즉시 DB 업데이트 (업데이트된 배열 직접 전달)
                  logActivity({
                    accord_selected: isAdding ? acc : undefined,
                    selected_accords_override: newAccords
                  });
                }}
                  className={`relative aspect-square rounded-2xl border-2 transition-all ${selectedAccords.includes(acc) ? "border-[#C8A24D] bg-[#C8A24D]/10" : "border-[#E2D7C5] bg-white"}`}>
                  <div className="absolute inset-0 flex flex-col items-center justify-center p-1 sm:p-2">
                    <Icon className="w-7 h-7 sm:w-8 sm:h-8 md:w-9 md:h-9 text-[#7A6B57] mb-1 sm:mb-2" strokeWidth={1.75} />
                    <span className="text-[10px] sm:text-xs md:text-sm font-semibold text-center leading-tight">{fmtAccord(acc)}</span>
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </section>

      {/* 2단계: 세부 필터 */}
      <section className="space-y-4">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-[15px] sm:text-lg font-semibold">더 꼼꼼하게 찾아보고 싶다면</h2>
            <p className="text-xs text-[#7A6B57]">브랜드와 계절, 특별한 순간을 더해 나만의 취향을 더 선명하게 찾아보세요.</p>
          </div>
          <button
            onClick={() => setIsDetailFilterOpen(!isDetailFilterOpen)}
            className="h-8 px-3 rounded-full border border-[#E2D7C5] bg-white text-[11px] font-semibold whitespace-nowrap sm:h-9 sm:px-4 sm:text-xs"
          >
            {isDetailFilterOpen ? "▲ 접기" : "▼ 펼치기"}
          </button>
        </div>
        {isDetailFilterOpen && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { label: "브랜드", options: visibleBrands, selected: selectedBrands, setter: setSelectedBrands, formatter: fmtBrand, isBrand: true },
              { label: "계절감", options: effectiveFilterOptions.seasons, selected: selectedSeasons, setter: setSelectedSeasons, formatter: fmtSeason },
              { label: "어울리는 상황", options: effectiveFilterOptions.occasions, selected: selectedOccasions, setter: setSelectedOccasions, formatter: fmtOccasion },
              { label: "어울리는 성별", options: effectiveFilterOptions.genders, selected: selectedGenders, setter: setSelectedGenders, formatter: fmtGender }
            ].map((group, i) => (
              <div key={i} className="flex flex-col gap-2">
                <div className="flex justify-between items-center">
                  <label className="text-xs font-semibold text-[#4D463A]">{group.label}</label>
                  <button onClick={() => { group.setter([]); setSelectedPerfumeId(null); }} className="text-[10px] text-[#7A6B57]">초기화</button>
                </div>
                <div className="h-48 flex flex-col rounded-xl border border-[#E1D7C8] bg-white p-2">
                  <div className="flex-1 overflow-y-auto">
                    {group.options.map(opt => (
                      <label key={opt} className="flex items-center gap-2 px-2 py-1.5 hover:bg-[#F5F2EA] text-sm cursor-pointer">
                        <input type="checkbox" checked={group.selected.includes(opt)} onChange={() => {
                          group.setter((prev: string[]) => prev.includes(opt) ? prev.filter(v => v !== opt) : [...prev, opt]);
                          setSelectedPerfumeId(null);
                          logActivity({ filter_changed: group.label });
                        }} className="accent-[#C8A24D]" />
                        <span className="text-xs">{formatLabelWithEnglishPair(opt, group.formatter)}</span>
                      </label>
                    ))}
                  </div>
                  {group.isBrand && totalPages > 1 && (
                    <div className="flex justify-between items-center px-2 pt-2 border-t border-[#F5F2EA]">
                      <button onClick={() => setBrandPage(p => Math.max(1, p - 1))} disabled={safeBrandPage === 1} className="text-[10px] disabled:opacity-30">이전</button>
                      <span className="text-[10px]">{safeBrandPage}/{totalPages}</span>
                      <button onClick={() => setBrandPage(p => Math.min(totalPages, p + 1))} disabled={safeBrandPage === totalPages} className="text-[10px] disabled:opacity-30">다음</button>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </>
  );
}
