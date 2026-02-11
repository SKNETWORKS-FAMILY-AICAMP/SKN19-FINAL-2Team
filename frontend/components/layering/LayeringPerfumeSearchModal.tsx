"use client";

import { useEffect, useRef, useState, type ChangeEvent } from "react";

const API_URL = "/api";

type SearchResult = {
  perfume_id: number;
  name: string;
  name_kr?: string;
  brand: string;
  brand_kr?: string;
  image_url: string | null;
};

type AutocompleteResult = {
  brands: string[];
  keywords: string[];
};

type LayeringPerfumeSearchModalProps = {
  onSelect: (name: string) => void;
  compact?: boolean;
};

export default function LayeringPerfumeSearchModal({
  onSelect,
  compact = true,
}: LayeringPerfumeSearchModalProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [isKorean, setIsKorean] = useState(true);
  const [suggestions, setSuggestions] = useState<AutocompleteResult>({
    brands: [],
    keywords: [],
  });
  const [showSuggestions, setShowSuggestions] = useState(false);

  const searchTimeout = useRef<NodeJS.Timeout | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (!open) {
      setQuery("");
      setResults([]);
      setSuggestions({ brands: [], keywords: [] });
      setShowSuggestions(false);
      return;
    }

    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    setTimeout(() => inputRef.current?.focus(), 0);
  }, [open]);

  const executeSearch = async (searchTerm: string) => {
    if (!searchTerm.trim()) {
      setResults([]);
      return;
    }
    try {
      setLoading(true);
      setShowSuggestions(false);
      const res = await fetch(
        `${API_URL}/perfumes/search?q=${encodeURIComponent(searchTerm)}`,
      );
      if (res.ok) {
        const data = (await res.json()) as SearchResult[];
        setResults(data);
      }
    } catch (error) {
      console.error("Search failed:", error);
    } finally {
      setLoading(false);
    }
  };

  const fetchAutocomplete = async (input: string) => {
    if (!input.trim()) {
      setSuggestions({ brands: [], keywords: [] });
      return;
    }
    try {
      const res = await fetch(
        `${API_URL}/perfumes/autocomplete?q=${encodeURIComponent(input)}`,
      );
      if (res.ok) {
        const data = (await res.json()) as AutocompleteResult;
        setSuggestions(data);
        setShowSuggestions(true);
      }
    } catch (error) {
      console.error("Autocomplete failed:", error);
    }
  };

  const handleInputChange = (event: ChangeEvent<HTMLInputElement>) => {
    const value = event.target.value;
    setQuery(value);

    if (searchTimeout.current) {
      clearTimeout(searchTimeout.current);
    }

    searchTimeout.current = setTimeout(() => {
      if (value.length >= 1) {
        fetchAutocomplete(value);
        executeSearch(value);
      } else {
        setResults([]);
        setShowSuggestions(false);
      }
    }, 300);
  };

  const handleSuggestionClick = (keyword: string) => {
    setQuery(keyword);
    executeSearch(keyword);
    setShowSuggestions(false);
  };

  const handleSelect = (perfume: SearchResult) => {
    const name = isKorean
      ? (perfume.name_kr || perfume.name)
      : (perfume.name || perfume.name_kr);
    const brand = isKorean
      ? (perfume.brand_kr || perfume.brand)
      : (perfume.brand || perfume.brand_kr);
    const insertText = brand ? `${brand} ${name}` : name;

    if (insertText) {
      onSelect(insertText);
    }
    setOpen(false);
  };

  const triggerSizeClass = compact
    ? "w-8 h-8 sm:w-9 sm:h-9 rounded-lg"
    : "w-10 h-10 sm:w-[72px] sm:h-[72px] rounded-lg sm:rounded-xl";

  const iconSizeClass = compact
    ? "w-[14px] h-[14px] sm:w-[16px] sm:h-[16px]"
    : "w-[19px] h-[19px] sm:w-7 sm:h-7";

  return (
    <div className="relative" ref={containerRef}>
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className={`${triggerSizeClass} flex items-center justify-center transition-all ${open ? "bg-[#C5A55D] text-white shadow-md" : "text-gray-400 hover:text-[#C5A55D] hover:bg-[#F5F2EA]"}`}
        title="향수 검색"
        aria-label="향수 검색"
      >
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className={iconSizeClass}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-4.35-4.35m1.1-4.4a7.5 7.5 0 11-15 0 7.5 7.5 0 0115 0z" />
        </svg>
      </button>

      {open && (
        <div className="absolute bottom-full left-0 mb-2 w-[min(88vw,380px)] sm:w-[380px] rounded-2xl border border-[#E6DDCF] bg-white shadow-2xl overflow-hidden z-50">
          <div className="p-3 border-b border-[#E6DDCF] flex justify-between items-center bg-[#FDFBF8]">
            <div className="flex items-center gap-2.5">
              <h2 className="font-bold text-sm text-[#2E2B28]">향수 검색</h2>
              <button
                onClick={() => setIsKorean((prev) => !prev)}
                className="w-7 h-7 flex items-center justify-center rounded-full border border-[#E6DDCF] text-[10px] font-bold text-[#7A6B57] hover:bg-[#2E2B28] hover:text-white transition-all"
                title={isKorean ? "Switch to English" : "한글로 전환"}
              >
                {isKorean ? "KR" : "EN"}
              </button>
            </div>
            <button onClick={() => setOpen(false)} className="text-gray-400 hover:text-gray-600 text-sm">✕</button>
          </div>

          <div className="p-3 relative z-20">
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={handleInputChange}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  if (searchTimeout.current) {
                    clearTimeout(searchTimeout.current);
                  }
                  setShowSuggestions(false);
                  executeSearch(query);
                }
              }}
              placeholder="브랜드 혹은 향수 이름 입력..."
              className="w-full bg-[#FAF8F5] text-[#333] px-3 py-2.5 rounded-xl border border-[#EEE5D8] focus:ring-2 focus:ring-[#C5A55D]/30 focus:border-[#DCC8A0] transition text-sm font-medium placeholder-gray-400"
            />

            {showSuggestions && (suggestions.brands.length > 0 || suggestions.keywords.length > 0) && (
              <div className="absolute left-3 right-3 top-[calc(100%-4px)] bg-white border border-[#EEE5D8] rounded-xl shadow-xl overflow-hidden">
                {suggestions.brands.length > 0 && (
                  <div className="p-1.5">
                    <div className="text-[10px] text-gray-400 font-bold px-2.5 py-1 uppercase">Brands</div>
                    {suggestions.brands.map((brand, idx) => (
                      <div
                        key={`b-${idx}`}
                        onClick={() => handleSuggestionClick(brand)}
                        className="px-2.5 py-2 hover:bg-[#FAF8F5] cursor-pointer text-xs font-medium text-gray-700 flex items-center gap-2 rounded-lg"
                      >
                        <span className="w-1.5 h-1.5 rounded-full bg-indigo-400"></span>
                        {brand}
                      </div>
                    ))}
                  </div>
                )}
                {suggestions.keywords.length > 0 && (
                  <div className="p-1.5 border-t border-gray-50">
                    <div className="text-[10px] text-gray-400 font-bold px-2.5 py-1 uppercase">Perfumes</div>
                    {suggestions.keywords.map((keyword, idx) => (
                      <div
                        key={`k-${idx}`}
                        onClick={() => handleSuggestionClick(keyword)}
                        className="px-2.5 py-2 hover:bg-[#FAF8F5] cursor-pointer text-xs text-gray-600 flex items-center gap-2 rounded-lg"
                      >
                        <svg className="w-3 h-3 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                        </svg>
                        {keyword}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="max-h-72 overflow-y-auto p-3 space-y-2.5 bg-white" onClick={() => setShowSuggestions(false)}>
            {results.length === 0 ? (
              <div className="text-center py-8 text-xs text-gray-400">
                {loading ? "검색 중..." : query ? "검색 결과가 없습니다." : "원하는 향수를 검색해보세요."}
              </div>
            ) : (
              results.map((perfume) => (
                <div
                  key={perfume.perfume_id}
                  className="group flex items-center gap-3 p-2.5 bg-white border border-gray-100 rounded-xl hover:border-[#C5A55D]/30 hover:shadow-md transition"
                >
                  <div className="w-12 h-14 bg-[#f9f9f9] rounded-lg flex items-center justify-center overflow-hidden">
                    {perfume.image_url ? (
                      <img
                        src={perfume.image_url}
                        alt={perfume.name}
                        className="max-w-full max-h-full object-contain mix-blend-multiply scale-[1.2] -translate-y-0.5"
                      />
                    ) : (
                      <span className="text-gray-300 text-[10px]">No img</span>
                    )}
                  </div>

                  <div className="flex-1 min-w-0">
                    <p className="text-[#333] font-bold text-xs truncate">
                      {isKorean ? (perfume.name_kr || perfume.name) : (perfume.name || perfume.name_kr)}
                    </p>
                    <p className="text-[#999] text-[10px] font-medium uppercase tracking-wide truncate mt-0.5">
                      {isKorean ? (perfume.brand_kr || perfume.brand) : perfume.brand}
                    </p>
                  </div>

                  <button
                    onClick={() => handleSelect(perfume)}
                    className="px-2.5 py-1.5 rounded-lg bg-[#2E2B28] text-white border border-[#2E2B28] hover:bg-[#1E1C1A] transition text-[10px] font-bold whitespace-nowrap"
                  >
                    입력
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
