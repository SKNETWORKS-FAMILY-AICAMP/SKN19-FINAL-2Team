"use client";

import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";

const API_URL = "/api";

interface Perfume {
    my_perfume_id: number;
    perfume_name: string;
    brand: string;
    image_url: string | null;
}

interface Props {
    memberId: number;
    onSelect: (name: string) => void;
    compact?: boolean;
}

export default function LayeringPerfumePicker({ memberId, onSelect, compact = false }: Props) {
    const [isOpen, setIsOpen] = useState(false);
    const [perfumes, setPerfumes] = useState<Perfume[]>([]);
    const [loading, setLoading] = useState(false);
    const containerRef = useRef<HTMLDivElement>(null);

    // 외부 클릭 시 닫기
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
                setIsOpen(false);
            }
        };
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    // 데이터 로드
    useEffect(() => {
        if (isOpen && memberId > 0 && perfumes.length === 0) {
            setLoading(true);
            fetch(`${API_URL}/users/${memberId}/perfumes`)
                .then(res => res.json())
                .then(data => {
                    // API 응답 구조 매핑
                    const mapped = data.map((item: any) => ({
                        my_perfume_id: item.perfume_id,
                        perfume_name: item.perfume_name,
                        brand: item.brand,
                        image_url: item.image_url
                    }));
                    setPerfumes(mapped);
                })
                .catch(err => console.error(err))
                .finally(() => setLoading(false));
        }
    }, [isOpen, memberId]);

    const triggerSizeClass = compact
        ? "w-8 h-8 sm:w-9 sm:h-9 rounded-lg"
        : "w-10 h-10 sm:w-[72px] sm:h-[72px] rounded-lg sm:rounded-xl";

    const iconSizeClass = compact
        ? "w-[14px] h-[14px] sm:w-[16px] sm:h-[16px]"
        : "w-[19px] h-[19px] sm:w-7 sm:h-7";

    return (
        <div className="relative" ref={containerRef}>
            {/* 팝오버 창 */}
            <AnimatePresence>
                {isOpen && (
                    <motion.div
                        initial={{ opacity: 0, scale: 0.9, y: 10 }}
                        animate={{ opacity: 1, scale: 1, y: -10 }}
                        exit={{ opacity: 0, scale: 0.9, y: 10 }}
                        transition={{ type: "spring", duration: 0.3 }}
                        className="absolute bottom-full left-0 mb-2 w-72 max-w-[85vw] bg-white/90 backdrop-blur-md border border-[#E6DDCF] rounded-2xl shadow-xl overflow-hidden z-50 origin-bottom-left"
                    >
                        <div className="p-3 bg-[#FDFBF8] border-b border-[#E6DDCF] flex justify-between items-center">
                            <span className="text-xs font-bold text-[#7A6B57]">MY PERFUME ({perfumes.length})</span>
                            <button onClick={() => setIsOpen(false)} className="text-gray-400 hover:text-gray-600 text-xs">✕</button>
                        </div>

                        <div className="max-h-64 overflow-y-auto p-2 custom-scrollbar">
                            {loading ? (
                                <div className="text-center py-4 text-xs text-gray-400">로딩 중...</div>
                            ) : perfumes.length === 0 ? (
                                <div className="text-center py-4 text-xs text-gray-400">등록된 향수가 없어요.</div>
                            ) : (
                                <div className="grid grid-cols-2 gap-2">
                                    {perfumes.map(p => (
                                        <button
                                            key={p.my_perfume_id}
                                            onClick={() => {
                                                onSelect(p.perfume_name);
                                                setIsOpen(false);
                                            }}
                                            className="flex flex-col items-center p-2 rounded-xl border border-transparent hover:border-[#C5A55D]/30 hover:bg-white hover:shadow-sm transition group"
                                        >
                                            <div className="w-10 h-12 mb-2 rounded-lg bg-gray-50 flex items-center justify-center overflow-hidden">
                                                {p.image_url ? (
                                                    <img src={p.image_url} alt={p.perfume_name} className="w-full h-full object-contain mix-blend-multiply" />
                                                ) : (
                                                    <span className="text-[10px] text-gray-300">No img</span>
                                                )}
                                            </div>
                                            <span className="text-[10px] font-bold text-[#333] text-center line-clamp-1 w-full">{p.perfume_name}</span>
                                            <span className="text-[9px] text-[#999] text-center line-clamp-1 w-full group-hover:text-[#C5A55D]">{p.brand}</span>
                                        </button>
                                    ))}
                                </div>
                            )}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* 트리거 버튼 (입력창 옆에 보일 아이콘) */}
            <button
                onClick={() => setIsOpen(!isOpen)}
                className={`${triggerSizeClass} flex items-center justify-center transition-all ${isOpen ? 'bg-[#C5A55D] text-white shadow-md' : 'text-gray-400 hover:text-[#C5A55D] hover:bg-[#F5F2EA]'}`}
                title="내 향수 불러오기"
            >
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className={iconSizeClass}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M21 11.25v8.25a1.5 1.5 0 0 1-1.5 1.5H4.5a1.5 1.5 0 0 1-1.5-1.5v-8.25M12 4.875A2.625 2.625 0 1 0 9.375 7.5H12m0-2.625V7.5m0-2.625A2.625 2.625 0 1 1 14.625 7.5H12m0 0V21m-8.625-9.75h1.875c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125Zm17.25 0h1.875c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125h-1.875c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125Z" />
                </svg>
            </button>
        </div>
    );
}
