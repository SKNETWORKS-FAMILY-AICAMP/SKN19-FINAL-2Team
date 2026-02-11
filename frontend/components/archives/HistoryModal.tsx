/* HistoryModal.tsx (Popover Version) */
"use client";
import CabinetShelf from './CabinetShelf';
import { motion } from "framer-motion";
interface MyPerfume {
    my_perfume_id: number;
    perfume_id: number;
    name: string;
    brand: string;
    image_url: string | null;
    status: string;
    preference?: string;
}
interface Props {
    historyItems: MyPerfume[];
    onClose: () => void;
    onSelect: (perfume: MyPerfume) => void;
    isKorean: boolean;
}
export default function HistoryModal({ historyItems, onClose, onSelect, isKorean }: Props) {
    return (
        <>
            {/* [Backdrop] 배경 블러 & 어둡게 처리 */}
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="fixed inset-0 z-[100] bg-black/40 backdrop-blur-md"
                onClick={onClose}
            />

            {/* [Modal Container] 화면 중앙에 배치 */}
            <motion.div
                initial={{ opacity: 0, scale: 0.95, y: 20 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95, y: 20 }}
                className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[90%] md:w-[600px] max-h-[80vh] bg-white rounded-[40px] shadow-2xl z-[110] flex flex-col overflow-hidden"
            >
                {/* 헤더 */}
                <div className="flex items-center justify-between px-8 py-6 border-b border-gray-50 bg-[#FDFBF8]">
                    <div className="flex items-center gap-3">
                        <span className="text-2xl">⏳</span>
                        <div>
                            <h2 className="text-xl font-black text-black uppercase tracking-tighter">History Archive</h2>
                            <p className="text-[10px] font-bold text-gray-400 uppercase tracking-widest mt-0.5">Your Past Scent Journeys</p>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="w-10 h-10 flex items-center justify-center rounded-full hover:bg-black/5 transition-colors"
                    >
                        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12"></path></svg>
                    </button>
                </div>

                {/* 리스트 (스크롤 가능) */}
                <div className="flex-1 overflow-y-auto p-8 custom-scrollbar bg-white">
                    {historyItems.length === 0 ? (
                        <div className="py-20 flex flex-col items-center justify-center text-gray-300">
                            <span className="text-5xl mb-4">🍃</span>
                            <p className="text-sm font-bold uppercase tracking-widest">No memories yet</p>
                        </div>
                    ) : (
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-6">
                            {historyItems.map((item) => (
                                <div key={item.my_perfume_id} className="relative group">
                                    <CabinetShelf
                                        perfume={item}
                                        onSelect={(p) => {
                                            onClose();
                                            onSelect(p);
                                        }}
                                        isKorean={isKorean}
                                    />
                                    {item.preference && (
                                        <div className="absolute top-2 right-2 bg-white/90 backdrop-blur-md w-8 h-8 flex items-center justify-center rounded-full text-sm shadow-sm border border-gray-100 z-10 pointer-events-none">
                                            {item.preference === "GOOD" && "👍"}
                                            {item.preference === "BAD" && "👎"}
                                            {item.preference === "NEUTRAL" && "👌"}
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* 푸터 스탯 */}
                <div className="px-8 py-4 bg-gray-50/50 border-t border-gray-50 flex justify-end items-center">
                    <span className="text-[10px] font-black text-gray-400 uppercase tracking-widest">
                        Total {historyItems.length} Memories
                    </span>
                </div>
            </motion.div>
        </>
    );
}
