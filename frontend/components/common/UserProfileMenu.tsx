"use client";

import { useEffect, useState } from "react";
import { useSession, signOut } from "next-auth/react";
import Link from "next/link";
import { motion, AnimatePresence, Variants } from "framer-motion";
import { User, Shield, LogOut, Library } from "lucide-react";

interface UserProfileMenuProps {
    isOpen: boolean;
    onClose: () => void;
}

// [MENU ITEM] 스타일 컴포넌트 (Sidebar와 동일 스타일)
function MenuItem({ href, icon: Icon, title, desc, onClick, className = "" }: any) {
    return (
        <Link
            href={href}
            onClick={onClick}
            className={`flex items-center gap-3 md:gap-4 py-2.5 md:py-3 px-4 md:px-5 hover:bg-white/10 transition-all duration-300 group rounded-xl ${className}`}
        >
            <div className="relative group-hover:scale-110 transition-transform duration-300">
                <Icon strokeWidth={1.5} className="w-5 h-5 text-[#1a1a1a] group-hover:text-black transition-colors" />
            </div>

            <div className="flex flex-col">
                <span className="text-sm md:text-base font-bold text-[#1a1a1a] tracking-tight group-hover:tracking-widest transition-all duration-500 whitespace-nowrap">
                    {title}
                </span>
                {desc && <span className="text-[9px] md:text-[10px] text-gray-500 mt-0.5">{desc}</span>}
            </div>
            {/* Dot Indicator */}
            <div className="ml-auto w-1.2 md:w-1.5 h-1.2 md:h-1.5 rounded-full bg-black opacity-0 group-hover:opacity-100 transition-all transform scale-0 group-hover:scale-100 shadow-[0_0_8px_rgba(0,0,0,0.1)]" />
        </Link>
    );
}

export default function UserProfileMenu({ isOpen, onClose }: UserProfileMenuProps) {
    const { data: session } = useSession();
    const [profileRoleType, setProfileRoleType] = useState<string | null>(null);
    // 세션에 심어둔 roleType으로 UI를 즉시 표시 (서버 검증은 그대로 유지)
    const sessionRoleType = (session?.user as any)?.roleType as string | undefined;

    // Role 확인
    useEffect(() => {
        if (!isOpen) return;
        const memberId = session?.user?.id;
        if (!memberId) return;

        // [Admin Button Fix] Force fresh fetch to ensure role_type is up to date
        fetch(`/api/users/profile/${memberId}`, { cache: 'no-store' })
            .then((res) => (res.ok ? res.json() : null))
            .then((data) => {
                if (data?.role_type) setProfileRoleType(data.role_type);
            })
            .catch(() => { });
    }, [isOpen, session]);

    // UI는 세션 roleType으로 즉시 표시, 이후 서버 응답으로 보정
    const resolvedRoleType = (profileRoleType || sessionRoleType || "").toUpperCase();
    const isAdmin = resolvedRoleType === "ADMIN";

    // Outside Click Close
    useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            const target = event.target as Element;
            // 프로필 아이콘(토글 버튼) 클릭 시 닫히지 않도록 예외 처리용 ID 확인 필요
            if (target.closest("#profile-menu-toggle")) return;
            // 메뉴 내부 클릭은 유지, 그 외 닫기 (실제 구현 시 ref 사용 권장하지만 간단히 처리)
        }
        if (isOpen) { document.addEventListener("mousedown", handleClickOutside); }
        return () => { document.removeEventListener("mousedown", handleClickOutside); };
        // *심플한 닫기 처리를 위해 메뉴 클릭 시 닫히도록 MenuItem에 onClose 연결함
    }, [isOpen, onClose]);

    const handleOverlayClick = () => onClose();

    // [ANIMATION VARIANTS]
    // 1. Container: Orchestrates the staging of children. (No visual styles itself)
    const containerVariants: Variants = {
        hidden: { opacity: 1, transition: { staggerChildren: 0.05 } },
        show: { opacity: 1, transition: { staggerChildren: 0.05 } },
        exit: { opacity: 0, transition: { duration: 0.2 } }
    };

    // 2. Card: Individual "Round Blur Plates" that animate in.
    const cardVariants: Variants = {
        hidden: {
            opacity: 0, scale: 0.95, y: -10
        },
        show: {
            opacity: 1, scale: 1, y: 0,
            transition: { type: "spring" as const, stiffness: 300, damping: 30 }
        },
        exit: {
            opacity: 0, scale: 0.95, y: -10,
            transition: { duration: 0.2 }
        }
    };

    // [HYPER-REALISTIC LIQUID GLASS BLOCK]
    const liquidGlassBlock = "transform-gpu bg-gradient-to-br from-white/80 to-white/40 border border-white/40 shadow-[inset_0_1px_1px_rgba(255,255,255,0.9),inset_0_15px_30px_rgba(255,255,255,0.15),inset_0_-2px_10px_rgba(0,0,0,0.05),0_20px_40px_-10px_rgba(0,0,0,0.2)] overflow-hidden rounded-[24px] md:rounded-[32px] will-change-transform backdrop-blur-md";

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
                        onClick={handleOverlayClick}
                    />
                    <div
                        className="fixed inset-0 z-40 bg-transparent hidden md:block"
                        onClick={handleOverlayClick}
                    />

                    <motion.div
                        className="fixed top-[84px] md:top-20 right-4 md:right-20 z-50 w-[calc(100%-32px)] sm:w-[320px] md:w-[260px] flex flex-col gap-3 md:gap-4"
                        variants={containerVariants}
                        initial="hidden"
                        animate="show"
                        exit="exit"
                    >
                        {/* --- CHUNK 1: ADMIN STUDIO --- */}
                        {isAdmin && (
                            <motion.div variants={cardVariants} className={`${liquidGlassBlock} p-1`}>
                                <MenuItem href="/admin" icon={Shield} title="관리자 페이지" className="!text-blue-600" onClick={onClose} />
                            </motion.div>
                        )}

                        {/* --- CHUNK 2: PERSONAL --- */}
                        <motion.div variants={cardVariants} className={`${liquidGlassBlock} p-1`}>
                            <div className="flex flex-col divide-y divide-black/5">
                                <MenuItem href="/mypage" icon={User} title="마이 페이지" desc="내 정보 및 프로필 관리" onClick={onClose} />
                                <MenuItem href="/archives" icon={Library} title="나만의 보관함" desc="나만의 향수 라이브러리" onClick={onClose} />
                            </div>
                        </motion.div>

                        {/* --- CHUNK 3: LOGOUT --- */}
                        <motion.div variants={cardVariants} className={`${liquidGlassBlock} p-1`}>
                            <button
                                onClick={() => {
                                    if (session) signOut({ callbackUrl: "/login" });
                                    else window.location.href = "/login";
                                }}
                                className="w-full flex items-center justify-between p-3.5 md:p-4 px-5 md:px-6 hover:bg-white/10 transition-all duration-300 group rounded-xl"
                            >
                                <span className="text-sm md:text-base font-bold text-[#1a1a1a] tracking-tight group-hover:tracking-widest transition-all duration-500">로그아웃</span>
                                <LogOut strokeWidth={1.5} className="w-4 h-4 md:w-5 md:h-5 text-gray-400 group-hover:text-red-500 transition-all duration-300" />
                            </button>
                        </motion.div>
                    </motion.div>
                </>
            )}
        </AnimatePresence>
    );
}
