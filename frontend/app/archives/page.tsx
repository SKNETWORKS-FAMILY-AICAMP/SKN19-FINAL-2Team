"use client";

import { useState, useEffect, useMemo } from "react";
import { useSession } from "next-auth/react"; // 카카오 로그인 세션
import Link from "next/link";
import ArchiveSidebar from "@/components/archives/ArchiveSidebar";
import CabinetShelf from "@/components/archives/CabinetShelf";
import PerfumeSearchModal from "@/components/archives/PerfumeSearchModal";
import PerfumeDetailModal from "@/components/archives/PerfumeDetailModal";
import HistoryModal from '@/components/archives/HistoryModal';
import ArchiveGlobeView from "@/components/archives/ArchiveGlobeView";
import PageLayout from "@/components/common/PageLayout";
import { SavedPerfumesProvider } from "@/contexts/SavedPerfumesContext";
import { motion, AnimatePresence } from "framer-motion";

const API_URL = "/api";
// const MEMBER_ID = 1;

interface MyPerfume {
    my_perfume_id: number;
    perfume_id: number;
    name: string;
    name_en?: string;
    name_kr?: string;
    brand: string;
    brand_kr?: string;
    image_url: string | null;
    register_status: string;
    preference?: string;
    status: string;
}

type TabType = 'ALL' | 'HAVE' | 'HAD' | 'WISH';

const createSeededRandom = (seed: number) => {
    let state = seed >>> 0;
    return () => {
        state = (state * 1664525 + 1013904223) >>> 0;
        return state / 4294967296;
    };
};

const getStarColor = (r: number, alpha: number) => {
    if (r < 0.08) return `rgba(170, 198, 255, ${alpha})`; // 차가운 블루 별
    if (r < 0.14) return `rgba(255, 226, 185, ${alpha})`; // 따뜻한 별
    return `rgba(255, 255, 255, ${alpha})`; // 기본 화이트 별
};

const buildStarLayer = ({
    rng,
    count,
    minSize,
    maxSize,
    minOpacity,
    maxOpacity,
}: {
    rng: () => number;
    count: number;
    minSize: number;
    maxSize: number;
    minOpacity: number;
    maxOpacity: number;
}) => {
    return Array.from({ length: count }, () => {
        const x = (rng() * 100).toFixed(2);
        const y = (rng() * 100).toFixed(2);
        const size = minSize + rng() * (maxSize - minSize);
        const alpha = minOpacity + rng() * (maxOpacity - minOpacity);
        const color = getStarColor(rng(), Number(alpha.toFixed(3)));
        const inner = `${size.toFixed(2)}px`;
        const outer = `${(size + 0.85).toFixed(2)}px`;
        return `radial-gradient(circle at ${x}% ${y}%, ${color} 0px, ${color} ${inner}, transparent ${outer})`;
    }).join(", ");
};

export default function ArchivesPage() {
    const { data: session } = useSession(); // 카카오 로그인 세션
    const [collection, setCollection] = useState<MyPerfume[]>([]);
    const [selectedPerfume, setSelectedPerfume] = useState<MyPerfume | null>(null);
    const [activeTab, setActiveTab] = useState<TabType>('ALL');
    const [isSidebarOpen, setIsSidebarOpen] = useState(false);
    const [isSearchOpen, setIsSearchOpen] = useState(false);
    const [isAddModalOpen, setIsAddModalOpen] = useState(false);
    const [isKorean, setIsKorean] = useState(true);
    const [isHistoryOpen, setIsHistoryOpen] = useState(false);
    const [memberId, setMemberId] = useState<number>(0);
    const [viewMode, setViewMode] = useState<'GRID' | 'GLOBE'>('GRID');
    const [isMounted, setIsMounted] = useState(false);
    const [searchQuery, setSearchQuery] = useState("");
    const [isMobileSearchExpanded, setIsMobileSearchExpanded] = useState(false); // 모바일 검색 확장 상태

    const isGalaxy = viewMode === 'GLOBE';
    const t = isKorean
        ? {
            switchToGallery: "갤러리 모드로 전환",
            switchToGalaxy: "갤럭시 모드로 전환",
            total: "총합",
            have: "보유",
            wish: "위시",
            searchPlaceholder: "보유향수 검색",
            history: "히스토리",
            addScent: "향수 추가",
            noScents: "검색 결과가 없어요",
            addFirst: "+ 첫 향수 추가하기",
            scentMap: "향수 지도",
        }
        : {
            switchToGallery: "Switch to Gallery mode",
            switchToGalaxy: "Switch to Galaxy mode",
            total: "TOTAL",
            have: "HAVE",
            wish: "WISH",
            searchPlaceholder: "SEARCH YOUR SCENTS...",
            history: "HISTORY",
            addScent: "ADD SCENT",
            noScents: "No scents found",
            addFirst: "+ Add Your First Perfume",
            scentMap: "Scent Map",
        };
    const modeLabel = isGalaxy ? "GALAXY" : "GALLERY";
    const modeLabelSlotClass = "w-[7.8ch] md:w-[8.4ch]";
    const modeLabelTextClass = "tracking-[-0.015em]";
    const archiveSubtitleFixed = "나만의 향수 보관함";

    const galaxyStarfieldStyle = useMemo(() => {
        const rng = createSeededRandom(20260210);
        const layer1 = buildStarLayer({
            rng,
            count: 90,
            minSize: 0.45,
            maxSize: 0.95,
            minOpacity: 0.28,
            maxOpacity: 0.66,
        });
        const layer2 = buildStarLayer({
            rng,
            count: 46,
            minSize: 0.85,
            maxSize: 1.55,
            minOpacity: 0.45,
            maxOpacity: 0.86,
        });
        const layer3 = buildStarLayer({
            rng,
            count: 18,
            minSize: 1.4,
            maxSize: 2.3,
            minOpacity: 0.62,
            maxOpacity: 0.98,
        });

        return {
            backgroundImage: [layer1, layer2, layer3].join(", "),
        };
    }, []);

    useEffect(() => {
        setIsMounted(true);
    }, []);

    // 화면 크기 변경 시 모바일 검색 확장 상태 초기화
    useEffect(() => {
        const handleResize = () => {
            if (window.innerWidth >= 768) {
                setIsMobileSearchExpanded(false);
            }
        };
        window.addEventListener('resize', handleResize);
        return () => window.removeEventListener('resize', handleResize);
    }, []);

    const fetchPerfumes = async () => {
        if (memberId === 0) return;
        try {
            const res = await fetch(`${API_URL}/users/${memberId}/perfumes`);
            if (res.ok) {
                const data = await res.json();
                const mapped = data.map((item: any) => ({
                    my_perfume_id: item.perfume_id,
                    perfume_id: item.perfume_id,
                    name: item.perfume_name,
                    name_en: item.name_en || item.perfume_name,
                    name_kr: item.name_kr || item.perfume_name,
                    brand: item.brand || "Unknown",
                    brand_kr: item.brand_kr || item.brand,
                    image_url: item.image_url || null,
                    register_status: item.register_status,
                    register_dt: item.register_dt,
                    preference: item.preference,
                    status: item.register_status
                }));
                setCollection(mapped);
            }
        } catch (e) {
            console.error("Failed to fetch perfumes", e);
        }
    };

    useEffect(() => {
        if (session?.user?.id) {
            setMemberId(Number(session.user.id));
        }
    }, [session]);

    const displayName = session?.user?.name || session?.user?.email?.split('@')[0] || "Guest";
    const isLoggedIn = Boolean(session);

    useEffect(() => {
        if (memberId > 0) {
            fetchPerfumes();
        }
    }, [memberId]);

    const handleAdd = async (perfume: any, status: string) => {
        if (memberId === 0) return;
        try {
            const payload = {
                perfume_id: perfume.perfume_id,
                perfume_name: perfume.name,
                register_status: status,
                register_reason: "USER",
                preference: "NEUTRAL"
            };
            await fetch(`${API_URL}/users/${memberId}/perfumes`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            fetchPerfumes();
        } catch (e) { console.error("Add failed", e); }
    };

    const handleUpdateStatus = async (id: number, status: string) => {
        if (memberId === 0) return;
        try {
            await fetch(`${API_URL}/users/${memberId}/perfumes/${id}`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ register_status: status })
            });
            fetchPerfumes();
            if (selectedPerfume && selectedPerfume.my_perfume_id === id) {
                setSelectedPerfume({ ...selectedPerfume, register_status: status, status: status });
            }
        } catch (e) { console.error("Update failed", e); }
    };

    const handleDelete = async (id: number, rating?: number) => {
        if (memberId === 0) return;
        try {
            if (rating !== undefined) {
                let pref = "NEUTRAL";
                if (rating === 3) pref = "GOOD";
                if (rating === 1) pref = "BAD";

                await fetch(`${API_URL}/users/${memberId}/perfumes/${id}`, {
                    method: "PATCH",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ register_status: "HAD", preference: pref })
                });
            } else {
                await fetch(`${API_URL}/users/${memberId}/perfumes/${id}`, {
                    method: "DELETE"
                });
            }
            fetchPerfumes();
            setSelectedPerfume(null);
        } catch (e) { console.error("Delete failed", e); }
    };

    const handleUpdatePreference = async (id: number, preference: string) => {
        if (memberId === 0) return;
        try {
            await fetch(`${API_URL}/users/${memberId}/perfumes/${id}`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ register_status: "HAD", preference: preference })
            });
            fetchPerfumes();
            setSelectedPerfume(prev => prev ? { ...prev, register_status: 'HAD', status: 'HAD', preference: preference } : null);
        } catch (e) { console.error("Update preference failed", e); }
    };

    const stats = {
        have: collection.filter(p => p.register_status === 'HAVE').length,
        had: collection.filter(p => p.register_status === 'HAD').length,
        wish: collection.filter(p => p.register_status === 'RECOMMENDED').length
    };

    const filteredCollection = collection.filter(item => {
        let matchesTab = true;
        if (activeTab === 'ALL') matchesTab = item.register_status !== 'HAD';
        else if (activeTab === 'HAVE') matchesTab = item.register_status === 'HAVE';
        else if (activeTab === 'HAD') matchesTab = item.register_status === 'HAD';
        else if (activeTab === 'WISH') matchesTab = item.register_status === 'RECOMMENDED';

        if (!matchesTab) return false;

        if (searchQuery.trim()) {
            const query = searchQuery.toLowerCase();
            const nameMatch =
                item.name_kr?.toLowerCase().includes(query) ||
                item.name_en?.toLowerCase().includes(query) ||
                item.name?.toLowerCase().includes(query);
            const brandMatch =
                item.brand_kr?.toLowerCase().includes(query) ||
                item.brand?.toLowerCase().includes(query);
            return nameMatch || brandMatch;
        }

        return true;
    });

    if (!isMounted) return null;

    return (
        <SavedPerfumesProvider memberId={memberId}>
            <PageLayout
                className={`min-h-screen font-sans overflow-x-hidden relative ${isGalaxy ? 'bg-[#02030A] text-white' : 'bg-[#FDFBF8] text-black'}`}
                isTransparent={isGalaxy}
                headerTheme={isGalaxy ? "dark" : "light"}
                disableContentPadding
            >
                {isGalaxy ? (
                    <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
                        <div className="absolute inset-0 bg-[#02030A]" />
                        <div
                            className="absolute inset-0 opacity-95"
                            style={galaxyStarfieldStyle}
                        />
                        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,rgba(255,255,255,0.12),transparent_45%),radial-gradient(ellipse_at_bottom,rgba(84,105,255,0.16),transparent_52%)]" />
                        <div className="absolute inset-0 bg-gradient-to-b from-black/25 via-transparent to-black/45" />
                    </div>
                ) : (
                    <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
                        <motion.div
                            animate={{
                                x: [0, 80, 0],
                                y: [0, 40, 0],
                                scale: [1, 1.1, 1],
                            }}
                            transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
                            className="absolute -top-[5%] -right-[5%] w-[40%] h-[40%] bg-[#D4E6F1]/20 rounded-full blur-[100px]"
                        />
                        <motion.div
                            animate={{
                                x: [0, -60, 0],
                                y: [0, 80, 0],
                                scale: [1, 1.2, 1],
                            }}
                            className="absolute bottom-[10%] -left-[10%] w-[50%] h-[50%] bg-[#FADBD8]/20 rounded-full blur-[100px]"
                        />
                    </div>
                )}

                {/* Main Content */}
                <main className="relative z-10 pt-[70px] sm:pt-[98px] md:pt-[108px] lg:pt-[114px] pb-32 px-3 sm:px-6 max-w-7xl mx-auto min-h-screen">
                    {/* Header: Title & Description & Controls */}
                    <div className="mb-6 md:mb-8">
                        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-2">
                            <div className="flex items-center gap-4">
                                <motion.button
                                    type="button"
                                    initial="initial"
                                    whileHover="hover"
                                    onClick={() => setViewMode((prev) => (prev === 'GRID' ? 'GLOBE' : 'GRID'))}
                                    /* [가이드] 타이틀 배치 조정:
                                       - items-baseline: 글자 밑선 기준 정렬 (추천). items-center, items-start 등으로 변경 가능.
                                       - gap-2 md:gap-3: MY와 GALAXY 사이 간격.
                                    */
                                    className="group flex items-baseline gap-2 md:gap-3 text-2xl sm:text-[2.78rem] md:text-[3.48rem] lg:text-6xl font-black tracking-tighter leading-[0.94] md:leading-[0.9] uppercase whitespace-nowrap cursor-pointer z-10"
                                    title={modeLabel === 'GALAXY' ? t.switchToGallery : t.switchToGalaxy}
                                >
                                    <span className={`transition-colors duration-300 ${isGalaxy ? 'text-white' : 'text-black'}`}>MY</span>

                                    {/* Responsive Container using Invisible Spacer Text */}
                                    <span className="relative inline-block text-left">
                                        {/* Invisible Spacer to set natural width/height matching the font metrics exactly */}
                                        <span className="opacity-0 select-none" aria-hidden="true">GALLERY</span>

                                        <AnimatePresence mode="wait" initial={false}>
                                            <motion.span
                                                key={modeLabel}
                                                /* [가이드] 텍스트 높이 조정: bottom-[0em] 값을 조절하세요 (예: bottom-1, bottom-[-0.1em]) */
                                                initial={{ y: 5, opacity: 0 }}
                                                animate={{ y: 0, opacity: 1 }}
                                                exit={{ y: -5, opacity: 0 }}
                                                transition={{ duration: 0.25, ease: "easeOut" }}
                                                className={`absolute left-0 bottom-[0em] origin-bottom ${isGalaxy ? 'text-white' : 'text-black'}`}
                                            >
                                                {modeLabel}
                                            </motion.span>
                                        </AnimatePresence>

                                        {/* [가이드] 밑줄 위치 조정: -bottom-[0.2em] 값을 조절하세요 (숫자가 커질수록 더 아래로 내려감) */}
                                        <span className={`absolute left-0 -bottom-[3px] w-full h-[3px] md:h-[4px] rounded-full transition-colors duration-300 ${isGalaxy ? 'bg-white/40 group-hover:bg-white/80' : 'bg-black/20 group-hover:bg-black/60'}`} />
                                    </span>

                                    {/* Rotating Icon - Grouped with Title */}
                                    <motion.span
                                        variants={{
                                            hover: { rotate: 180, scale: 1.1 },
                                            initial: { rotate: 0, scale: 1 }
                                        }}
                                        transition={{ duration: 0.4 }}
                                        className={`ml-1 md:ml-2 self-center p-1 rounded-full ${isGalaxy ? 'text-white/70 group-hover:text-white' : 'text-black/50 group-hover:text-black'}`}
                                    >
                                        <svg
                                            className="w-5 h-5 md:w-6 md:h-6"
                                            viewBox="0 0 24 24"
                                            fill="none"
                                            stroke="currentColor"
                                            strokeWidth="2"
                                            strokeLinecap="round"
                                            strokeLinejoin="round"
                                        >
                                            <path d="M3 12a9 9 0 0 1 15.5-6.4" />
                                            <path d="M18.5 2.5v4h-4" />
                                            <path d="M21 12a9 9 0 0 1-15.5 6.4" />
                                            <path d="M5.5 21.5v-4h4" />
                                        </svg>
                                    </motion.span>
                                </motion.button>

                                {/* Language Toggle (Moved from Menu) */}
                                <button
                                    onClick={() => setIsKorean((prev) => !prev)}
                                    className={`ml-1 md:ml-2 p-2 rounded-full transition-colors duration-300 ${isGalaxy ? 'text-white/50 hover:text-white hover:bg-white/10' : 'text-black/30 hover:text-black hover:bg-black/5'}`}
                                    title={isKorean ? "Switch to English" : "한국어로 전환"}
                                >
                                    <svg
                                        className="w-5 h-5 md:w-6 md:h-6"
                                        viewBox="0 0 24 24"
                                        fill="none"
                                        stroke="currentColor"
                                        strokeWidth="2"
                                        strokeLinecap="round"
                                        strokeLinejoin="round"
                                    >
                                        <circle cx="12" cy="12" r="10" />
                                        <line x1="2" y1="12" x2="22" y2="12" />
                                        <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
                                    </svg>
                                </button>
                            </div>

                            {/* Controls: Removed (Language Toggle moved up) */}
                        </div>


                        <motion.p
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            transition={{ delay: 0.3 }}
                            className={`text-xs md:text-sm font-bold uppercase tracking-[0.2em] ${isGalaxy ? 'text-white/60' : 'text-gray-400'}`}
                        >
                            {archiveSubtitleFixed}
                        </motion.p>
                    </div>

                    {/* Stats & Toolbar Row */}
                    <div className="flex flex-col md:flex-row items-center md:items-start justify-between gap-3 mb-8 md:mb-12">

                        {/* 1. Group 1: Stats + Search Icon (Lang Removed) */}
                        <motion.div
                            layout // [추가] 검색창 열릴 때 부드럽게 너비 확장
                            transition={{ duration: 0.3, ease: "easeOut" }} // [추가] 레이아웃 변경 애니메이션 설정
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            // [수정] 높이 60px로 증가 for visual balance
                            className={`relative w-full md:w-auto md:h-[60px] flex flex-wrap md:flex-nowrap items-center justify-between md:justify-start gap-1 md:gap-3 px-1.5 md:px-3 py-1.5 rounded-[20px] md:rounded-[30px] ${isGalaxy
                                ? 'bg-black/45 border border-white/22 backdrop-blur-xl shadow-[inset_0_1px_0_rgba(255,255,255,0.2),0_18px_40px_rgba(0,0,0,0.5)]'
                                : 'bg-white/40 border border-white/60 backdrop-blur-md shadow-sm'
                                }`}
                        >
                            {/* [Mobile] Stats divided evenly */}
                            <div className="flex-1 flex items-center justify-center md:flex-none h-full">
                                <StatItem
                                    label={t.total}
                                    count={stats.have + stats.wish}
                                    activeColor={isGalaxy ? 'text-white' : 'text-black'}
                                    isActive={activeTab === 'ALL'}
                                    onClick={() => setActiveTab('ALL')}
                                    isGalaxy={isGalaxy}
                                />
                            </div>
                            <div className={`w-px h-6 hidden sm:block ${isGalaxy ? 'bg-white/28' : 'bg-gray-200/50'}`} />

                            <div className="flex-1 flex items-center justify-center md:flex-none h-full">
                                <StatItem
                                    label={t.have}
                                    count={stats.have}
                                    activeColor={isGalaxy ? 'text-sky-300' : 'text-indigo-500'}
                                    isActive={activeTab === 'HAVE'}
                                    onClick={() => setActiveTab('HAVE')}
                                    isGalaxy={isGalaxy}
                                />
                            </div>
                            <div className={`w-px h-6 hidden sm:block ${isGalaxy ? 'bg-white/28' : 'bg-gray-200/50'}`} />

                            <div className="flex-1 flex items-center justify-center md:flex-none h-full">
                                <StatItem
                                    label={t.wish}
                                    count={stats.wish}
                                    activeColor={isGalaxy ? 'text-rose-300' : 'text-rose-400'}
                                    isActive={activeTab === 'WISH'}
                                    onClick={() => setActiveTab('WISH')}
                                    isGalaxy={isGalaxy}
                                />
                            </div>

                            {/* [Desktop Only] Divider */}
                            <div className={`w-px h-6 hidden md:block ${isGalaxy ? 'bg-white/28' : 'bg-gray-200/50'}`} />

                            {/* [Desktop] Expandable Search */}
                            <div className="hidden md:flex items-center ml-1">
                                <div className="flex items-center">
                                    {/* 1. Search Icon (Always Visible) */}
                                    <button
                                        onClick={() => setIsSearchOpen(prev => !prev)}
                                        className={`p-2 rounded-full transition-colors ${isGalaxy ? 'text-white/60 hover:text-white hover:bg-white/10' : 'text-black/50 hover:text-black hover:bg-black/5'}`}
                                        title="Search"
                                    >
                                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
                                    </button>

                                    {/* 2. Expanding Input Container (Expands to Right) */}
                                    <motion.div
                                        initial={false}
                                        animate={{ width: isSearchOpen ? 200 : 0, opacity: isSearchOpen ? 1 : 0 }}
                                        transition={{ duration: 0.3, ease: "easeOut" }}
                                        className="overflow-hidden h-full flex items-center"
                                    >
                                        <div className="relative w-[200px] h-full flex items-center pl-2">
                                            <input
                                                type="text"
                                                value={searchQuery}
                                                onChange={(e) => setSearchQuery(e.target.value)}
                                                placeholder={t.searchPlaceholder}
                                                // Removed autoFocus to prevent jarring jump, or keep if desired
                                                // onBlur={() => !searchQuery && setIsSearchOpen(false)} // Optional: close on blur if empty
                                                className={`w-full h-9 rounded-xl pl-3 pr-8 text-xs font-bold leading-none bg-transparent outline-none ${isGalaxy
                                                    ? 'text-white placeholder:text-white/40'
                                                    : 'text-black placeholder:text-black/40'
                                                    }`}
                                            />
                                            {/* Close/Clear Button */}
                                            <button
                                                onClick={() => {
                                                    setSearchQuery("");
                                                    setIsSearchOpen(false);
                                                }}
                                                className={`absolute right-1 top-1/2 -translate-y-1/2 p-1 rounded-full ${isGalaxy ? 'text-white/40 hover:text-white' : 'text-black/40 hover:text-black'}`}
                                            >
                                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M6 18L18 6M6 6l12 12"></path></svg>
                                            </button>
                                        </div>
                                    </motion.div>
                                </div>
                            </div>

                            {/* [Mobile Only] Search Trigger Icon */}
                            <button
                                onClick={() => setIsMobileSearchExpanded(true)}
                                className={`
                                    md:hidden flex items-center justify-center w-10 h-10
                                    ${isMobileSearchExpanded ? 'hidden' : 'block'}
                                    ${isGalaxy ? 'text-white/70' : 'text-black/60'}
                                `}
                            >
                                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
                            </button>

                            {/* [Mobile Only] Expanded Search Overlay */}
                            <AnimatePresence>
                                {isMobileSearchExpanded && (
                                    <motion.div
                                        initial={{ opacity: 0, scale: 0.95 }}
                                        animate={{ opacity: 1, scale: 1 }}
                                        exit={{ opacity: 0, scale: 0.95 }}
                                        transition={{ duration: 0.2, ease: "easeOut" }}
                                        // [수정] 부모와 동일한 rounded-[20px], -inset-[1px]로 부모 테두리 덮기
                                        className={`absolute -inset-[1px] z-50 flex items-center px-2 rounded-[20px] ${isGalaxy
                                            ? 'bg-[#18181b] text-white border border-white/22'
                                            : 'bg-white text-black border border-white/60 shadow-sm'
                                            }`}
                                    >
                                        <button
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                setIsMobileSearchExpanded(false);
                                                setSearchQuery("");
                                            }}
                                            className={`p-2 mr-1 rounded-full ${isGalaxy ? 'hover:bg-white/10 text-white/70' : 'hover:bg-black/5 text-black/60'}`}
                                        >
                                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M15 19l-7-7 7-7"></path></svg>
                                        </button>
                                        <div className="flex-1 relative">
                                            <div className={`absolute left-3 top-1/2 -translate-y-1/2 ${isGalaxy ? 'text-white/40' : 'text-black/40'}`}>
                                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
                                            </div>
                                            <input
                                                type="text"
                                                value={searchQuery}
                                                onChange={(e) => setSearchQuery(e.target.value)}
                                                placeholder={t.searchPlaceholder}
                                                autoFocus
                                                className={`w-full h-9 rounded-xl pl-9 pr-8 text-xs font-bold bg-transparent outline-none ${isGalaxy ? 'text-white placeholder:text-white/40' : 'text-black placeholder:text-black/40'
                                                    }`}
                                            />
                                            {searchQuery && (
                                                <button
                                                    onClick={() => setSearchQuery("")}
                                                    className={`absolute right-2 top-1/2 -translate-y-1/2 p-1 ${isGalaxy ? 'text-white/50' : 'text-black/50'}`}
                                                >
                                                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M6 18L18 6M6 6l12 12"></path></svg>
                                                </button>
                                            )}
                                        </div>
                                    </motion.div>
                                )}
                            </AnimatePresence>
                        </motion.div>

                        {/* 2. Group 2 & 3: History & Add (Separate Buttons) */}
                        <div className="hidden md:flex items-center gap-3 h-[60px]">
                            {/* Group 2: History Button (Standalone) */}
                            <div className="relative h-full">
                                <motion.button
                                    whileHover={{ scale: 1.02 }}
                                    whileTap={{ scale: 0.98 }}
                                    onClick={() => setIsHistoryOpen(!isHistoryOpen)}
                                    // [수정] 높이 60px 적용
                                    className={`flex items-center gap-3 px-6 h-full rounded-[30px] transition-all duration-300 ${isGalaxy
                                        ? `${isHistoryOpen ? 'bg-white/20 ring-1 ring-white/50' : 'bg-black/45 hover:bg-black/60'} text-white/90 border border-white/22 backdrop-blur-xl shadow-[inset_0_1px_0_rgba(255,255,255,0.2),0_18px_40px_rgba(0,0,0,0.5)]`
                                        : `${isHistoryOpen ? 'bg-black/5 ring-1 ring-black/10' : 'bg-white/40 hover:bg-white/60'} text-black/70 border border-white/60 backdrop-blur-md shadow-sm`
                                        }`}
                                    title={t.history}
                                >
                                    <svg className={`w-5 h-5 ${isGalaxy ? 'text-white/70' : 'text-black/50'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                                    <div className="flex flex-col items-start leading-none gap-0.5">
                                        <span className={`text-[9px] font-black uppercase tracking-widest ${isGalaxy ? 'text-white/50' : 'text-black/40'}`}>History</span>
                                        <span className="text-sm font-black">{stats.had}</span>
                                    </div>
                                </motion.button>
                                <AnimatePresence>
                                    {isHistoryOpen && (
                                        <HistoryModal
                                            historyItems={collection.filter(p => p.register_status === 'HAD')}
                                            onClose={() => setIsHistoryOpen(false)}
                                            onSelect={(p) => setSelectedPerfume(p as MyPerfume)}
                                            isKorean={isKorean}
                                        />
                                    )}
                                </AnimatePresence>
                            </div>

                            {/* Group 3: Add Button (Standalone) */}
                            <motion.button
                                whileHover={{ scale: 1.05 }}
                                whileTap={{ scale: 0.95 }}
                                onClick={() => setIsSearchOpen(true)}
                                // [수정] 높이 60px 적용, 스타일 더욱 강렬하게
                                className={`flex items-center justify-center gap-2 px-8 h-full rounded-[30px] text-xs font-black uppercase tracking-wider relative overflow-hidden group ${isGalaxy
                                    ? 'bg-gradient-to-r from-indigo-500 to-purple-600 text-white shadow-lg shadow-indigo-500/30 border border-white/10'
                                    : 'bg-black text-white hover:bg-gray-800 shadow-md border border-transparent'
                                    }`}
                            >
                                {/* Glow Effect for Galaxy */}
                                {isGalaxy && (
                                    <div className="absolute inset-0 bg-white/20 translate-y-full group-hover:translate-y-0 transition-transform duration-300 blur-md rounded-[30px]" />
                                )}
                                <span className="relative z-10">Add</span>
                                <svg className="w-3.5 h-3.5 relative z-10" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M12 6v6m0 0v6m0-6h6m-6 0H6"></path></svg>
                            </motion.button>
                        </div>

                        {/* 3. Action Toolbar (Mobile Only - remains separate row below stats) */}
                        <div className="order-1 -mt-2 md:hidden flex items-center gap-3 w-full justify-between">
                            <div className="flex items-center gap-3 w-full">
                                <div className="relative">
                                    <button
                                        onClick={() => setIsHistoryOpen(!isHistoryOpen)}
                                        className={`flex items-center gap-2 px-5 py-3 rounded-full transition-all ${isGalaxy
                                            ? `${isHistoryOpen ? 'ring-2 ring-white/85' : ''} border border-white/45 bg-black/58 backdrop-blur-md hover:bg-black/44 shadow-[0_8px_20px_rgba(0,0,0,0.45)]`
                                            : `${isHistoryOpen ? 'ring-2 ring-black bg-white shadow-md' : 'shadow-sm'} border border-gray-100 bg-white/50 backdrop-blur-sm hover:border-gray-200`
                                            }`}
                                    >
                                        <svg className={`w-4 h-4 ${isGalaxy ? 'text-white/92' : 'text-gray-400'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                                        <span className={`text-[10px] font-black uppercase tracking-widest ${isGalaxy ? 'text-white' : 'text-gray-500'}`}>{t.history}</span>
                                        <span className={`text-xs font-black ml-1 ${isGalaxy ? 'text-white' : 'text-black'}`}>{stats.had}</span>
                                    </button>
                                    <AnimatePresence>
                                        {isHistoryOpen && (
                                            <HistoryModal
                                                historyItems={collection.filter(p => p.register_status === 'HAD')}
                                                onClose={() => setIsHistoryOpen(false)}
                                                onSelect={(p) => setSelectedPerfume(p as MyPerfume)}
                                                isKorean={isKorean}
                                            />
                                        )}
                                    </AnimatePresence>
                                </div>
                                <motion.button
                                    whileHover={{ scale: 1.02 }}
                                    whileTap={{ scale: 0.98 }}
                                    onClick={() => setIsAddModalOpen(true)}
                                    className={`flex-1 flex items-center justify-center gap-2 px-6 py-2.5 rounded-full text-[9px] font-black uppercase tracking-[0.1em] ${isGalaxy
                                        ? 'bg-[#606EFF]/90 border border-[#CFD4FF]/80 text-white backdrop-blur-md hover:bg-[#7380FF]/95 shadow-[0_10px_28px_rgba(78,96,255,0.55)]'
                                        : 'bg-black text-white shadow-lg shadow-black/10'
                                        }`}
                                >
                                    <span>{t.addScent}</span>
                                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M12 6v6m0 0v6m0-6h6m-6 0H6"></path></svg>
                                </motion.button>
                            </div>
                        </div>
                    </div>

                    {/* Content Section */}
                    <AnimatePresence mode="wait">
                        {viewMode === 'GLOBE' ? (
                            <motion.div
                                key="globe"
                                initial={{ opacity: 0, scale: 0.98 }}
                                animate={{ opacity: 1, scale: 1 }}
                                exit={{ opacity: 0, scale: 1.02 }}
                                className="animate-fade-in"
                            >
                                <ArchiveGlobeView collection={filteredCollection} isKorean={isKorean} />
                            </motion.div>
                        ) : (
                            <motion.div
                                key="grid"
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, y: -20 }}
                            >
                                {filteredCollection.length === 0 ? (
                                    <div className={`flex flex-col items-center justify-center py-32 rounded-[40px] border backdrop-blur-sm ${isGalaxy ? 'bg-black/35 border-white/20' : 'bg-white/30 border-white/50'
                                        }`}>
                                        <p className={`font-bold uppercase tracking-widest mb-6 ${isGalaxy ? 'text-white/70' : 'text-gray-400'}`}>{t.noScents}</p>
                                        <button
                                            onClick={() => setIsAddModalOpen(true)}
                                            className={`font-black text-xs uppercase tracking-widest hover:underline decoration-2 underline-offset-8 ${isGalaxy ? 'text-white' : 'text-black'}`}
                                        >
                                            {t.addFirst}
                                        </button>
                                    </div>
                                ) : (
                                    <section className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-2 md:gap-8">
                                        {filteredCollection.map((item) => (
                                            <CabinetShelf
                                                key={item.my_perfume_id}
                                                perfume={item}
                                                onSelect={(p) => setSelectedPerfume(p as MyPerfume)}
                                                isKorean={isKorean}
                                            />
                                        ))}
                                    </section>
                                )}
                            </motion.div>
                        )}
                    </AnimatePresence>
                </main>

                {isAddModalOpen && (
                    <PerfumeSearchModal
                        memberId={String(memberId)}
                        onClose={() => setIsAddModalOpen(false)}
                        onAdd={handleAdd}
                        isKorean={isKorean}
                        onToggleLanguage={() => setIsKorean(!isKorean)}
                        existingIds={collection.map(p => p.perfume_id)}
                    />
                )}
                {selectedPerfume && (
                    <PerfumeDetailModal
                        perfume={selectedPerfume}
                        onClose={() => setSelectedPerfume(null)}
                        onUpdateStatus={handleUpdateStatus}
                        onDelete={handleDelete}
                        onUpdatePreference={handleUpdatePreference}
                        isKorean={isKorean}
                    />
                )}
            </PageLayout>
        </SavedPerfumesProvider >
    );
}

function StatItem({
    label,
    count,
    activeColor = "text-black",
    isActive,
    onClick,
    isGalaxy = false,
}: {
    label: string;
    count: number;
    activeColor?: string;
    isActive: boolean;
    onClick: () => void;
    isGalaxy?: boolean;
}) {
    // [수정] 배경 없는 텍스트 전용 버튼 디자인
    return (
        <button
            onClick={onClick}
            // [수정] 배경/그림자/테두리 스타일 제거
            // 오직 Active 아닐 때 투명도(opacity) 차이만으로 구분
            className={`
                flex flex-col items-center justify-center w-full md:w-auto md:min-w-[96px] h-full px-2 md:px-4 py-1 rounded-[25px] transition-all duration-300
                ${!isActive
                    ? (isGalaxy ? 'hover:opacity-100 opacity-40' : 'hover:opacity-100 opacity-40')
                    : 'opacity-100' // active는 투명도 100%
                }
            `}
        >
            <span className={`text-[9px] md:text-[9.5px] font-black uppercase tracking-widest mb-[1px] transition-colors ${isGalaxy ? 'text-white' : 'text-black'
                }`}>
                {label}
            </span>
            <span className={`text-[1.8rem] md:text-[1.85rem] leading-[0.9] font-black transition-all ${isActive
                ? activeColor // Active일 때 색상 (Pink, Sky 등)
                : (isGalaxy ? 'text-white' : 'text-gray-400') // Inactive일 때 기본 색상 (부모 opacity 영향을 받아 흐려짐)
                }`}>
                {count}
            </span>
        </button>
    );
}
