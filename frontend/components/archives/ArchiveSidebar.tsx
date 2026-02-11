"use client";

import { useEffect, useState } from "react";
import { useSession, signOut } from "next-auth/react";

interface ArchiveSidebarProps {
    isOpen: boolean;
    onClose: () => void;
}

export default function ArchiveSidebar({ isOpen, onClose }: ArchiveSidebarProps) {
    const { data: session } = useSession();
    const [profileImageUrl, setProfileImageUrl] = useState<string | null>(null);
    const displayName = session?.user?.name || session?.user?.email || "회원";

    useEffect(() => {
        if (!isOpen) return;
        if (typeof window === "undefined") return;
        const apiBaseUrl = "/api";
        // localAuth 제거: 세션 ID로만 조회
        const memberId = session?.user?.id;
        if (!memberId) {
            setProfileImageUrl(null);
            return;
        }
        fetch(`${apiBaseUrl}/users/profile/${memberId}`)
            .then((res) => (res.ok ? res.json() : null))
            .then((data) => {
                if (data?.profile_image_url) {
                    setProfileImageUrl(data.profile_image_url);
                } else {
                    setProfileImageUrl(null);
                }
            })
            .catch(() => setProfileImageUrl(null));
    }, [isOpen, session]);

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-[9999] flex justify-end">
            {/* 배경 클릭 시 닫힘 */}
            <div className="fixed inset-0 bg-black/50" onClick={onClose} />

            {/* 사이드바 본체 (폭을 넓게 w-96 설정) */}
            <div className="relative w-96 h-full bg-white shadow-2xl flex flex-col z-10 overflow-y-auto animate-slide-in-right">

                {/* 닫기 버튼 (우측 상단 X) */}
                <button onClick={onClose} className="absolute top-6 right-6 text-gray-400 hover:text-black transition-colors">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-8 h-8">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                </button>

                {/* 1. 유저 프로필 영역 */}
                <div className="pt-24 px-8 pb-10 flex flex-col items-center border-b border-gray-100 bg-[#FAFAFA]">
                    <div className="w-32 h-32 rounded-full overflow-hidden mb-5 shadow-lg border-4 border-white bg-[#F2F2F2]">
                        <img
                            src={profileImageUrl || "/default_profile.png"}
                            alt="User Profile"
                            className="w-full h-full object-cover"
                            onError={(event) => {
                                event.currentTarget.src = "/default_profile.png";
                            }}
                        />
                    </div>
                    <h2 className="text-xl font-bold text-gray-900 mb-1">{displayName}님</h2>
                    <p className="text-sm text-gray-500 font-medium tracking-wide">환영합니다!</p>
                    <button
                        onClick={() => {
                            if (session) {
                                signOut({ callbackUrl: "/login" });
                                return;
                            }
                            window.location.href = "/login";
                        }}
                        className="mt-4 text-sm text-gray-400 hover:text-red-500 underline decoration-gray-300 hover:decoration-red-300 underline-offset-4 transition-colors"
                    >
                        로그아웃
                    </button>
                </div>

                {/* 2. 메뉴 섹션 (s1, s2, s3 이미지) */}
                <div className="flex-1 px-6 py-8 space-y-6 bg-white">
                    <p className="text-xs font-bold text-gray-400 px-2 uppercase tracking-wider mb-2">My Best</p>

                    <div className="group cursor-pointer hover:shadow-lg transition-all duration-300 rounded-2xl overflow-hidden shadow-sm border border-gray-100">
                        <img src="/perfumes/archive_s1.png" alt="나만의 아카이브" className="w-full h-auto group-hover:scale-105 transition-transform duration-500" />
                    </div>

                    <div className="group cursor-pointer hover:shadow-lg transition-all duration-300 rounded-2xl overflow-hidden shadow-sm border border-gray-100">
                        <img src="/perfumes/archive_s2.png" alt="향수 관계맵" className="w-full h-auto group-hover:scale-105 transition-transform duration-500" />
                    </div>

                    <div className="group cursor-pointer hover:shadow-lg transition-all duration-300 rounded-2xl overflow-hidden shadow-sm border border-gray-100">
                        <img src="/perfumes/archive_s3.png" alt="문의하기" className="w-full h-auto group-hover:scale-105 transition-transform duration-500" />
                    </div>

                    <div className="pt-8 text-center" />
                </div>

            </div>
        </div>
    );
}
