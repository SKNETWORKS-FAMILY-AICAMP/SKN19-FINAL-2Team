/* PerfumeDetailModal.tsx (3-State Buttons: HAVE, HAD-Amber, WISH) */
"use client";

import { useState } from "react";

interface MyPerfume {
    my_perfume_id: number;
    perfume_id: number;
    name: string;
    brand: string;
    image_url: string | null;
    status: string; // HAVE, HAD, RECOMMENDED
    preference?: string; // 추가
}

interface Props {
    perfume: MyPerfume;
    onClose: () => void;
    onUpdateStatus: (id: number, status: string) => void;
    onDelete: (id: number, rating: number) => void;
    onUpdatePreference: (id: number, preference: string) => void;
    isKorean?: boolean;
}

export default function PerfumeDetailModal({ perfume, onClose, onUpdateStatus, onDelete, onUpdatePreference, isKorean = false }: Props) {
    const [isDeleting, setIsDeleting] = useState(false);

    const handleDeleteWithRating = (rating: number) => {
        onDelete(perfume.my_perfume_id, rating);
        onClose();
    };

    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-3 sm:p-4 animate-fade-in"
            onPointerDown={onClose}
        >
            <div
                className="bg-white w-[min(92vw,760px)] md:w-full md:max-w-3xl rounded-2xl md:rounded-3xl overflow-hidden shadow-2xl relative flex flex-col md:flex-row max-h-[82vh] md:max-h-[88vh]"
                onPointerDown={(e) => e.stopPropagation()}
                onClick={(e) => e.stopPropagation()}
            >
                <button
                    type="button"
                    onPointerDown={(e) => {
                        e.stopPropagation();
                        onClose();
                    }}
                    onClick={(e) => {
                        e.stopPropagation();
                        onClose();
                    }}
                    className="absolute top-4 right-4 z-10 w-8 h-8 flex items-center justify-center rounded-full bg-gray-100 text-gray-500 hover:bg-gray-200 transition"
                    aria-label="닫기"
                >
                    &times;
                </button>

                {/* Left: Image Section */}
                <div className={`w-full md:w-1/2 h-[190px] md:aspect-square md:h-auto bg-[#Fdfcf8] flex items-center justify-center p-6 md:p-10 relative transition-all ${isDeleting ? 'brightness-50 grayscale' : ''}`}>
                    <div className="absolute w-[80%] h-[80%] rounded-full bg-[#f5f1e6] blur-3xl opacity-60"></div>
                    {perfume.image_url ? (
                        <img
                            src={perfume.image_url}
                            alt={perfume.name}
                            className="max-w-full max-h-full object-contain relative z-10 drop-shadow-xl scale-[1.08] md:scale-[1.2] md:-translate-y-4"
                        />
                    ) : (
                        <span className="text-gray-300 font-medium">No Image</span>
                    )}
                </div>

                {/* Right: Info Section */}
                <div className="w-full md:w-1/2 p-5 md:p-10 flex flex-col justify-center relative overflow-y-auto">

                    {!isDeleting ? (
                        <>
                            <div className="mb-5 md:mb-8">
                                <p className="text-[#C5A55D] text-xs font-bold tracking-widest uppercase mb-2">{perfume.brand}</p>
                                <h2 className="text-2xl md:text-3xl font-bold text-[#222] leading-tight mb-3 md:mb-4">{perfume.name}</h2>
                                <div className="h-1 w-12 bg-[#C5A55D]/30 rounded-full"></div>
                            </div>

                            <div className="space-y-4 md:space-y-6">
                                <div className="space-y-3">
                                    <label className="text-gray-400 text-xs font-bold uppercase tracking-wider">
                                        {perfume.status === 'HAD' ? "My Rating (경험 평가)" : "Current Status"}
                                    </label>

                                    {perfume.status === 'HAD' ? (
                                        // [HAD 상태일 때: 평가 버튼]
                                        <div className="flex flex-col gap-2">
                                            <div className="flex gap-2">
                                                <button
                                                    onClick={() => onUpdatePreference(perfume.my_perfume_id, 'GOOD')}
                                                    className={`
                                                        flex-1 py-3 px-2 rounded-xl border transition-all flex items-center justify-center gap-2
                                                        ${perfume.preference === 'GOOD'
                                                            ? 'bg-green-500 text-white border-green-500 shadow-md'
                                                            : 'bg-white text-gray-500 border-gray-200 hover:bg-green-50 hover:text-green-600'}
                                                    `}
                                                >
                                                    <span>👍</span> <span className="text-xs font-bold">좋았어요</span>
                                                </button>
                                                <button
                                                    onClick={() => onUpdatePreference(perfume.my_perfume_id, 'NEUTRAL')}
                                                    className={`
                                                        flex-1 py-3 px-2 rounded-xl border transition-all flex items-center justify-center gap-2
                                                        ${perfume.preference === 'NEUTRAL'
                                                            ? 'bg-gray-500 text-white border-gray-500 shadow-md'
                                                            : 'bg-white text-gray-500 border-gray-200 hover:bg-gray-50 hover:text-gray-600'}
                                                    `}
                                                >
                                                    <span>😐</span> <span className="text-xs font-bold">무난해요</span>
                                                </button>
                                                <button
                                                    onClick={() => onUpdatePreference(perfume.my_perfume_id, 'BAD')}
                                                    className={`
                                                        flex-1 py-3 px-2 rounded-xl border transition-all flex items-center justify-center gap-2
                                                        ${perfume.preference === 'BAD'
                                                            ? 'bg-red-500 text-white border-red-500 shadow-md'
                                                            : 'bg-white text-gray-500 border-gray-200 hover:bg-red-50 hover:text-red-600'}
                                                    `}
                                                >
                                                    <span>👎</span> <span className="text-xs font-bold">별로예요</span>
                                                </button>
                                            </div>
                                            <div className="text-center mt-2">
                                                <button onClick={() => onUpdateStatus(perfume.my_perfume_id, 'HAVE')} className="text-[10px] text-gray-400 underline hover:text-gray-600">
                                                    다시 보유 상태로 변경하기 (Status Change)
                                                </button>
                                            </div>
                                        </div>
                                    ) : (
                                        // [HAVE / WISH 상태일 때: 상태 변경 버튼]
                                        <div className="flex gap-2">
                                            <button
                                                onClick={() => onUpdateStatus(perfume.my_perfume_id, 'HAVE')}
                                                className={`
                                                    flex-1 py-3 text-sm font-bold rounded-xl border transition-all
                                                    ${perfume.status === 'HAVE'
                                                        ? 'bg-indigo-600 text-white border-indigo-600 shadow-lg shadow-indigo-200'
                                                        : 'bg-white text-gray-400 border-gray-100 hover:bg-indigo-50 hover:text-indigo-600'}
                                                `}
                                            >
                                                보유 (HAVE)
                                            </button>

                                            {/* HAD 버튼 제거됨 (삭제 기능으로 대체) */}

                                            <button
                                                onClick={() => onUpdateStatus(perfume.my_perfume_id, 'RECOMMENDED')}
                                                className={`
                                                    flex-1 py-3 text-sm font-bold rounded-xl border transition-all
                                                    ${perfume.status === 'RECOMMENDED' || perfume.status === 'WANT'
                                                        ? 'bg-rose-500 text-white border-rose-500 shadow-lg shadow-rose-200'
                                                        : 'bg-white text-gray-400 border-gray-100 hover:bg-rose-50 hover:text-rose-500'}
                                                `}
                                            >
                                                위시 (WISH)
                                            </button>
                                        </div>
                                    )}
                                </div>

                                <div className="pt-6 border-t border-gray-100">
                                    <button
                                        onClick={() => setIsDeleting(true)}
                                        className="w-full py-3 text-sm font-medium text-red-400 hover:text-red-600 hover:bg-red-50 rounded-xl transition flex items-center justify-center gap-2"
                                    >
                                        이 향수 삭제하기
                                    </button>
                                </div>
                            </div>
                        </>
                    ) : (
                        /* 삭제 평가 모드 */
                        <div className="absolute inset-0 p-10 flex flex-col justify-center bg-white/95 backdrop-blur-sm z-20 animate-slide-up">
                            <h3 className="text-xl font-bold text-[#333] mb-2">이 향수는 어땠나요?</h3>
                            <p className="text-gray-500 text-sm mb-6">평가를 남기면 취향 분석이 더 정확해집니다.</p>

                            <div className="space-y-3">
                                <button
                                    onClick={() => handleDeleteWithRating(1)}
                                    className="w-full py-3 px-4 bg-green-50 hover:bg-green-100/80 border border-green-100 rounded-xl flex items-center gap-3 transition group"
                                >
                                    <span className="text-2xl group-hover:scale-110 transition">👍</span>
                                    <div className="text-left">
                                        <p className="font-bold text-green-700 text-sm">좋았어요</p>
                                        <p className="text-[10px] text-green-600/70">내 취향에 잘 맞음 (+1)</p>
                                    </div>
                                </button>

                                <button
                                    onClick={() => handleDeleteWithRating(0)}
                                    className="w-full py-3 px-4 bg-gray-50 hover:bg-gray-100 border border-gray-200 rounded-xl flex items-center gap-3 transition group"
                                >
                                    <span className="text-2xl group-hover:scale-110 transition">😐</span>
                                    <div className="text-left">
                                        <p className="font-bold text-gray-700 text-sm">무난했어요</p>
                                        <p className="text-[10px] text-gray-500">쏘쏘 (0)</p>
                                    </div>
                                </button>

                                <button
                                    onClick={() => handleDeleteWithRating(-1)}
                                    className="w-full py-3 px-4 bg-red-50 hover:bg-red-100/80 border border-red-100 rounded-xl flex items-center gap-3 transition group"
                                >
                                    <span className="text-2xl group-hover:scale-110 transition">👎</span>
                                    <div className="text-left">
                                        <p className="font-bold text-red-700 text-sm">별로였어요</p>
                                        <p className="text-[10px] text-red-600/70">내 취향 아님 (-1)</p>
                                    </div>
                                </button>
                            </div>

                            <div className="mt-6 flex flex-col items-center gap-3">
                                <button
                                    onClick={() => {
                                        onDelete(perfume.my_perfume_id, undefined as any); // Hard Delete
                                        onClose();
                                    }}
                                    className="text-xs text-red-300 hover:text-red-500 underline transition"
                                >
                                    기록 없이 영구 삭제하기
                                </button>

                                <button
                                    onClick={() => setIsDeleting(false)}
                                    className="text-xs text-gray-400 hover:text-gray-600 underline"
                                >
                                    취소 (돌아가기)
                                </button>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
