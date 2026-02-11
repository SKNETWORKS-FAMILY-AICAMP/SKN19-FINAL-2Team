"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { Home, Sparkles, Layers, Map as MapIcon, BookOpen, Phone, Info, FlaskConical, Network, Globe } from "lucide-react";

interface SidebarProps {
    isOpen: boolean;
    onClose: () => void;
    context: "home" | "chat";
}

// [MENU ITEM] Icon + Text + Glass Interaction
function MenuItem({ href, icon: Icon, title, desc, onClick, className = "" }: any) {
    return (
        <Link
            href={href}
            onClick={onClick}
            className={`flex items-center gap-3 md:gap-4 py-2.5 md:py-3.5 px-4 md:px-6 hover:bg-white/10 transition-all duration-300 group rounded-xl ${className}`}
        >
            {/* Icon with Glassy Glow */}
            <div className="relative group-hover:scale-110 transition-transform duration-300">
                <Icon strokeWidth={1.5} className="w-5 h-5 md:w-6 md:h-6 text-[#1a1a1a] group-hover:text-black transition-colors" />
                <div className="absolute inset-0 bg-white/20 blur-md opacity-0 group-hover:opacity-100 transition-opacity" />
            </div>

            <div className="flex flex-col">
                <span className="text-base md:text-lg font-bold text-[#1a1a1a] tracking-tight group-hover:tracking-widest transition-all duration-500 whitespace-nowrap">
                    {title}
                </span>
                {desc && <span className="text-[10px] text-gray-500 mt-0.5">{desc}</span>}
            </div>

            {/* Hidden Dot Indicator */}
            <div className="ml-auto w-1.5 h-1.5 rounded-full bg-black opacity-0 group-hover:opacity-100 transition-all transform scale-0 group-hover:scale-100 shadow-[0_0_8px_rgba(0,0,0,0.1)]" />
        </Link>
    );
}

export default function Sidebar({ isOpen, onClose, context }: SidebarProps) {
    // localAuth 제거: 사이드바는 로그인 정보에 의존하지 않음

    const [ref, setRef] = useState<HTMLDivElement | null>(null);
    useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            const target = event.target as Element;
            if (target.closest("#global-menu-toggle")) return;
            if (ref && !ref.contains(target as Node)) { onClose(); }
        }
        if (isOpen) { document.addEventListener("mousedown", handleClickOutside); }
        return () => { document.removeEventListener("mousedown", handleClickOutside); };
    }, [isOpen, ref, onClose]);

    // [ANIMATION VARIANTS] EC2 빌드 에러 방지를 위해 'as const' 추가 - ksu.
    // [ANIMATION VARIANTS] EC2 빌드 에러 방지를 위해 'as const' 추가 - ksu.
    // 1. Container: Orchestrates the staging of children. (No visual styles itself)
    const containerVariants = {
        hidden: { opacity: 1, transition: { staggerChildren: 0.1 } },
        show: { opacity: 1, transition: { staggerChildren: 0.1 } },
        exit: { opacity: 0, transition: { duration: 0.2 } }
    } as const;

    // 2. Card: Individual "Round Blur Plates" that animate in.
    const cardVariants = {
        hidden: {
            opacity: 0, x: 20, y: 0, scale: 0.95,
            backdropFilter: "blur(20px)", WebkitBackdropFilter: "blur(20px)"
        },
        show: {
            opacity: 1, x: 0, y: 0, scale: 1,
            backdropFilter: "blur(20px)", WebkitBackdropFilter: "blur(20px)",
            transition: { type: "spring", stiffness: 300, damping: 30 }
        },
        exit: {
            opacity: 0, x: 20, y: 0, scale: 0.95,
            backdropFilter: "blur(20px)", WebkitBackdropFilter: "blur(20px)",
            transition: { duration: 0.2 }
        }
    } as const;

    // [HYPER-REALISTIC LIQUID GLASS BLOCK]
    // 1. Specular Highlights: Multiple inset shadows for the sharp rim and surface sheen.
    // 2. Volumetric Depth: Bottom inset shadow to simulate the glass meniscus.
    // 3. Clarity: Opacity increased to 0.8 at start for better legibility on dark backgrounds. Blur handled via class + parent.
    const liquidGlassBlock = "transform-gpu bg-gradient-to-br from-white/80 to-white/40 border border-white/40 shadow-[inset_0_1px_1px_rgba(255,255,255,0.9),inset_0_15px_30px_rgba(255,255,255,0.15),inset_0_-2px_10px_rgba(0,0,0,0.05),0_20px_40px_-10px_rgba(0,0,0,0.2)] overflow-hidden rounded-[36px] will-change-transform backdrop-blur-md";

    // [OBSIDIAN LIQUID GLASS BLOCK]
    const obsidianGlassBlock = "transform-gpu bg-gradient-to-br from-black/80 to-black/40 border border-white/10 shadow-[inset_0_1px_1px_rgba(255,255,255,0.3),inset_0_10px_20px_rgba(255,255,255,0.05),inset_0_-2px_10px_rgba(0,0,0,0.5),0_20px_40px_-5px_rgba(0,0,0,0.4)] overflow-hidden rounded-[32px] will-change-transform backdrop-blur-md";

    return (
        <AnimatePresence>
            {isOpen && (
                <>
                    {/* Mobile: Blur Overlay, Desktop: Transparent */}
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="fixed inset-0 z-40 bg-black/5 backdrop-blur-[4px] md:hidden"
                        onClick={onClose}
                    />
                    <div className="fixed inset-0 z-40 bg-transparent hidden md:block" />

                    <motion.div
                        ref={setRef}
                        className="fixed top-[84px] md:top-24 right-4 md:right-8 z-50 w-[calc(100%-32px)] sm:w-[350px] md:w-[300px] flex flex-col gap-3 md:gap-5"
                        variants={containerVariants}
                        initial="hidden"
                        animate="show"
                        exit="exit"
                    >
                        {/* --- CHUNK 1: HOME --- */}
                        <motion.div variants={cardVariants} className={`${liquidGlassBlock} p-1`}>
                            <MenuItem href="/" icon={Home} title="첫 화면" onClick={onClose} />
                        </motion.div>

                        {/* --- CHUNK 2: CORE FEATURES (The Big Glass Square) --- */}
                        <motion.div variants={cardVariants} className={`${liquidGlassBlock} p-1`}>
                            <div className="flex flex-col divide-y divide-black/5">
                                <MenuItem href="/chat" icon={Sparkles} title="향수 추천" onClick={onClose} />
                                <MenuItem href="/layering" icon={FlaskConical} title="레이어링 랩" onClick={onClose} />
                                <MenuItem href="/perfume-network/nmap" icon={Globe} title="향수 지도" onClick={onClose} />
                                <MenuItem href="/perfume-wiki" icon={BookOpen} title="향수 백과" onClick={onClose} />
                            </div>
                        </motion.div>

                        {/* --- CHUNK 3: FOOTER (Obsidian Glass) --- */}
                        <motion.div variants={cardVariants} className={`${obsidianGlassBlock} p-4 md:p-6 flex flex-col gap-3 md:gap-4`}>
                            <Link href="/contact" onClick={onClose} className="flex items-center justify-between group">
                                <span className="text-xs font-bold tracking-[0.2em] text-gray-400 group-hover:text-white transition-colors">CONTACT</span>
                                {/* 살아있는 레드 도트 (Pulse 애니메이션) */}
                                <span className="relative flex h-2 w-2">
                                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
                                    <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.8)] group-hover:bg-green-500 transition-all"></span>
                                </span>
                            </Link>

                            <div className="h-px bg-white/5" />

                            <Link href="/about" onClick={onClose} className="cursor-pointer group flex flex-col items-start mt-1 gap-0.5">
                                <p className="text-[10px] text-white/40 font-medium leading-none">About.</p>
                                <div className="flex items-center justify-between w-full">
                                    <span className="text-sm font-black tracking-[0.05em] text-gray-300 group-hover:tracking-[0.2em] group-hover:text-white transition-all duration-500">SCENTENCE</span>
                                    <span className="text-xl font-black text-gray-500 group-hover:text-white transition-all duration-500 transform rotate-90 group-hover:rotate-0 opacity-50 group-hover:opacity-100 mr-1">!</span>
                                </div>
                            </Link>
                        </motion.div>
                    </motion.div>
                </>
            )}
        </AnimatePresence>
    );
}
